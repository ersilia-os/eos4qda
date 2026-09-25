import tempfile
import os
import csv
import shlex
import shutil
import subprocess
import sys
import warnings
import random
from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
# FRAGMENTS_FILE = os.path.join(ROOT, "..", "..", "checkpoints", "fragmented_fragments_from_enamine_merged.smi")
FRAGMENTS_FILE = os.path.join(ROOT, "..", "..", "checkpoints", "chembl_frags.smi")
FRAGMENT_SCRIPT = os.path.join(ROOT, "fasmifra_fragment.py")
# {atom type: tag index} of the tags used in FRAGMENTS_FILE. The input must be fragmented with the same
# numbering, otherwise its cut-bond tags do not mean the same thing as the library's.
TYPES_FILE = os.path.join(ROOT, "..", "..", "checkpoints", "atom_types.json")

# fasmifra assembles molecules by picking, uniformly at random, a seed and then fragments from the lines of the
# fragments file: the pool is the ChEMBL library plus the input's own fragment lines, repeated INPUT_WEIGHT times.
INPUT_WEIGHT = 1000
LIBRARY_LINES = 100000
N_SAMPLES_PER_ROUND = 300000
# Only the TOP_CANDIDATES most similar molecules are ever canonicalized / substructure-checked.
TOP_CANDIDATES = 2000
# A piece of the input must have at least this many heavy atoms to count as "containing a fragment of the input"
# (smaller pieces such as a phenyl are in almost every molecule).
MIN_PIECE_ATOMS = 6
MAX_ITER = 5
_SIM_CHUNK = 20000


_CHECKED_FASMIFRA = set()


def _check_atom_map_tags(fasmifra_bin):
    """fasmifra 2.x reads/writes atom-map tags ([*:i][*:j]); 1.x uses isotope tags ([i*][j*]) and cannot
    read the fragment files of this model. The version cannot be queried, so look for the format string."""
    if fasmifra_bin in _CHECKED_FASMIFRA:
        return
    with open(fasmifra_bin, "rb") as f:
        if b"[*:%d]" not in f.read():
            raise RuntimeError(
                f"{fasmifra_bin} does not use atom-map tags ([*:i]); this model needs fasmifra 2.x "
                "(the fragment library is written with atom-map tags)."
            )
    _CHECKED_FASMIFRA.add(fasmifra_bin)


class BiasedFasmifraSampler(object):
    def __init__(
        self, input_smiles, n_samples_per_round=N_SAMPLES_PER_ROUND, n_selected_samples=100
    ):
        self.input_smiles = input_smiles
        self.n_samples_per_round = n_samples_per_round
        self.n_selected_samples = n_selected_samples
        self.frags_file = os.path.abspath(FRAGMENTS_FILE)
        self.tmp_folder = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmp_folder, "log.txt")
        self.output_file = os.path.join(os.path.join(self.tmp_folder, "output.smi"))
        self.random_seed = random.randint(1, 99999)
        self.input_fragments = os.path.join(self.tmp_folder, "input_frags.smi")
        self.cur_frags_file = os.path.join(self.tmp_folder, "cur_frags.smi")
        self._library = None

    def _fragment_input_by_mw(self, mw):
        input_fragment_file = os.path.join(self.tmp_folder, "query.smi")
        with open(input_fragment_file, "w") as f:
            f.write("{0}\t{1}".format(self.input_smiles, "MY_INPUT"))
        cmd = "{0} {1} -i {2} -o {3} -n 5 -w {4} --types {5}".format(
            shlex.quote(sys.executable),
            shlex.quote(FRAGMENT_SCRIPT),
            shlex.quote(input_fragment_file),
            shlex.quote(self.input_fragments),
            mw,
            shlex.quote(os.path.abspath(TYPES_FILE)),
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
        return sorted(set(input_fragments))

    def _build_focused_fragments_file(self, fragmented_input):
        # fasmifra draws its seeds and the fragments it attaches uniformly from the lines of this file, so
        # repeating the input's own fragment lines INPUT_WEIGHT times is what biases the generation towards
        # the input (10 lines out of 100,000 make no measurable difference).
        if self._library is None:
            with open(self.frags_file, "r") as f:
                self._library = [r[0] for r in csv.reader(f, delimiter="\t")]
        frags = random.sample(self._library, min(LIBRARY_LINES, len(self._library)))
        frags = fragmented_input * INPUT_WEIGHT + frags
        random.shuffle(frags)
        with open(self.cur_frags_file, "w") as f:
            for i, frag in enumerate(frags):
                f.write("{0}\tfrag_{1}\n".format(frag, i))

    def _sample_single(self):
        self.random_seed += 1

        def _find_fasmifra():
            # The copy installed in this Python's own environment comes first: a `fasmifra` found on PATH
            # can be another version (e.g. an opam switch on a developer machine), which silently produces
            # garbage because the versions read different tag formats.
            env_bin = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "fasmifra")
            if os.path.exists(env_bin) and os.access(env_bin, os.X_OK):
                return env_bin

            p = shutil.which("fasmifra")
            if p:
                return p

            try:
                opam = shutil.which("opam")
                if opam:
                    prefix = subprocess.check_output(
                        [opam, "var", "prefix"],
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=os.environ,
                    ).strip()
                    cand = os.path.join(prefix, "bin", "fasmifra")
                    if os.path.exists(cand) and os.access(cand, os.X_OK):
                        os.environ["PATH"] = (
                            os.path.join(prefix, "bin")
                            + os.pathsep
                            + os.environ.get("PATH", "")
                        )
                        return cand
            except Exception:
                pass

            for cand in [
                "/usr/local/bin/fasmifra",
                "/usr/bin/fasmifra",
                "/bin/fasmifra",
                "/root/.opam/default/bin/fasmifra",
            ]:
                if os.path.exists(cand) and os.access(cand, os.X_OK):
                    return cand

            return None

        fasmifra_bin = _find_fasmifra()
        if not fasmifra_bin:
            raise RuntimeError(
                "fasmifra not found from Python. "
                f"PATH={os.environ.get('PATH', '')}. "
                "Tried PATH, `opam var prefix`, and common locations."
            )

        _check_atom_map_tags(fasmifra_bin)

        # -f: fasmifra caches the indexed fragments in <input file>.bin_cache and reuses the cache on the
        # next run without checking that the input changed. The fragments file is rewritten every round,
        # so without -f every round after the first would silently reuse the first round's fragments.
        cmd = [
            fasmifra_bin,
            "-f",
            "-i",
            self.cur_frags_file,
            "-o",
            self.output_file,
            "-n",
            str(self.n_samples_per_round),
            "--seed",
            str(self.random_seed),
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

    def _input_pieces(self, fragment_lines, input_heavy_atoms):
        """Substructure queries for the pieces of the input between its cut bonds (a cut-bond tag matches any
        atom). A piece must have between MIN_PIECE_ATOMS and (input_heavy_atoms - MIN_PIECE_ATOMS) atoms: the
        upper bound requires the OTHER side of the cut to be a real fragment too, not just a trimmed-off atom
        or two. Without it, a rigid, mostly-uncuttable input (fused rings, e.g. a steroid: every bond is
        either in a ring or next to a stereocentre, both protected by fasmifra_fragment.py) produces only
        "pieces" that are in fact almost the whole molecule. Requiring an assembled candidate to contain such
        a piece amounts to requiring it to reproduce the input almost exactly -- which then either matches
        nothing, or matches only the input itself and is dropped by the echo exclusion in
        `_rank_by_similarity`. Confirmed empirically on two such inputs: dropping the size cap left every one
        of MAX_ITER rounds returning 0 selected molecules, despite hundreds of thousands of raw candidates."""
        max_atoms = input_heavy_atoms - MIN_PIECE_ATOMS
        queries = []
        for line in fragment_lines:
            mol = Chem.MolFromSmiles(line)
            if mol is None:
                continue
            rw = Chem.RWMol(mol)
            for a in mol.GetAtoms():
                if a.GetAtomicNum() == 0:
                    for n in a.GetNeighbors():
                        if n.GetAtomicNum() == 0 and n.GetIdx() > a.GetIdx():
                            rw.RemoveBond(a.GetIdx(), n.GetIdx())
            for piece in Chem.GetMolFrags(rw.GetMol(), asMols=True, sanitizeFrags=False):
                n = sum(1 for a in piece.GetAtoms() if a.GetAtomicNum() != 0)
                if MIN_PIECE_ATOMS <= n <= max_atoms:
                    q = Chem.MolFromSmarts(Chem.MolToSmiles(piece))
                    if q is not None:
                        queries.append(q)
        return queries

    def _rank_by_similarity(self, smiles, ref_fp, input_flat, ranked):
        """Merge `smiles` into `ranked`, a list of (similarity, raw_smiles) kept to the TOP_CANDIDATES best.
        Similarity is the Morgan (radius 2, count) Tanimoto to the input.

        The input molecule itself must be excluded HERE, not only when `ranked` is finally read out: for a
        rigid input with few cut bonds (e.g. fused rings), fasmifra mostly reconstructs the input itself, in
        many equivalent stereo re-orderings, all scoring the maximum similarity of 1.0 (Morgan fingerprints
        ignore stereochemistry by default). Confirmed empirically: for such an input, all TOP_CANDIDATES slots
        filled up with these echoes and nothing else ever got selected, across every one of MAX_ITER rounds.
        Excluding echoes before they can occupy a slot leaves room for real, different-but-similar molecules.

        The echo check (isomericSmiles=False) already canonicalizes every candidate once; a second, fully
        canonical form is only computed later, for the far smaller `ranked` set (see `_select_n_best`).
        """
        for start in range(0, len(smiles), _SIM_CHUNK):
            fps, ok = [], []
            for smi in smiles[start:start + _SIM_CHUNK]:
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    continue
                if Chem.MolToSmiles(mol, isomericSmiles=False) == input_flat:
                    continue
                fps.append(AllChem.GetMorganFingerprint(mol, 2))
                ok.append(smi)
            ranked = ranked + list(zip(DataStructs.BulkTanimotoSimilarity(ref_fp, fps), ok))
            ranked.sort(key=lambda x: -x[0])
            del ranked[TOP_CANDIDATES:]
        return ranked

    def _select_n_best(self, ranked, pieces):
        """The most similar molecules that are unique and contain a piece of the input. `ranked` already
        excludes the input itself (see `_rank_by_similarity`)."""
        selected, seen = [], set()
        for _, smi in ranked:
            mol = Chem.MolFromSmiles(smi)
            can = Chem.MolToSmiles(mol)
            if can in seen:
                continue
            if pieces and not any(mol.HasSubstructMatch(q) for q in pieces):
                continue
            seen.add(can)
            selected.append(can)
            if len(selected) == self.n_selected_samples:
                break
        return selected

    def sample(self):
        try:
            input_mol = Chem.MolFromSmiles(self.input_smiles)
            if input_mol is None:
                raise ValueError("invalid input SMILES: %r" % self.input_smiles)
            input_flat = Chem.MolToSmiles(input_mol, isomericSmiles=False)
            ref_fp = AllChem.GetMorganFingerprint(input_mol, 2)
            input_fragments = self._fragment_input()
            pieces = self._input_pieces(input_fragments, input_mol.GetNumHeavyAtoms())
            ranked, done, selected = [], set(), []
            for _ in range(MAX_ITER):
                self._build_focused_fragments_file(input_fragments)
                complete = [s for s in self._sample_single() if "*" not in s and s not in done]
                done.update(complete)
                ranked = self._rank_by_similarity(complete, ref_fp, input_flat, ranked)
                selected = self._select_n_best(ranked, pieces)
                if len(selected) >= self.n_selected_samples:
                    break
            return selected
        finally:
            shutil.rmtree(self.tmp_folder, ignore_errors=True)
