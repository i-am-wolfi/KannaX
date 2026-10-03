# Kanna-X no Termux (Android)

Testado como alvo: Android ARM64, Termux do F-Droid (não use a versão da Play Store, está desatualizada).

## 1. Pacotes do sistema

```bash
pkg update -y
pkg install -y python git ffmpeg jq curl tmux libjpeg-turbo zlib openssl
# pré-compilados do Termux (evitam compilar via pip, que quebra):
pkg install -y python-numpy python-pillow python-lxml python-psutil
```

> `tgcrypto` foi removido do `requirements-termux.txt` (não compila bem no
> clang do Termux; o pyrogram usa implementação Python pura — mais lento,
> funciona). `selenium`, `opencv` e `scikit-image` também ficaram de fora
> (sem Chrome no Android; builds pesados).

## 2. Clonar e instalar

```bash
git clone https://github.com/i-am-wolfi/KannaX
cd KannaX
python -m venv --system-site-packages .venv   # enxerga os python-* do pkg
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-termux.txt
```

Se algo falhar compilando, tente a versão binária:

```bash
pip install --only-binary :all: -r requirements-termux.txt
```

## 3. Configurar

Copie `config.env.sample` para `config.env` e preencha no mínimo:

- `API_ID` / `API_HASH` (https://my.telegram.org)
- `HU_STRING_SESSION` (gere com `python tools/genStrSession.py`)
- `DATABASE_URL` (MongoDB Atlas — o bot não usa banco local)
- `LOG_CHANNEL_ID`
- `WORKERS` pode ficar vazio

## 4. Rodar (mantendo vivo)

```bash
termux-wake-lock
tmux new -s kanna
./run-kanna.sh start
# Ctrl+B, D para destacar; `tmux attach -t kanna` para voltar
```

- Tire o Termux da otimização de bateria do Android.
- Deixe carregando de preferência.

## 5. Limitações conhecidas no Termux

| Recurso | Estado |
|---|---|
| Comandos gerais, alive, mute, admin | OK |
| `carbon`, `webss` | Quebrados (precisam de Chrome) |
| `kang`, stickers com cv2 | Parcial (sem opencv) |
| Velocidade cripto (sem tgcrypto) | Um pouco mais lento |
| Boot (121 plugins) | Pesado; celular com 4GB+ RAM recomendado |

Para 24/7 considere um VPS — o `Dockerfile` do repo já está pronto para isso.
