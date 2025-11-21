#!/usr/bin/env bash
set -euo pipefail

# System deps (opam + build essentials often needed by opam packages)
apt-get update
apt-get install -y --no-install-recommends \
  opam curl git build-essential m4 unzip bubblewrap pkg-config \
  python3-pip python3-dev
rm -rf /var/lib/apt/lists/*

# Initialize opam (no sandbox in containers)
opam init -y --disable-sandboxing
eval "$(opam env)"
opam update

# RDKit for Python (use rdkit-pypi first; fall back to rdkit if needed)
pip3 install --no-cache-dir rdkit-pypi || pip3 install --no-cache-dir rdkit

# Tell opam that RDKit exists, then install fasmifra
eval "$(opam env)"
opam install -y --fake conf-rdkit
opam install -y fasmifra

# Prove binaries exist (PATH is correct within this shell)
which fasmifra_fragment.py || true
which fasmifra || true

# Make opam env available for future shells/containers
opam env --shell=bash > /etc/profile.d/opam.sh
echo 'source /etc/profile.d/opam.sh' >> /etc/bash.bashrc
