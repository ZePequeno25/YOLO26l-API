#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  exec python3 launcher.py
fi

if command -v python >/dev/null 2>&1; then
  exec python launcher.py
fi

echo "Python 3 nao encontrado. Instale o Python 3 e execute novamente."
exit 1
