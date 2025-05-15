# imports
import os
import csv
import sys

root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(root)
from biased_sampler import BiasedFasmifraSampler

# parse arguments
input_file = sys.argv[1]
output_file = sys.argv[2]

# current file directory
root = os.path.dirname(os.path.abspath(__file__))


# my model
def sample(smi):
    sampler = BiasedFasmifraSampler(input_smiles=smi)
    return sampler.sample()


# read SMILES from .csv file, assuming one column with header
with open(input_file, "r") as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    smiles_list = [r[0] for r in reader]

# run model
outputs = []
for smi in smiles_list:
    output = sample(smi)
    outputs += [output]


N_COLS = 100

# write output in a .csv file
with open(output_file, "w") as f:
    writer = csv.writer(f)
    h = ["cpd_{:02d}".format(i) for i in range(N_COLS)]
    writer.writerow(h)
    for o in outputs:
        o = o[:N_COLS]
        if len(o) < N_COLS:
            o = o + [None] * (N_COLS - len(o))
        writer.writerow(o)
