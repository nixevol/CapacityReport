#!/usr/bin/env sh
set -eu

TARGET="${1:-server}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
DESKTOP_API_BASE="http://127.0.0.1:19082"
cd "$ROOT"

log() {
  printf '\n==> %s\n' "$1"
}

run() {
  printf '    %s\n' "$*"
  "$@"
}

platform_name() {
  case "$(uname -s)" in
    Darwin) printf 'macos' ;;
    Linux) printf 'linux' ;;
    *) printf 'windows' ;;
  esac
}

ensure_python() {
  log "Preparing Python environment"
  if [ ! -x ".venv/bin/python" ]; then
    run uv venv
  fi
  run uv pip install -r requirements.txt
  run uv pip install pyinstaller
}

build_frontend() {
  log "Building frontend"
  if [ ! -d "frontend/node_modules" ]; then
    (cd frontend && run npm ci)
  fi
  if [ "${1:-}" = "desktop" ]; then
    (cd frontend && VITE_API_BASE="$DESKTOP_API_BASE" run npm run build)
  else
    (cd frontend && run npm run build)
  fi
}

build_server_binary() {
  mode="${1:-onedir}"
  ensure_python
  log "Building server binary"
  rm -rf build/pyinstaller
  if [ "$mode" = "onefile" ]; then
    CAPAREPORT_ONEFILE=1
    export CAPAREPORT_ONEFILE
    run .venv/bin/python -m PyInstaller --clean --noconfirm \
      --workpath build/pyinstaller/work \
      --distpath build/pyinstaller/dist \
      build/capareport-server.spec
    unset CAPAREPORT_ONEFILE
  else
    run .venv/bin/python -m PyInstaller --clean --noconfirm \
      --workpath build/pyinstaller/work \
      --distpath build/pyinstaller/dist \
      build/capareport-server.spec
  fi
}

write_launchers() {
  out_dir="$1"
  exe_name="$2"
  cat > "$out_dir/start.sh" <<EOF
#!/usr/bin/env sh
set -eu
SCRIPT_DIR="\$(CDPATH= cd -- "\$(dirname -- "\$0")" && pwd)"
cd "\$SCRIPT_DIR"
mkdir -p cache logs
chmod +x "./$exe_name" 2>/dev/null || true
echo "Starting CapacityReport server..."
echo "URL: http://localhost:9081"
exec "./$exe_name" --host 0.0.0.0 --port 9081
EOF
  chmod +x "$out_dir/start.sh"
}

build_server() {
  platform="$(platform_name)"
  build_frontend server
  build_server_binary onedir

  out_dir="dist/packages/CapacityReport-Server-$platform-x64"
  rm -rf "$out_dir"
  mkdir -p "$out_dir/cache" "$out_dir/logs" "$out_dir/frontend"
  cp -R build/pyinstaller/dist/capareport-server/. "$out_dir/"
  cp Configure.json ReportScript.sql "$out_dir/"
  cp -R frontend/dist "$out_dir/frontend/"
  write_launchers "$out_dir" "capareport-server"
  (cd "$out_dir/.." && tar -czf "$(basename "$out_dir").tar.gz" "$(basename "$out_dir")")
  log "Server package: $out_dir"
}

build_docker() {
  log "Building Docker image"
  run docker build --progress=plain -f build/Dockerfile -t capacity-report-app:latest .
  run docker compose -f build/docker-compose.yml config
}

build_desktop() {
  build_frontend desktop
  build_server_binary onefile
  triple="$(rustc -vV | awk '/^host:/ {print $2}')"
  mkdir -p src-tauri/binaries
  cp build/pyinstaller/dist/capareport-server "src-tauri/binaries/capareport-server-$triple"
  if ! cargo tauri --version >/dev/null 2>&1; then
    run cargo install tauri-cli --locked
  fi
  (cd src-tauri && run cargo tauri build)
}

case "$TARGET" in
  server) build_server ;;
  docker) build_docker ;;
  desktop) build_desktop ;;
  all) build_server; build_docker; build_desktop ;;
  *) echo "Usage: scripts/build.sh [server|docker|desktop|all]" >&2; exit 1 ;;
esac

log "Build finished"
