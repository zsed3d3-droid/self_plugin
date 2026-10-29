#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/.runtime"
REV=9e3308f65adf547b7e4776e5ed22467a2649d2ee
mkdir -p "$RUNTIME"
if [ ! -d "$RUNTIME/gstack/.git" ]; then
  git clone https://github.com/garrytan/gstack.git "$RUNTIME/gstack"
  git -C "$RUNTIME/gstack" checkout "$REV"
fi
[ "$(git -C "$RUNTIME/gstack" rev-parse HEAD)" = "$REV" ] || { echo 'gstack revision differs; inspect before upgrading' >&2; exit 1; }
if ! command -v bun >/dev/null 2>&1; then
  npm install --prefix "$RUNTIME/tools" --no-audit --no-fund bun@1.4.2
  (cd "$RUNTIME/tools/node_modules/bun" && node install.js)
  export PATH="$RUNTIME/tools/node_modules/.bin:$PATH"
fi
cd "$RUNTIME/gstack"
# Skip unrelated CSO native compiler and OS-level package installation.
GSTACK_SKIP_COREUTILS=1 GSTACK_SKIP_FONTS=1 GSTACK_SKIP_ASIDE=1 GSTACK_SETUP_SKIP_CSO_BUILD=1 ./setup --host cursor --prefix --no-harness-auto "$@"
