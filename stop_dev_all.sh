#!/usr/bin/env bash
# macOS 等价于 stop_dev_all.ps1：结束占用后端/前端端口的监听进程。
set -euo pipefail

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

stop_port_listeners() {
  local port="$1" label="$2"
  local pids
  pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    echo "[$label] Port $port has no listener."
    return 0
  fi
  echo "[$label] Stopping listeners on port $port ..."
  for pid in $pids; do
    local name
    name="$(ps -p "$pid" -o comm= 2>/dev/null | tr -d '[:space:]' || echo "<unknown>")"
    echo "  stopping PID=$pid, Name=$name"
    kill -9 "$pid" 2>/dev/null || true
  done
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PATH="$SCRIPT_DIR/.env"

BACKEND_PORT_RAW="$(get_env_value_from_file "$ENV_PATH" "DESKTOP_WEB_PORT")"
BACKEND_PORT=17999
if [[ -n "$BACKEND_PORT_RAW" ]] && [[ "$BACKEND_PORT_RAW" =~ ^[0-9]+$ ]]; then
  BACKEND_PORT="$BACKEND_PORT_RAW"
fi

stop_port_listeners "$BACKEND_PORT" "backend"
stop_port_listeners 5173 "frontend"
stop_port_listeners 5174 "frontend-alt"

echo "Done."
