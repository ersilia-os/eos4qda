import tempfile
import os
import csv
import re
import subprocess
import warnings
from tqdm import tqdm
import random
from FPSim2.io import create_db_file
from FPSim2 import FPSim2Engine
from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
# FRAGMENTS_FILE = os.path.join(ROOT, "..", "..", "checkpoints", "fragmented_fragments_from_enamine_merged.smi")
FRAGMENTS_FILE = os.path.join(ROOT, "..", "..", "checkpoints", "chembl_frags.smi")
FRAGMENT_SCRIPT = os.path.join(ROOT, "fasmifra_fragment.py")

MAX_ITER = 10
INFLATION = 1.25


def calculate_similarity(ref_mol, mol_list):
    ref_fp = AllChem.GetMorganFingerprint(ref_mol, 2)
    mol_fps = [AllChem.GetMorganFingerprint(mol, 2) for mol in mol_list]
    similarities = [
        DataStructs.TanimotoSimilarity(ref_fp, mol_fp) for mol_fp in mol_fps
    ]
    return similarities


def sort_molecules_by_similarity(ref_mol, mol_list, top_n):
    similarities = calculate_similarity(ref_mol, mol_list)
    paired = list(zip(mol_list, similarities))
    sorted_mols = sorted(paired, key=lambda x: x[1], reverse=True)
    print("Sorted mols", len(sorted_mols))
    return [mol for mol, sim in sorted_mols][:top_n]


class BiasedFasmifraSampler(object):
    def __init__(
        self, input_smiles, n_samples_per_round=1000000, n_selected_samples=100
    ):
        self.input_smiles = input_smiles
        self.n_samples_per_round = n_samples_per_round
        self.n_selected_samples = n_selected_samples
        self.frags_file = os.path.abspath(FRAGMENTS_FILE)
        self.tmp_folder = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmp_folder, "log.txt")
        self.db_file = os.path.join(self.tmp_folder, "db_file.h5")
        self.output_file = os.path.join(os.path.join(self.tmp_folder, "output.smi"))
        self.random_seed = random.randint(1, 99999)
        self.input_fragments = os.path.join(self.tmp_folder, "input_frags.smi")
        self.cur_frags_file = os.path.join(self.tmp_folder, "cur_frags.smi")

    def _fragment_input_by_mw(self, mw):
        input_fragment_file = os.path.join(self.tmp_folder, "query.smi")
        with open(input_fragment_file, "w") as f:
            f.write("{0}\t{1}".format(self.input_smiles, "MY_INPUT"))
        cmd = "python {0} -i {1} -o {2} -n 5 -w {3}".format(
            FRAGMENT_SCRIPT, input_fragment_file, self.input_fragments, mw
        )
        with open(self.log_file, "a") as fp:
            subprocess.Popen(
                cmd, stdout=fp, stderr=fp, shell=True, env=os.environ
            ).wait()
        with open(self.input_fragments, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            input_fragments = []
            for r in reader:
                input_fragments += [r[0]]
        return list(set(input_fragments))

    def _fragment_input(self):
        input_fragments = []
        for mw in [100, 150]:
            input_fragments += self._fragment_input_by_mw(mw)
        input_fragments = list(set(input_fragments))
        self.input_broken = []
        for frag in input_fragments:
            self.input_broken += self.break_molecule(frag)
        self.input_broken = list(set(self.input_broken))
        self.input_broken = [x for x in self.input_broken if len(x) >= 10]
        return input_fragments

    def break_molecule(self, s):
        s = [y for x in s.split("[") for y in x.split("]") if re.search("[a-zA-Z]", y)]
        return s

    def _build_focused_fragments_file(self, fragmented_input):
        frags = []
        with open(self.frags_file, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for r in reader:
                frags += [r[0]]
        frags = random.sample(frags, 100000)
        frags = fragmented_input + frags
        with open(self.cur_frags_file, "w") as f:
            for i, frag in enumerate(frags):
                f.write("{0}\tfrag_{1}\n".format(frag, i))

    def _sample_single(self):
        import shutil

        self.random_seed += 1

        fasmifra_bin = shutil.which("fasmifra")
        if not fasmifra_bin:
            raise RuntimeError(
                "fasmifra not found on PATH for this Python process. "
                f"PATH={os.environ.get('PATH', '')}"
            )

        cmd = [
            fasmifra_bin,
            "-i", self.cur_frags_file,
            "-o", self.output_file,
            "-n", str(self.n_samples_per_round),
            "--seed", str(self.random_seed),
        ]

        with open(self.log_file, "a") as fp:
            fp.write(f"\nCMD: {' '.join(cmd)}\n")
            fp.flush()
            p = subprocess.run(cmd, stdout=fp, stderr=fp, env=os.environ)

        if p.returncode != 0 or not os.path.exists(self.output_file):
            raise RuntimeError(
                f"fasmifra failed (exit={p.returncode}); output_missing={not os.path.exists(self.output_file)}; "
                f"see log: {self.log_file}"
            )

        sampled_smiles = []
        with open(self.output_file, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for r in reader:
                if r:
                    sampled_smiles.append(r[0])

        return list(set(sampled_smiles))


    def _build_search_database(self, smiles_list):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
        smiles_list_ = []
        for smi in tqdm(smiles_list):
            mol = Chem.MolFromSmiles(smi)
            if mol is not None:
                smiles_list_ += [smi]
        self.cur_input_list = [[smi, i] for i, smi in enumerate(smiles_list_)]
        create_db_file(
            self.cur_input_list, self.db_file, "Morgan", {"radius": 2, "nBits": 2048}
        )

    def _search_database(self):
        fpe = FPSim2Engine(self.db_file)
        results = fpe.similarity(self.input_smiles, 0.7, n_workers=1)
        hits = [self.cur_input_list[r[0]][0] for r in results]
        return hits

    def _select_n_best(self, smiles_list):
        if len(smiles_list) == 0:
            return []
        mol_list = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            mol_list += [mol]
        ref_mol = Chem.MolFromSmiles(self.input_smiles)
        sorted_mols = sort_molecules_by_similarity(
            ref_mol, mol_list, top_n=self.n_selected_samples
        )
        sorted_smiles = []
        for m in sorted_mols:
            if m is None:
                continue
            sorted_smiles += [Chem.MolToSmiles(m)]
        return sorted_smiles

    def sample(self):
        input_fragments = self._fragment_input()
        all_hits = set()
        for _ in range(MAX_ITER):
            self._build_focused_fragments_file(input_fragments)
            sampled_smiles = [
                s for s in list(set(self._sample_single())) if "*" not in s
            ]
            sampled_smiles_ = []
            for smi in sampled_smiles:
                for x in self.input_broken:
                    if x in smi:
                        sampled_smiles_ += [smi]
            sampled_smiles = sampled_smiles_
            sampled_smiles_ = []
            for smi in sampled_smiles:
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    continue
                sampled_smiles_ += [Chem.MolToSmiles(mol)]
            sampled_smiles = sampled_smiles_
            sampled_smiles = list(set(sampled_smiles))
            hits = sampled_smiles
            all_hits.update(hits)
            if len(all_hits) > self.n_selected_samples * INFLATION:
                break
        all_hits = list(all_hits)
        all_hits = self._select_n_best(all_hits)
        return all_hits
