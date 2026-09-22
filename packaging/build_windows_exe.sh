#!/usr/bin/env bash
# 把 AirMouse 打包成 Windows 单文件 exe。
#
# 用法（在仓库任意位置执行均可）：
#     bash packaging/build_windows_exe.sh
#
# 前置条件：
#     pip install -r requirments.txt pyinstaller
# 产物：
#     dist/AirMouseServer.exe
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# PyInstaller 是原生 Windows 程序，不认 MSYS 的 /c/... 路径，这里转成盘符路径
if command -v cygpath >/dev/null 2>&1; then
  ROOT_WIN="$(cygpath -w "$ROOT")"
else
  ROOT_WIN="$ROOT"
fi

PY="${PYTHON:-python}"

cd "$ROOT"

# 注意：--add-data / --runtime-hook 的相对路径是相对 --specpath 解析的，
# 所以这里统一使用绝对路径，否则会去 build/ 目录下找资源而报错。
"$PY" -m PyInstaller \
  --noconfirm --clean --onefile \
  --name AirMouseServer \
  --distpath "$ROOT_WIN/dist" \
  --workpath "$ROOT_WIN/build/pyi-work" \
  --specpath "$ROOT_WIN/build" \
  --runtime-hook "$ROOT_WIN/packaging/hook_airmouse.py" \
  --add-data "$ROOT_WIN/templates;templates" \
  --add-data "$ROOT_WIN/static;static" \
  --add-data "$ROOT_WIN/cert.pem;." \
  --add-data "$ROOT_WIN/key.pem;." \
  --add-data "$ROOT_WIN/macro_configs.json;." \
  --add-data "$ROOT_WIN/gamepad_configs.json;." \
  --hidden-import "engineio.async_drivers.threading" \
  --hidden-import "engineio.async_drivers._websocket_wsgi" \
  --hidden-import "pynput.keyboard._win32" \
  --hidden-import "pynput.mouse._win32" \
  --console \
  "$ROOT_WIN/server.py"

echo ""
echo "构建完成：$ROOT/dist/AirMouseServer.exe"
