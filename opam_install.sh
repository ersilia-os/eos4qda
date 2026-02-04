#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

try_sudo() {
  if have sudo; then
    sudo "$@" || "$@"
  else
    "$@"
  fi
}

apt_install() {
  try_sudo apt-get install -y --no-install-recommends "$@"
}

ensure_apt_deps() {
  if ! have apt-get; then
    log "ERROR: apt-get not found (this script assumes Debian/Ubuntu base)."
    exit 1
  fi

  log "apt-get update"
  try_sudo apt-get update -y

  log "Installing base deps"
  apt_install \
    ca-certificates curl unzip git rsync \
    build-essential autoconf pkg-config \
    python3 python3-pip
}

ensure_opam() {
  if have opam; then
    log "opam already installed: $(opam --version)"
    return 0
  fi

  log "Installing opam"
  try_sudo mkdir -p /usr/local/bin
  curl -fsSL https://opam.ocaml.org/install.sh -o /tmp/opam-install.sh
  chmod +x /tmp/opam-install.sh

  printf '%s\n' '/usr/local/bin' | try_sudo sh /tmp/opam-install.sh --no-backup

  if ! have opam; then
    log "ERROR: opam install finished but opam not found on PATH"
    exit 1
  fi
  log "opam installed: $(opam --version)"
}

ensure_opam_initialized() {
  log "Initializing opam (non-interactive, sandboxing disabled)"
  opam init -y --bare --disable-sandboxing --reinit

  opam repo add default https://opam.ocaml.org -y >/dev/null 2>&1 || true
  opam update -y

  eval "$(opam env)"
}

pick_ocaml_compiler_pkg() {
  local pkg
  pkg="$(opam switch list-available --short 2>/dev/null \
    | grep -E '^ocaml-base-compiler\.[0-9]+\.[0-9]+(\.[0-9]+)?$' \
    | sort -V \
    | tail -n 1 || true)"
  echo "$pkg"
}

ensure_opam_switch() {
  local cur_switch
  cur_switch="$(opam switch show 2>/dev/null || true)"
  if [ -n "${cur_switch:-}" ]; then
    log "opam switch already set: $cur_switch"
    eval "$(opam env --switch="$cur_switch")"
    return 0
  fi

  log "Creating opam switch"
  local compiler_pkg
  compiler_pkg="$(pick_ocaml_compiler_pkg)"

  if [ -n "${compiler_pkg:-}" ]; then
    log "Using compiler package: $compiler_pkg"
    opam switch create default "$compiler_pkg" -y
    eval "$(opam env --switch=default)"
    return 0
  fi

  if ! have ocaml; then
    log "No ocaml-base-compiler packages visible; installing system OCaml as fallback"
    apt_install ocaml
  fi

  log "Using ocaml-system fallback"
  opam switch create default ocaml-system -y
  eval "$(opam env --switch=default)"
}

ensure_fasmifra() {
  if have fasmifra; then
    log "fasmifra already on PATH: $(command -v fasmifra)"
    return 0
  fi

  log "Attempting to install fasmifra via opam"
  opam install -y fasmifra || true

  if have fasmifra; then
    log "fasmifra installed (opam): $(command -v fasmifra)"
    return 0
  fi

  log "ERROR: fasmifra not found after opam install."
  log "If fasmifra is bundled in your repo/image, ensure its directory is on PATH."
  exit 1
}

sanity() {
  log "Sanity checks"
  log "opam: $(opam --version)"
  log "switch: $(opam switch show || true)"
  log "python: $(python3 --version)"
  log "pip: $(python3 -m pip --version)"
  log "fasmifra: $(command -v fasmifra || echo 'NOT FOUND')"
  if have fasmifra; then
    fasmifra 2>/dev/null || true
  fi
}

main() {
  ensure_apt_deps
  ensure_opam
  ensure_opam_initialized
  ensure_opam_switch

  opam install --fake -y conf-rdkit >/dev/null 2>&1 || true

  ensure_fasmifra

  log "fasmifra_fragment.py check (optional)"
  command -v fasmifra_fragment.py >/dev/null 2>&1 && log "found: $(command -v fasmifra_fragment.py)" || log "not on PATH (ok if referenced by full path)"

  sanity
  log "Done."
}

main "$@"
