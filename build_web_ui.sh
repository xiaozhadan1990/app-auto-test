#!/usr/bin/env bash
# macOS / Unix 等价于 build_web_ui.bat：构建前端、打包 PyInstaller one-dir 产物。
set -euo pipefail

APP_NAME="mobile-auto-test-ui"
INSTALL_DEPS=0
NPM_CMD="${NPM_CMD:-npm}"
UV_CMD="${UV_CMD:-uv}"
UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"

usage() {
  echo "Usage: $0 [--install]" >&2
  echo "  --install  同步 uv、安装前端依赖后再构建（否则仅在缺少 node_modules 时安装）" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      INSTALL_DEPS=1
      shift
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PROJECT_ROOT="$PWD"
FRONTEND_DIR="$PROJECT_ROOT/web-ui"
UI_DIR="$PROJECT_ROOT/ui"
DIST_DIR="$PROJECT_ROOT/dist/$APP_NAME"
BUILD_DIR="$PROJECT_ROOT/build/$APP_NAME"

# PyInstaller --add-data 在 Windows 用 ;，在 macOS/Linux 用 :
DATA_SEP=":"

echo "============================================================"
echo " Flask Web UI build script"
echo " APP_NAME       : $APP_NAME"
echo " INSTALL_DEPS   : $INSTALL_DEPS"
echo " PACKAGE_ADB    : NO"
echo " PACKAGE_APPIUM : NO"
echo " PYTHON_TOOL    : $UV_CMD"
echo " UV_CACHE_DIR   : $UV_CACHE_DIR"
echo " FRONTEND_DIR   : $FRONTEND_DIR"
echo "============================================================"
echo

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  echo "[Step] Syncing Python dependencies with uv..."
  "$UV_CMD" sync --cache-dir "$UV_CACHE_DIR"
fi

echo "[Step] Checking uv / Node.js / npm..."
command -v "$UV_CMD" >/dev/null 2>&1 || {
  echo "[ERROR] uv is required but not found in PATH" >&2
  exit 1
}
command -v node >/dev/null 2>&1 || {
  echo "[ERROR] node is required but not found in PATH" >&2
  exit 1
}
command -v "$NPM_CMD" >/dev/null 2>&1 || {
  echo "[ERROR] npm is required but not found in PATH" >&2
  exit 1
}

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "[ERROR] Frontend project not found: $FRONTEND_DIR/package.json" >&2
  exit 1
fi

echo "[Step] Building frontend UI..."
pushd "$FRONTEND_DIR" >/dev/null
if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  echo "[Step] Installing frontend dependencies..."
  "$NPM_CMD" install
else
  if [[ ! -d node_modules ]]; then
    echo "[Step] node_modules not found, installing frontend dependencies..."
    "$NPM_CMD" install
  fi
fi

"$NPM_CMD" run build
popd >/dev/null

if [[ ! -f "$UI_DIR/index.html" ]]; then
  echo "[ERROR] Frontend output missing: $UI_DIR/index.html" >&2
  exit 1
fi

echo "[Step] Installing PyInstaller..."
"$UV_CMD" sync --cache-dir "$UV_CACHE_DIR"

echo "[Step] Stopping running packaged app if exists..."
killall -9 "$APP_NAME" 2>/dev/null || true

echo "[Step] Cleaning previous build outputs..."
if [[ -d "$DIST_DIR" ]]; then
  rm -rf "$DIST_DIR"
  if [[ -d "$DIST_DIR" ]]; then
    echo "[ERROR] Failed to remove old dist output: $DIST_DIR" >&2
    echo "        Please close the packaged app and retry." >&2
    exit 1
  fi
fi
if [[ -d "$BUILD_DIR" ]]; then
  rm -rf "$BUILD_DIR"
  if [[ -d "$BUILD_DIR" ]]; then
    echo "[ERROR] Failed to remove old build output: $BUILD_DIR" >&2
    echo "        Please close any process locking files under that directory and retry." >&2
    exit 1
  fi
fi

if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp -f .env.example .env
fi

echo "[Step] Running PyInstaller..."
PYARGS=(--noconfirm --clean --onedir --name "$APP_NAME")
PYARGS+=(--add-data "ui${DATA_SEP}ui")
PYARGS+=(--add-data "tests${DATA_SEP}tests")
PYARGS+=(--add-data "conftest.py${DATA_SEP}.")
PYARGS+=(--add-data "pytest.ini${DATA_SEP}.")
PYARGS+=(--collect-all appium)
PYARGS+=(--collect-all selenium)
[[ -f .env ]] && PYARGS+=(--add-data ".env${DATA_SEP}.")
[[ -f .env.example ]] && PYARGS+=(--add-data ".env.example${DATA_SEP}.")

"$UV_CMD" run --with pyinstaller --cache-dir "$UV_CACHE_DIR" pyinstaller "${PYARGS[@]}" desktop_web_app.py

DIST_APP="$PROJECT_ROOT/dist/$APP_NAME"
if [[ -d "$DIST_APP" ]]; then
  echo "[Step] Copying runtime env files..."
  [[ -f .env ]] && cp -f .env "$DIST_APP/.env"
  [[ -f .env.example ]] && cp -f .env.example "$DIST_APP/.env.example"
fi

echo
echo "============================================================"
echo " Build completed"
echo " Output: $DIST_APP"
echo "============================================================"
