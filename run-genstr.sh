#!/bin/bash
# run-genstr.sh — gera a HU_STRING_SESSION (Pyrogram) do Kanna-X.
# Uso: bash run-genstr.sh
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -x "$DIR/.venv/bin/python" ]] || { echo "❌ venv não encontrada. Rode o install-termux.sh primeiro."; exit 1; }
cd "$DIR" || exit 1
PYTHONPATH="$DIR/tools/py314:${PYTHONPATH:-}" .venv/bin/python tools/genStrSession.py
