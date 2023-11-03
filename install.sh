sudo apt-get update
sudo apt-get install software-properties-common
sudo add-apt-repository ppa:avsm/ppa
sudo apt-get update
sudo apt-get install opam
opam init -y
eval $(opam env --switch=default)
pip install rdkit
eval `opam config env`
opam install --fake conf-rdkit
opam install -y fasmifra
which fasmifra_fragment.py
which fasmifra
pip install fpsim2