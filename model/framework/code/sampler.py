import tempfile
import csv
import os
import subprocess
import shutil


class FasmifraSampler(object):
    def __init__(self):
        pass

    def sample(self, smi, n):
        tmp_folder = tempfile.mkdtemp()
        input_file = os.path.join(tmp_folder, "input.smi")
        frags_file = os.path.join(tmp_folder, "frags.smi")
        output_file = os.path.join(tmp_folder, "output.smi")
        log_file = os.path.join(tmp_folder, "log.log")
        with open(input_file, "w") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([smi, "molecule-0"])
        cmd = "opam init -a; eval $(opam env); fasmifra_fragment.py -i {0} -o {1}".format(
            input_file, frags_file
        )
        with open(log_file, "w") as fp:
            subprocess.Popen(
                cmd, stdout=fp, stderr=fp, shell=True, env=os.environ
            ).wait()
        cmd = "opam init -a; eval $(opam env); fasmifra -i {0} -o {1} -n {2}".format(
            frags_file, output_file, n
        )
        with open(log_file, "a") as fp:
            subprocess.Popen(
                cmd, stdout=fp, stderr=fp, shell=True, env=os.environ
            ).wait()
        sampled_smiles = []
        with open(output_file, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for r in reader:
                sampled_smiles += [r[0]]
        shutil.rmtree(tmp_folder)
        print(len(sampled_smiles))
        return sampled_smiles