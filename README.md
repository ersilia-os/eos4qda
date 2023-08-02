# Fasmifra molecule generator

FasmiFra is a molecular generator based on (deep)SMILES fragments. The authors use Deep SMILES to ensure the generated molecules are syntactically valid, and by working on string operations they are able to obtain high performance (>340,000 molecule/s)

## Identifiers

* EOS model ID: `eos4qda`
* Slug: `fasmifra`

## Characteristics

* Input: `Compound`
* Input Shape: `Single`
* Task: `Generative`
* Output: `Compound`
* Output Type: `String`
* Output Shape: `List`
* Interpretation: 1000 generated molecules per each input

## References

* [Publication](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-021-00566-4)
* [Source Code](https://github.com/UnixJunkie/FASMIFRA)
* Ersilia contributor: [miquelduranfrigola](https://github.com/miquelduranfrigola)

## Ersilia model URLs
* [GitHub](https://github.com/ersilia-os/eos4qda)
* [AWS S3](https://ersilia-models-zipped.s3.eu-central-1.amazonaws.com/eos4qda.zip)

## Citation

If you use this model, please cite the [original authors](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-021-00566-4) of the model and the [Ersilia Model Hub](https://github.com/ersilia-os/ersilia/blob/master/CITATION.cff).

## License

This package is licensed under a GPL-3.0 license. The model contained within this package is licensed under a GPL-3.0 license.

Notice: Ersilia grants access to these models 'as is' provided by the original authors, please refer to the original code repository and/or publication if you use the model in your research.

## About Us

The [Ersilia Open Source Initiative](https://ersilia.io) is a Non Profit Organization ([1192266](https://register-of-charities.charitycommission.gov.uk/charity-search/-/charity-details/5170657/full-print)) with the mission is to equip labs, universities and clinics in LMIC with AI/ML tools for infectious disease research.

[Help us](https://www.ersilia.io/donate) achieve our mission!