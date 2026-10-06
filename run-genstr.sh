#!/bin/bash
# run-genstr.sh — gera a HU_STRING_SESSION (Pyrogram) do Kanna-X.
# Usa venv isolada .venv-genstr com pyrogram v2, porque o Telegram
# bloqueia logins novos no pyrogram 1.4.16 (406 UPDATE_APP_TO_LOGIN).
# A string gerada serve no bot normalmente.
# Uso: bash run-genstr.sh
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENV="$DIR/.venv-genstr"
cd "$DIR" || exit 1
if [[ ! -x "$GENV/bin/python" ]]; then
    echo "ℹ️  criando venv do gerador (só na primeira vez)..."
    python -m venv "$GENV" || { echo "❌ falha ao criar venv"; exit 1; }
    "$GENV/bin/pip" install -q --upgrade pip
    "$GENV/bin/pip" install -q "pyrogram>=2" tgcrypto || "$GENV/bin/pip" install -q "pyrogram>=2" \
        || { echo "❌ falha ao instalar pyrogram v2"; exit 1; }
fi
PYTHONPATH="$DIR/tools/py314:${PYTHONPATH:-}" "$GENV/bin/python" tools/genStrSession.py
