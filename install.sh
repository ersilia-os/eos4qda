try_sudo() {
  cmd="$@"
  if command -v sudo >/dev/null 2>&1; then
    # If sudo is available, try to run the command with sudo.
    sudo $cmd || $cmd
  else
    # If sudo is not available, run the command without sudo.
    $cmd
  fi
}
try_sudo apt update
try_sudo apt install software-properties-common
try_sudo add-apt-repository ppa:avsm/ppa
try_sudo apt update
try_sudo apt install opam
opam init -y
eval $(opam env --switch=default)
pip install rdkit
eval `opam config env`
opam install --fake conf-rdkit
opam install -y fasmifra
which fasmifra_fragment.py
which fasmifra
pip install fpsim2
pip install tqdm
