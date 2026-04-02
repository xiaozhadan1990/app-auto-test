#!/usr/bin/env bash
# macOS 等价于 start_dev_all.ps1：同步依赖（可选）、释放端口、在新终端标签页启动后端与前端。
set -euo pipefail

NO_INSTALL=false
FRONTEND_PORT=5173

usage() {
  echo "Usage: $0 [--no-install] [--frontend-port N | -p N]" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-install)
      NO_INSTALL=true
      shift
      ;;
    -p|--frontend-port)
      [[ $# -ge 2 ]] || usage
      FRONTEND_PORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      ;;
  esac
done

get_env_value_from_file() {
  local file_path="$1" key="$2"
  [[ -f "$file_path" ]] || return 0
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    local line="${raw_line#"${raw_line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
    [[ "$line" == *=* ]] || continue
    local k="${line%%=*}"
    k="${k%"${k##*[![:space:]]}"}"
    k="${k#"${k%%[![:space:]]*}"}"
    [[ "$k" != "$key" ]] && continue
    local v="${line#*=}"
    v="${v#"${v%%[![:space:]]*}"}"
    v="${v%"${v##*[![:space:]]}"}"
    v="${v%\"}"
    v="${v#\"}"
    v="${v%\'}"
    v="${v#\'}"
    printf '%s' "$v"
    return 0
  done < "$file_path"
  return 0
}

stop_port_owners() {
  local port="$1" label="$2"
  local pids
  pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    echo "[$label] Port $port is free."
    return 0
  fi
  echo "[$label] Port $port is occupied, stopping processes..."
  for pid in $pids; do
    local name
    name="$(ps -p "$pid" -o comm= 2>/dev/null | tr -d '[:space:]' || echo "<unknown>")"
    echo "  stopping PID=$pid, Name=$name"
    kill -9 "$pid" 2>/dev/null || true
  done
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
WEB_UI_ROOT="$PROJECT_ROOT/web-ui"
ENV_PATH="$PROJECT_ROOT/.env"

if [[ ! -d "$WEB_UI_ROOT" ]]; then
  echo "[ERROR] web-ui directory not found." >&2
  exit 1
fi

BACKEND_HOST="$(get_env_value_from_file "$ENV_PATH" "DESKTOP_WEB_HOST")"
[[ -z "$BACKEND_HOST" ]] && BACKEND_HOST="127.0.0.1"
BACKEND_PORT_RAW="$(get_env_value_from_file "$ENV_PATH" "DESKTOP_WEB_PORT")"
BACKEND_PORT=17999
if [[ -n "$BACKEND_PORT_RAW" ]] && [[ "$BACKEND_PORT_RAW" =~ ^[0-9]+$ ]]; then
  BACKEND_PORT="$BACKEND_PORT_RAW"
fi

echo "Project root : $PROJECT_ROOT"
echo "Backend host : $BACKEND_HOST"
echo "Backend port : $BACKEND_PORT"
echo "Frontend port: $FRONTEND_PORT"

stop_port_owners "$BACKEND_PORT" "backend"
stop_port_owners "$FRONTEND_PORT" "frontend"

if [[ "$NO_INSTALL" != true ]]; then
  echo "[backend] Syncing Python dependencies with uv..."
  (cd "$PROJECT_ROOT" && uv sync)
  if [[ ! -d "$WEB_UI_ROOT/node_modules" ]]; then
    echo "[frontend] Installing dependencies (yarn install)..."
    (cd "$WEB_UI_ROOT" && yarn install)
  fi
fi

backend_shell_cmd="cd $(printf '%q' "$PROJECT_ROOT") && uv run python desktop_web_app.py"
frontend_shell_cmd="cd $(printf '%q' "$WEB_UI_ROOT") && yarn dev"

echo "[backend] Starting desktop_web_app.py with uv (waitress preferred)..."
echo "[frontend] Starting yarn dev..."

osascript <<EOF
tell application "Terminal"
  activate
  do script "$backend_shell_cmd"
  delay 0.5
  do script "$frontend_shell_cmd"
end tell
EOF

echo ""
echo "Started:"
echo "  Backend : http://${BACKEND_HOST}:${BACKEND_PORT} (served by waitress when available)"
echo "  Frontend: http://127.0.0.1:${FRONTEND_PORT}"
echo ""
echo "Tip: use --no-install to skip dependency check."
