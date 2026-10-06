#!/data/data/com.termux/files/usr/bin/bash
# Instalador Kanna-X para Termux (uma linha):
#   curl -sL https://raw.githubusercontent.com/i-am-wolfi/KannaX/master/install-termux.sh | bash
# Idempotente: clona ou atualiza, depois roda o setup completo.
set -u

REPO="https://github.com/i-am-wolfi/KannaX"
DIR="$HOME/KannaX"

echo "ℹ️  atualizando pkg e instalando git/curl..."
pkg update -y
pkg install -y git curl

if [[ -d "$DIR/.git" ]]; then
    echo "ℹ️  repo existe, atualizando..."
    git -C "$DIR" pull
else
    echo "ℹ️  clonando Kanna-X..."
    git clone "$REPO" "$DIR" || { echo "❌ falha no clone"; exit 1; }
fi

cd "$DIR" || exit 1
bash setup-termux.sh
