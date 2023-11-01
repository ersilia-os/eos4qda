import tempfile
import os
import csv
import subprocess
import warnings
from FPSim2.io import create_db_file
from FPSim2 import FPSim2Engine
from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
FRAGMENTS_FILE = os.path.join(ROOT, "..", "..", "checkpoints", "fragments.smi")

MAX_ITER = 100
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
    return [mol for mol, sim in sorted_mols][:top_n]


class BiasedFasmifraSampler(object):
    def __init__(self, input_smiles, n_samples_per_round=100000, n_selected_samples=1000):
        self.input_smiles = input_smiles
        self.n_samples_per_round = n_samples_per_round
        self.n_selected_samples = n_selected_samples
        self.frags_file = os.path.abspath(FRAGMENTS_FILE)
        self.tmp_folder = tempfile.mktemp()
        self.log_file = os.path.join(self.tmp_folder, "log.txt")
        self.db_file = os.path.join(self.db_file, "db_file.h5")

    def _sample_single(self):
        output_file = os.path.join()
        cmd = "opam init -a; eval $(opam env); fasmifra -i {0} -o {1} -n {2}".format(
            self.frags_file, output_file, self.n_samples_per_round
        )
        with open(self.log_file, "a") as fp:
            subprocess.Popen(
                cmd, stdout=fp, stderr=fp, shell=True, env=os.environ
            ).wait()
        sampled_smiles = []
        with open(output_file, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for r in reader:
                sampled_smiles += [r[0]]
        return list(set(sampled_smiles))
    
    def _build_search_database(self, smiles_list):
        input_list = [[smi, i] for i,smi in enumerate(smiles_list)]
        create_db_file(input_list, self.db_file, 'Morgan', {'radius': 2, 'nBits': 2048})

    def _search_database(self):
       fpe = FPSim2Engine(self.db_file)
       results = fpe.similarity(self.input_smiles, 0.7, n_workers=1)
       hits = results # TODO
       return hits

    def _select_n_best(self, smiles_list):
        mol_list = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            mol_list += [mol]
        ref_mol = Chem.MolFromSmiles(self.input_smiles)
        sort_molecules_by_similarity(ref_mol, mol_list, top_n=self.n_selected_samples)

    def sample(self):
        all_hits = set()
        for _ in range(MAX_ITER):
            sampled_smiles = self._sample_single()
            self._build_search_database(sampled_smiles)
            hits = self._search_database()
            all_hits.update(hits)
            if len(all_hits) > self.n_selected_samples*INFLATION:
                break
        all_hits = list(all_hits)
        return self._select_n_best(all_hits)