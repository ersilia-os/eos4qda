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
    sampler  = BiasedFasmifraSampler(input_smiles=smi)
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
print(len(outputs))


# write output in a .csv file
with open(output_file, "w") as f:
    writer = csv.writer(f)
    writer.writerow(["cpd_{}".format(i) for i in range(1, 1001)])  # header
    for o in outputs:
        writer.writerow(o)