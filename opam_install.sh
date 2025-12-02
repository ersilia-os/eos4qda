export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y opam bubblewrap m4 unzip git curl ca-certificates python3-pip

opam init --disable-sandboxing -y
eval "$(opam env)"

python3 -m pip install rdkit==2023.9.6

opam install -y conf-rdkit
opam install -y fasmifra

which fasmifra
which fasmifra_fragment.py
