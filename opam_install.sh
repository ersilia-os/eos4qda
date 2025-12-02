export DEBIAN_FRONTEND=noninteractive

try_sudo() {
  cmd="$@"
  if command -v sudo >/dev/null 2>&1; then
    sudo $cmd || $cmd
  else
    $cmd
  fi
}

try_sudo apt-get update
try_sudo apt-get install -y autoconf apt-utils software-properties-common curl ca-certificates

curl -fsSL https://opam.ocaml.org/install.sh -o /tmp/opam-install.sh

try_sudo sh /tmp/opam-install.sh --no-backup

export PATH="/usr/local/bin:$PATH"

opam init --disable-sandboxing -y
eval "$(opam env --switch=default)"

python -m pip install rdkit==2023.9.6

eval "$(opam env)"
opam install --fake conf-rdkit
opam install -y fasmifra

which fasmifra_fragment.py || echo "fasmifra_fragment.py not found"
which fasmifra || echo "fasmifra not found"
