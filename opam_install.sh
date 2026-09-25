#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Pinned toolchain. fasmifra 1.x (OCaml 4.x) reads isotope tags ([i*][j*]) and fasmifra 2.x
# (OCaml >= 5) reads atom-map tags ([*:i][*:j]); the two cannot read each other's fragment files,
# so the version must never depend on what happens to be installed on the build machine.
FASMIFRA_VERSION="2.1.0"
OCAML_COMPILER="ocaml-base-compiler.5.5.0"
# Dedicated switch: a pre-existing switch (e.g. "default" on OCaml 4.14) is never reused.
OPAM_SWITCH="eos4qda-fasmifra${FASMIFRA_VERSION}"
FASMIFRA_BIN=""

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

REQUIRED_TOOLS="gcc make curl unzip git rsync autoconf pkg-config python3 strings"

missing_tools() {
  local t missing=""
  for t in $REQUIRED_TOOLS; do
    have "$t" || missing="$missing $t"
  done
  echo "$missing"
}

ensure_apt_deps() {
  # A failed/unavailable apt-get must never be silently swallowed: this whole install runs
  # non-interactively (no TTY, often no sudo), and ersilia's own log scan only flags a build as
  # failed if the literal word "ERROR" appears in the combined output -- apt's own failure text
  # ("E: Could not open lock file...") does not contain it. Under `set -e`, letting a bare
  # `apt-get update` failure kill the script partway through used to leave fasmifra silently
  # uninstalled while the overall fetch was reported as successful. So: try apt only if something
  # is actually missing, tolerate its failure, then verify for real and fail loudly (our own
  # "ERROR:" line) only if a required tool is still missing afterwards.
  local missing
  missing="$(missing_tools)"
  if [ "${SKIP_APT:-0}" = "1" ] || [ -z "$missing" ]; then
    log "Base build deps present; skipping apt"
    return 0
  fi

  log "Missing build deps:$missing"
  if have apt-get; then
    log "apt-get update (failure here is not fatal by itself)"
    try_sudo apt-get update -y || log "WARNING: apt-get update failed"
    log "Installing base deps (failure here is not fatal by itself)"
    apt_install \
      ca-certificates curl unzip git rsync \
      build-essential autoconf pkg-config \
      python3 python3-pip \
      || log "WARNING: apt-get install failed"
  else
    log "WARNING: apt-get not found; cannot install missing deps automatically"
  fi

  missing="$(missing_tools)"
  if [ -n "$missing" ]; then
    log "ERROR: required build tool(s) still missing and could not be installed (no usable apt/sudo in this environment):$missing"
    exit 1
  fi
  log "All required build deps present after apt attempt"
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
  if [ -d "${OPAMROOT:-$HOME/.opam}" ]; then
    # An existing root (e.g. a developer machine) is left as it is; only its package index is refreshed.
    log "opam root already initialized; not re-initializing"
  else
    log "Initializing opam (non-interactive, sandboxing disabled)"
    opam init -y --bare --disable-sandboxing
  fi

  opam repo add default https://opam.ocaml.org -y >/dev/null 2>&1 || true
  opam update -y
}

ensure_opam_switch() {
  if opam switch list --short 2>/dev/null | grep -qx "$OPAM_SWITCH"; then
    log "opam switch already exists: $OPAM_SWITCH"
  else
    log "Creating opam switch $OPAM_SWITCH with $OCAML_COMPILER"
    opam switch create "$OPAM_SWITCH" "$OCAML_COMPILER" -y
  fi
  eval "$(opam env --switch="$OPAM_SWITCH" --set-switch)"
}

ensure_fasmifra() {
  log "Installing fasmifra.${FASMIFRA_VERSION} into switch $OPAM_SWITCH"
  # rdkit is used through python, not as an opam library: fake the conf package so opam does not
  # try to install a system rdkit.
  opam install --switch="$OPAM_SWITCH" --fake -y conf-rdkit >/dev/null 2>&1 || true
  opam install --switch="$OPAM_SWITCH" -y "fasmifra.${FASMIFRA_VERSION}"

  # Use this switch's binary explicitly, never whatever `fasmifra` happens to be first on PATH.
  FASMIFRA_BIN="$(opam var bin --switch="$OPAM_SWITCH")/fasmifra"
  if [ ! -x "$FASMIFRA_BIN" ]; then
    log "ERROR: $FASMIFRA_BIN not found after installing fasmifra.${FASMIFRA_VERSION}"
    exit 1
  fi
  log "fasmifra installed (opam): $FASMIFRA_BIN"

  # The version cannot be queried from the CLI; fasmifra 2.x writes atom-map tags, 1.x isotope tags.
  # (no grep -q here: under pipefail it would make strings die of SIGPIPE and fail the check)
  if ! strings "$FASMIFRA_BIN" | grep -F '[*:%d]' >/dev/null; then
    log "ERROR: $FASMIFRA_BIN does not use atom-map tags ([*:i]); wrong fasmifra version for this model."
    exit 1
  fi
}

persist_fasmifra_into_python_prefix() {
  # opam installs fasmifra into its own switch directory (e.g. ~/.opam/default/bin),
  # which lives outside the conda environment. Ersilia's packaging only preserves
  # the conda environment's own directory tree, so opam's switch is discarded and
  # fasmifra ends up missing (not just off PATH) in the final packaged image.
  # Copying the binary into that conda environment's own bin dir bakes it into
  # the tree that actually survives.
  #
  # This script's own PATH override above (and apt-installing its own python3)
  # means a bare `python3` here is not reliable for finding the *target* conda
  # env -- use $CONDA_PREFIX directly, which ersilia sets before running this
  # script (it activates the environment first). Only fall back to python3's
  # own prefix for manual/local runs where CONDA_PREFIX isn't set.
  local src prefix_bin
  src="$FASMIFRA_BIN"
  if [ -n "${CONDA_PREFIX:-}" ]; then
    prefix_bin="$CONDA_PREFIX/bin"
  else
    log "WARN: CONDA_PREFIX not set, falling back to python3's own prefix"
    prefix_bin="$(python3 -c 'import sys; print(sys.prefix)')/bin"
  fi
  log "fasmifra source: $src"
  log "Target prefix bin dir (CONDA_PREFIX=${CONDA_PREFIX:-unset}): $prefix_bin"
  if [ "$(dirname "$src")" = "$prefix_bin" ]; then
    log "fasmifra already inside the target bin dir: $src"
    return 0
  fi
  log "Copying fasmifra into: $prefix_bin (overwriting any other version already there)"
  mkdir -p "$prefix_bin"
  cp -L "$src" "$prefix_bin/fasmifra"
  chmod +x "$prefix_bin/fasmifra"
  if ! strings "$prefix_bin/fasmifra" | grep -F '[*:%d]' >/dev/null; then
    log "ERROR: the copied binary does not use atom-map tags ([*:i])"
    exit 1
  fi
  log "Copied fasmifra.${FASMIFRA_VERSION} into $prefix_bin"
}

sanity() {
  log "Sanity checks"
  log "opam: $(opam --version)"
  log "switch: $(opam switch show || true)"
  log "python: $(python3 --version)"
  log "pip: $(python3 -m pip --version)"
  log "fasmifra (pinned ${FASMIFRA_VERSION}, opam switch $OPAM_SWITCH): $FASMIFRA_BIN"
  log "fasmifra first on PATH: $(command -v fasmifra || echo 'NOT FOUND')"
}

main() {
  ensure_apt_deps
  ensure_opam
  ensure_opam_initialized
  ensure_opam_switch
  ensure_fasmifra
  persist_fasmifra_into_python_prefix

  log "fasmifra_fragment.py check (optional)"
  command -v fasmifra_fragment.py >/dev/null 2>&1 && log "found: $(command -v fasmifra_fragment.py)" || log "not on PATH (ok if referenced by full path)"

  sanity
  log "Done."
}

main "$@"
