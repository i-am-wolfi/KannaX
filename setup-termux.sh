#!/data/data/com.termux/files/usr/bin/bash
# setup-termux.sh — prepara o Kanna-X no Termux (Android) do zero.
# Uso: bash setup-termux.sh
# Faz: pkg deps + venv + requirements-termux.txt + config.env inicial.

set -u

die() { echo "❌ $*" >&2; exit 1; }
ok()  { echo "✅ $*"; }
info(){ echo "ℹ️  $*"; }

# 0. checar termux ---------------------------------------------------------
[[ -d /data/data/com.termux ]] || die "rode este script dentro do Termux (Android)."
command -v pkg >/dev/null 2>&1 || die "comando 'pkg' não encontrado."

# 1. pacotes do sistema ----------------------------------------------------
# Deps Python com build nativo pesado: usa os pacotes PRÉ-COMPILADOS do
# Termux (python-*) em vez de compilar via pip — pip tentando compilar
# por cima desses quebra. A venv abaixo usa --system-site-packages para
# enxergá-los, e o pip os considera satisfeitos.
PKG_PYTHON_DEPS="python-numpy python-pillow python-lxml python-psutil python-cryptography"

info "atualizando pacotes..."
pkg update -y || die "falha no pkg update"

info "instalando dependências do sistema..."
pkg install -y python git jq curl tmux libjpeg-turbo zlib openssl clang \
    $PKG_PYTHON_DEPS \
    || die "falha no pkg install"
# NOTA: ffmpeg removido temporariamente (travava a instalação no Termux).
# Plugins de mídia que precisam dele (conversões, voice, etc.) ficam
# degradados até reinstalar: pkg install ffmpeg

# 2. venv ------------------------------------------------------------------
# --system-site-packages: enxerga os python-* instalados via pkg acima,
# então o pip não tenta recompilar numpy/Pillow/lxml/psutil.
if [[ ! -x .venv/bin/python ]]; then
    info "criando venv (com acesso aos pacotes do sistema)..."
    python -m venv --system-site-packages .venv || die "falha ao criar venv"
    ok "venv criada"
else
    ok "venv já existe"
fi
# shellcheck disable=SC1090
source .venv/bin/activate
pip install -q --upgrade pip || die "falha no pip"

# 3. dependências python ----------------------------------------------------
info "instalando requirements-termux.txt (pode demorar)..."
if ! pip install -r requirements-termux.txt; then
    info "tentando só com pacotes binários..."
    pip install --only-binary :all: -r requirements-termux.txt \
        || die "falha ao instalar requirements"
fi
ok "dependências instaladas"

# 4. config.env -------------------------------------------------------------
if [[ ! -f config.env ]]; then
    if [[ -f config.env.sample ]]; then
        cp config.env.sample config.env
        chmod 600 config.env
        info "config.env criado a partir do sample (EDITÁVEL: preencha API_ID, API_HASH, HU_STRING_SESSION, DATABASE_URL, LOG_CHANNEL_ID)"
    else
        info "config.env.sample não encontrado, pulei."
    fi
else
    ok "config.env já existe (não mexi)"
fi

# 5. shim asyncio (python 3.10+) --------------------------------------------
if [[ -f tools/py314/sitecustomize.py ]]; then
    export PYTHONPATH="$PWD/tools/py314:${PYTHONPATH:-}"
    ok "shim asyncio ativado"
fi

echo
ok "pronto! próximos passos:"
echo "  1. edite o config.env: nano config.env"
echo "  2. gere a sessão se precisar: .venv/bin/python tools/genStrSession.py"
echo "  3. mantenha acordado: termux-wake-lock"
echo "  4. rode em tmux: tmux new -s kanna"
echo "  5. inicie: ./run-kanna.sh start"
