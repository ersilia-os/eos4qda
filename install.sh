if [ -f /.dockerenv ]; then
    apt-get update
    apt-get install software-properties-common
    add-apt-repository ppa:avsm/ppa
    apt-get update
    apt-get install opam
else
    sudo apt-get update
    sudo apt-get install software-properties-common
    sudo add-apt-repository ppa:avsm/ppa
    sudo apt-get update
    sudo apt-get install opam
fi
opam init -y
eval $(opam env --switch=default)
pip install rdkit
eval `opam config env`
opam install --fake conf-rdkit
opam install -y fasmifra
which fasmifra_fragment.py
which fasmifra
pip install fpsim2
