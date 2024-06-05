export DEBIAN_FRONTEND=noninteractive
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
try_sudo apt-get update
try_sudo apt-get install -y autoconf
try_sudo apt-get install -y apt-utils
try_sudo apt-get install -y software-properties-common
try_sudo add-apt-repository ppa:avsm/ppa
try_sudo apt-get update
try_sudo apt-get install -y opam
opam init --disable-sandboxing -y
eval $(opam env --switch=default)
python -m pip install rdkit==2023.9.6
eval `opam config env`
opam install --fake conf-rdkit
opam install -y fasmifra
which fasmifra_fragment.py
which fasmifra
python -m pip install FPSim2==0.4.5
python -m pip install tqdm==4.66.4
