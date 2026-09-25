# Model pretrained parameters

The 100k ChEMBL file from the FasmiFra repository was downloaded, as used in the paper. Then it was fragmented with default parameters (150 Da, one pass per molecule).

## Files

- `chembl_frags.smi`: the 100k fragmented molecules. Every cut bond is tagged in place as `[*:i][*:j]`, where `i` and `j` are the indices of the atom type of the atom on each side of the bond (see `atom_types.json`). This is the tag format read by fasmifra 2.x. The file was originally written with fasmifra 1.x isotope tags (`[i*][j*]`); the tags were converted textually, which does not change the molecules or the meaning of the indices (checked on all 100,000 lines).
- `atom_types.json`: `{atom type: index}` for the 36 atom types used by the tags. An atom type is `"<pi electrons>,<atomic number>,<heavy-atom neighbours>,<formal charge>"`, as computed by `type_atom()` in `model/framework/code/fasmifra_fragment.py`. It was recovered from the library itself (joining the tag pairs back into the original molecules and recomputing the types); each index maps to exactly one type and vice versa. The input molecule must be fragmented with this same numbering (`fasmifra_fragment.py --types`), otherwise its tags do not mean the same thing as the library's.
