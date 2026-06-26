"""Tauri 桌面版编译脚本。

用法：
    python scripts/build_tauri.py                      # 编译当前系统的桌面版
    python scripts/build_tauri.py --platform windows    # 指定平台（windows/linux/macos）

特性：
- Windows 安装包内置 WebView2 离线安装器（tauri.conf.json 已配置 offlineInstaller），
  适合无外网、未预装 WebView2 Runtime 的机器。
- Windows NSIS 安装器默认安装到 D:\\Program Files\\CapacityReport（无 D 盘时回落系统盘）。
- 跨平台限制：Tauri 无法可靠跨系统交叉编译，--platform 必须与当前系统一致，否则会提示需在目标系统本机构建。

产物：dist/desktop/ 下的安装包（Windows: .msi/.exe；Linux: .deb/.AppImage；macOS: .dmg）。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

TAURI_CONF = _env.SRC_TAURI_DIR / "tauri.conf.json"
NSIS_HOOK = _env.SRC_TAURI_DIR / "windows" / "nsis-hooks.nsh"

INSTALLER_EXTS = {
    "windows": (".msi", ".exe"),
    "linux": (".deb", ".AppImage", ".rpm"),
    "macos": (".dmg", ".app.tar.gz"),
}


# --------------------------------------------------------------------------- NSIS 定制（Windows 默认装 D 盘）

_RESTORE_LINE = "    Call RestorePreviousInstallLocation"

_INSTALL_DIR_OVERRIDE = """    Call RestorePreviousInstallLocation

    !if "${INSTALLMODE}" == "perMachine"
      ${If} ${FileExists} "D:\\*.*"
        StrCpy $INSTDIR "D:\\Program Files\\${PRODUCTNAME}"
      ${Else}
        ${If} ${RunningX64}
          StrCpy $INSTDIR "$PROGRAMFILES64\\${PRODUCTNAME}"
        ${Else}
          StrCpy $INSTDIR "$PROGRAMFILES\\${PRODUCTNAME}"
        ${EndIf}
      ${EndIf}
    !endif
"""

_ON_INIT_TAIL = """  !if "${INSTALLMODE}" == "both"
    !insertmacro MULTIUSER_INIT
  !endif
FunctionEnd"""

_ON_INIT_OVERRIDE = """  !if "${INSTALLMODE}" == "both"
    !insertmacro MULTIUSER_INIT
  !endif

  !if "${INSTALLMODE}" == "perMachine"
    ${If} ${FileExists} "D:\\*.*"
      StrCpy $INSTDIR "D:\\Program Files\\${PRODUCTNAME}"
    ${Else}
      ${If} ${RunningX64}
        StrCpy $INSTDIR "$PROGRAMFILES64\\${PRODUCTNAME}"
      ${Else}
        StrCpy $INSTDIR "$PROGRAMFILES\\${PRODUCTNAME}"
      ${EndIf}
    ${EndIf}
  !endif
FunctionEnd"""

_RESTORE_FUNCTION = """Function RestorePreviousInstallLocation
  ReadRegStr $4 SHCTX "${MANUPRODUCTKEY}" ""
  StrCmp $4 "" +2 0
    StrCpy $INSTDIR $4
FunctionEnd"""

_RESTORE_OVERRIDE = """Function RestorePreviousInstallLocation
  !if "${INSTALLMODE}" == "perMachine"
    ${If} ${FileExists} "D:\\*.*"
      StrCpy $INSTDIR "D:\\Program Files\\${PRODUCTNAME}"
      Return
    ${EndIf}
  !endif

  ReadRegStr $4 SHCTX "${MANUPRODUCTKEY}" ""
  StrCmp $4 "" +2 0
    StrCpy $INSTDIR $4
FunctionEnd"""


def find_nsis_template() -> Path:
    registry = Path.home() / ".cargo" / "registry" / "src"
    if not registry.exists():
        _env.die(f"未找到 Cargo registry：{registry}", "先运行一次 cargo tauri build 拉取 tauri-bundler。")
    candidates = [
        path
        for path in registry.rglob("installer.nsi")
        if "tauri-bundler-" in str(path) and path.parts[-4:] == ("bundle", "windows", "nsis", "installer.nsi")
    ]
    if not candidates:
        _env.die("未找到 Tauri NSIS 模板（installer.nsi）", "先运行一次 cargo tauri build 拉取 tauri-bundler。")
    return sorted(candidates, reverse=True)[0]


def make_nsis_template(tmp_dir: Path) -> Path:
    source = find_nsis_template()
    content = source.read_text(encoding="utf-8")

    import re

    hook_path = str(NSIS_HOOK.resolve())
    content, n = re.subn(
        r'\{\{#if installer_hooks\}\}\s*!include "\{\{installer_hooks\}\}"\s*\{\{/if\}\}',
        f'!include "{hook_path}"',
        content,
    )
    if n == 0:
        _env.die("Tauri NSIS 模板已变化：installer_hooks 标记未找到")

    for marker, replacement, label in (
        (_RESTORE_LINE, _INSTALL_DIR_OVERRIDE, "RestorePreviousInstallLocation 调用点"),
        (_ON_INIT_TAIL, _ON_INIT_OVERRIDE, ".onInit 结尾"),
        (_RESTORE_FUNCTION, _RESTORE_OVERRIDE, "RestorePreviousInstallLocation 函数"),
    ):
        if marker not in content:
            _env.die(f"Tauri NSIS 模板已变化：{label}标记未找到")
        content = content.replace(marker, replacement)

    target = tmp_dir / "tauri-nsis-installer.nsi"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    return target


def build_with_windows_nsis(tmp_dir: Path) -> None:
    template = make_nsis_template(tmp_dir)
    original = TAURI_CONF.read_text(encoding="utf-8")
    try:
        config = json.loads(original)
        config["bundle"]["windows"]["nsis"]["template"] = str(template)
        TAURI_CONF.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        _env.remove_path(_env.SRC_TAURI_DIR / "target" / "release" / "bundle")
        _env.step("编译 Tauri 桌面版（cargo tauri build）")
        _env.run(["cargo", "tauri", "build"], cwd=_env.SRC_TAURI_DIR)
    finally:
        TAURI_CONF.write_text(original, encoding="utf-8")


def collect_installers(platform: str) -> None:
    bundle_dir = _env.SRC_TAURI_DIR / "target" / "release" / "bundle"
    out_dir = _env.DIST_DIR / "desktop"
    _env.remove_path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exts = INSTALLER_EXTS[platform]
    found = 0
    for path in bundle_dir.rglob("*"):
        if path.is_file() and path.name.endswith(exts):
            shutil.copy2(path, out_dir / path.name)
            found += 1
            _env.info(f"安装包：{path.name}")
    if found == 0:
        _env.warn(f"未在 {bundle_dir} 找到安装包产物")
    _env.step(f"桌面版完成：{out_dir}")


def main() -> int:
    _env.setup_console()
    parser = argparse.ArgumentParser(description="编译 Tauri 桌面版")
    parser.add_argument(
        "--platform",
        choices=["current", "windows", "linux", "macos"],
        default="current",
        help="目标平台（默认当前系统）",
    )
    args = parser.parse_args()

    host = _env.host_platform()
    platform = host if args.platform == "current" else args.platform
    if platform != host:
        _env.die(
            f"无法在 {host} 上交叉编译 {platform} 桌面版。",
            f"Tauri 需要在目标系统本机构建，请在 {platform} 机器上运行本脚本。",
        )

    _env.ensure_rust()
    python = _env.ensure_venv(extra_packages=["pyinstaller"])
    _env.build_frontend(api_base=_env.DESKTOP_API_BASE)

    tmp = _env.DIST_DIR / ".tmp"
    _env.build_tauri_sidecar(python, tmp / "pyinstaller" / "work", tmp / "pyinstaller" / "dist")
    _env.ensure_tauri_cli()

    if platform == "windows":
        build_with_windows_nsis(tmp)
    else:
        _env.remove_path(_env.SRC_TAURI_DIR / "target" / "release" / "bundle")
        _env.step("编译 Tauri 桌面版（cargo tauri build）")
        _env.run(["cargo", "tauri", "build"], cwd=_env.SRC_TAURI_DIR)

    collect_installers(platform)

    _env.step("清理中间产物")
    _env.remove_path(tmp)
    _env.remove_path(_env.FRONTEND_DIR / "dist")
    _env.remove_path(_env.SRC_TAURI_DIR / "binaries")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
