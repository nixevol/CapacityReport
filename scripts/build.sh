#!/usr/bin/env sh
set -eu

TARGET="${1:-server}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$ROOT/dist"
SERVER_DIST_DIR="$DIST_DIR/server"
DESKTOP_DIST_DIR="$DIST_DIR/desktop"
DOCKER_DIST_DIR="$DIST_DIR/docker"
TMP_DIR="$DIST_DIR/.tmp"
PYINSTALLER_DIR="$TMP_DIR/pyinstaller"
PACKAGING_DIR="$ROOT/packaging"
DESKTOP_API_BASE="http://127.0.0.1:9081"
SERVER_NAME="capareport-server"
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

server_exe_name() {
  case "$(platform_name)" in
    windows) printf '%s.exe' "$SERVER_NAME" ;;
    *) printf '%s' "$SERVER_NAME" ;;
  esac
}

clean_intermediates() {
  log "Cleaning intermediate output"
  rm -rf "$TMP_DIR" "$ROOT/frontend/dist" "$ROOT/src-tauri/binaries" "$ROOT/src-tauri/target"
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
  rm -rf "$PYINSTALLER_DIR"
  mkdir -p "$PYINSTALLER_DIR"

  if [ "$mode" = "onefile" ]; then
    CAPAREPORT_ONEFILE=1
    export CAPAREPORT_ONEFILE
    run .venv/bin/python -m PyInstaller --clean --noconfirm \
      --workpath "$PYINSTALLER_DIR/work" \
      --distpath "$PYINSTALLER_DIR/dist" \
      "$PACKAGING_DIR/capareport-server.spec"
    unset CAPAREPORT_ONEFILE
  else
    run .venv/bin/python -m PyInstaller --clean --noconfirm \
      --workpath "$PYINSTALLER_DIR/work" \
      --distpath "$PYINSTALLER_DIR/dist" \
      "$PACKAGING_DIR/capareport-server.spec"
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
  exe_name="$(server_exe_name)"
  out_dir="$SERVER_DIST_DIR/CapacityReport-Server-$platform-x64"
  rm -rf "$out_dir" "$SERVER_DIST_DIR/$(basename "$out_dir").tar.gz"

  build_frontend server
  build_server_binary onedir

  mkdir -p "$out_dir/cache" "$out_dir/logs" "$out_dir/frontend"
  cp -R "$PYINSTALLER_DIR/dist/$SERVER_NAME/." "$out_dir/"
  cp Configure.json ReportScript.sql "$out_dir/"
  cp -R frontend/dist "$out_dir/frontend/"
  write_launchers "$out_dir" "$exe_name"
  (cd "$SERVER_DIST_DIR" && tar -czf "$(basename "$out_dir").tar.gz" "$(basename "$out_dir")")
  log "Server package: $out_dir"
}

copy_docker_bundle() {
  rm -rf "$DOCKER_DIST_DIR"
  mkdir -p "$DOCKER_DIST_DIR/cache" "$DOCKER_DIST_DIR/logs"
  cp "$PACKAGING_DIR/docker-compose.yml" "$DOCKER_DIST_DIR/docker-compose.yml"
  cp Configure.json ReportScript.sql "$DOCKER_DIST_DIR/"
  cp -R "$PACKAGING_DIR/mysql" "$DOCKER_DIST_DIR/mysql"
}

build_docker() {
  rm -rf "$DOCKER_DIST_DIR"

  log "Building Docker image"
  run docker build --progress=plain -f "$PACKAGING_DIR/Dockerfile" -t capacity-report-app:latest .
  log "Packaging Docker output"
  copy_docker_bundle
  run docker save -o "$DOCKER_DIST_DIR/capacity-report-app-latest.tar" capacity-report-app:latest
  run docker compose -f "$DOCKER_DIST_DIR/docker-compose.yml" config
  log "Docker package: $DOCKER_DIST_DIR"
}

build_desktop() {
  rm -rf "$DESKTOP_DIST_DIR"

  build_frontend desktop
  build_server_binary onefile
  triple="$(rustc -vV | awk '/^host:/ {print $2}')"
  mkdir -p src-tauri/binaries
  cp "$PYINSTALLER_DIR/dist/$(server_exe_name)" "src-tauri/binaries/$SERVER_NAME-$triple"
  if ! cargo tauri --version >/dev/null 2>&1; then
    run cargo install tauri-cli --locked
  fi
  rm -rf src-tauri/target/release/bundle
  (cd src-tauri && run cargo tauri build)

  rm -rf "$DESKTOP_DIST_DIR"
  mkdir -p "$DESKTOP_DIST_DIR"
  find src-tauri/target/release/bundle -type f \( -name '*.msi' -o -name '*.exe' \) -exec cp {} "$DESKTOP_DIST_DIR/" \;
  log "Desktop package: $DESKTOP_DIST_DIR"
}

mkdir -p "$DIST_DIR"

case "$TARGET" in
  server) build_server ;;
  docker) build_docker ;;
  desktop) build_desktop ;;
  all) build_server; build_docker; build_desktop ;;
  *) echo "Usage: scripts/build.sh [server|docker|desktop|all]" >&2; exit 1 ;;
esac

clean_intermediates

log "Build finished"
