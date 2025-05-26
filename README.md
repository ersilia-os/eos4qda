# FasmiFra molecule generator

FasmiFra is a molecular generator based on (deep)SMILES fragments. The authors use Deep SMILES to ensure the generated molecules are syntactically valid, and by working on string operations they are able to obtain high performance (>340,000 molecule/s). Here, we use 100k compounds from ChEMBL to sample fragments. Only assembled molecules containing one of the fragments of the input molecule are retained.

This model was incorporated on 2023-08-01.

## Information
### Identifiers
- **Ersilia Identifier:** `eos4qda`
- **Slug:** `fasmifra`

### Domain
- **Task:** `Sampling`
- **Subtask:** `Generation`
- **Biomedical Area:** `Any`
- **Target Organism:** `Not Applicable`
- **Tags:** `Compound generation`

### Input
- **Input:** `Compound`
- **Input Dimension:** `1`

### Output
- **Output Dimension:** `1000`
- **Output Consistency:** `Variable`
- **Interpretation:** 1000 generated molecules per each input

Below are the **Output Columns** of the model:
| Name | Type | Direction | Description |
|------|------|-----------|-------------|
| cpd_00 | string |  | Generated molecule index 0 using FASMIFRA |
| cpd_01 | string |  | Generated molecule index 1 using FASMIFRA |
| cpd_02 | string |  | Generated molecule index 2 using FASMIFRA |
| cpd_03 | string |  | Generated molecule index 3 using FASMIFRA |
| cpd_04 | string |  | Generated molecule index 4 using FASMIFRA |
| cpd_05 | string |  | Generated molecule index 5 using FASMIFRA |
| cpd_06 | string |  | Generated molecule index 6 using FASMIFRA |
| cpd_07 | string |  | Generated molecule index 7 using FASMIFRA |
| cpd_08 | string |  | Generated molecule index 8 using FASMIFRA |
| cpd_09 | string |  | Generated molecule index 9 using FASMIFRA |

_10 of 100 columns are shown_
### Source and Deployment
- **Source:** `Local`
- **Source Type:** `External`
- **DockerHub**: [https://hub.docker.com/r/ersiliaos/eos4qda](https://hub.docker.com/r/ersiliaos/eos4qda)
- **Docker Architecture:** `AMD64`, `ARM64`
- **S3 Storage**: [https://ersilia-models-zipped.s3.eu-central-1.amazonaws.com/eos4qda.zip](https://ersilia-models-zipped.s3.eu-central-1.amazonaws.com/eos4qda.zip)

### Resource Consumption
- **Model Size (Mb):** `25`
- **Environment Size (Mb):** `637`
- **Image Size (Mb):** `624.98`

**Computational Performance (seconds):**
- 10 inputs: `35.09`
- 100 inputs: `223.59`
- 10000 inputs: `403.25`

### References
- **Source Code**: [https://github.com/UnixJunkie/FASMIFRA](https://github.com/UnixJunkie/FASMIFRA)
- **Publication**: [https://jcheminf.biomedcentral.com/articles/10.1186/s13321-021-00566-4](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-021-00566-4)
- **Publication Type:** `Peer reviewed`
- **Publication Year:** `2021`
- **Ersilia Contributor:** [miquelduranfrigola](https://github.com/miquelduranfrigola)

### License
This package is licensed under a [GPL-3.0](https://github.com/ersilia-os/ersilia/blob/master/LICENSE) license. The model contained within this package is licensed under a [GPL-3.0-only](LICENSE) license.

**Notice**: Ersilia grants access to models _as is_, directly from the original authors, please refer to the original code repository and/or publication if you use the model in your research.


## Use
To use this model locally, you need to have the [Ersilia CLI](https://github.com/ersilia-os/ersilia) installed.
The model can be **fetched** using the following command:
```bash
# fetch model from the Ersilia Model Hub
ersilia fetch eos4qda
```
Then, you can **serve**, **run** and **close** the model as follows:
```bash
# serve the model
ersilia serve eos4qda
# generate an example file
ersilia example -n 3 -f my_input.csv
# run the model
ersilia run -i my_input.csv -o my_output.csv
# close the model
ersilia close
```

## About Ersilia
The [Ersilia Open Source Initiative](https://ersilia.io) is a tech non-profit organization fueling sustainable research in the Global South.
Please [cite](https://github.com/ersilia-os/ersilia/blob/master/CITATION.cff) the Ersilia Model Hub if you've found this model to be useful. Always [let us know](https://github.com/ersilia-os/ersilia/issues) if you experience any issues while trying to run it.
If you want to contribute to our mission, consider [donating](https://www.ersilia.io/donate) to Ersilia!
