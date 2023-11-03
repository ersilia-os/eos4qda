apt update
apt install software-properties-common
add-apt-repository ppa:avsm/ppa
apt update
apt install opam
opam init -y
eval $(opam env --switch=default)
pip install rdkit
eval `opam config env`
opam install --fake conf-rdkit
opam install -y fasmifra
which fasmifra_fragment.py
which fasmifra
pip install fpsim2