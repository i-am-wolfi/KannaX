#!/bin/bash
# run-kanna.sh — roda o Kanna-X de forma fácil (Python 3.14 + VARs do Cat)
# Uso: ./run-kanna.sh {start|stop|restart|status|logs|console|genstr|setup}
# Rode ./setup-kanna.sh primeiro (uma vez).

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
PY="$VENV/bin/python"
PIDFILE="$DIR/kannax.pid"
LOGFILE="$DIR/logs/kannax.log"
ENV_FILE="$DIR/config.env"

die() { echo "❌ $*" >&2; exit 1; }
ok()  { echo "✅ $*"; }

is_running() {
  [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

need_setup() {
  [[ -x "$PY" ]] || die "venv não encontrada. Rode: ./setup-kanna.sh"
  [[ -f "$ENV_FILE" ]] || die "config.env não encontrado. Rode: ./setup-kanna.sh"
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
  # PATH: venv + jq local + shim asyncio via PYTHONPATH
  export PATH="$VENV/bin:$DIR/tools/bin:$PATH"
  export PYTHONPATH="$DIR/tools/py314:${PYTHONPATH:-}"
  export MOTOR_MAX_WORKERS="${WORKERS:-}"
}

check_required() {
  local missing=()
  [[ -z "${API_ID:-}" ]] && missing+=("API_ID")
  [[ -z "${API_HASH:-}" ]] && missing+=("API_HASH")
  [[ -z "${DATABASE_URL:-}" ]] && missing+=("DATABASE_URL (MongoDB Atlas: https://cloud.mongodb.com/)")
  [[ -z "${LOG_CHANNEL_ID:-}" ]] && missing+=("LOG_CHANNEL_ID")
  if [[ -z "${HU_STRING_SESSION:-}" && -z "${BOT_TOKEN:-}" ]]; then
    missing+=("HU_STRING_SESSION ou BOT_TOKEN (gere a sessão com ./run-kanna.sh genstr)")
  fi
  if [[ -n "${BOT_TOKEN:-}" && -z "${OWNER_ID:-}" ]]; then
    missing+=("OWNER_ID (obrigatório com BOT_TOKEN)")
  fi
  if ((${#missing[@]})); then
    echo "❌ Faltam variáveis no config.env:" >&2
    printf '   - %s\n' "${missing[@]}" >&2
    exit 1
  fi
}

cmd_start() {
  need_setup; load_env; check_required
  if is_running; then ok "Kanna-X já rodando (PID $(cat "$PIDFILE"))"; return 0; fi
  cd "$DIR" || die "não consegui entrar em $DIR"
  mkdir -p logs downloads
  echo "🚀 Iniciando Kanna-X ..."
  nohup bash run >>"$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 6
  if is_running; then
    ok "Kanna-X rodando (PID $(cat "$PIDFILE")). Veja: ./run-kanna.sh logs"
  else
    rm -f "$PIDFILE"
    echo "❌ falhou ao iniciar. Últimas linhas:" >&2
    tail -25 "$LOGFILE" >&2
    exit 1
  fi
}

cmd_stop() {
  if ! is_running; then rm -f "$PIDFILE"; echo "Kanna-X já está parado."; return 0; fi
  echo "🛑 Parando Kanna-X (PID $(cat "$PIDFILE"))..."
  kill -TERM "$(cat "$PIDFILE")" 2>/dev/null
  for _ in $(seq 1 15); do is_running || break; sleep 1; done
  is_running && kill -9 "$(cat "$PIDFILE")" 2>/dev/null
  sleep 1
  # the wrapper spawns children (bash -c ... runKannaX + python -m kannax)
  # that TERM sometimes misses; sweep leftovers so restarts don't stack
  pkill -9 -f "runKannaX" 2>/dev/null
  pkill -9 -f "python[0-9.]* -m kannax" 2>/dev/null
  rm -f "$PIDFILE"
  ok "Kanna-X parado."
}

cmd_status() {
  if is_running; then
    ok "Kanna-X RODANDO (PID $(cat "$PIDFILE"))"
    ps -o pid,etime,cmd -p "$(cat "$PIDFILE")"
  else
    echo "⏸️  Kanna-X PARADO."
  fi
}

cmd_logs() {
  tail -n "${1:-50}" -f "$LOGFILE" 2>/dev/null || die "sem log ainda ($LOGFILE)"
}

cmd_console() {
  need_setup; load_env; check_required
  cd "$DIR" || exit 1
  mkdir -p logs downloads
  exec bash run
}

cmd_genstr() {
  need_setup
  export PATH="$VENV/bin:$PATH"
  export PYTHONPATH="$DIR/tools/py314:${PYTHONPATH:-}"
  cd "$DIR" || exit 1
  exec "$PY" tools/genStrSession.py
}

case "${1:-}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_stop; sleep 2; cmd_start ;;
  status)  cmd_status ;;
  logs)    cmd_logs "${2:-50}" ;;
  console) cmd_console ;;
  genstr)  cmd_genstr ;;
  setup)   exec "$DIR/setup-kanna.sh" ;;
  *)
    echo "Uso: $0 {start|stop|restart|status|logs [N]|console|genstr|setup}"
    echo "  setup   - (re)executa o setup: venv + deps + config.env do Cat"
    echo "  genstr  - gera HU_STRING_SESSION (Pyrogram) — use o api_id/hash do Cat"
    echo "  start   - inicia em segundo plano (log: logs/kannax.log)"
    echo "  stop    - para o bot"
    echo "  restart - reinicia"
    echo "  status  - mostra se está rodando"
    echo "  logs    - últimas N linhas do log (padrão 50, com -f)"
    echo "  console - roda em primeiro plano (debug)"
    exit 1 ;;
esac
