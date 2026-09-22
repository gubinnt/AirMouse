"""PyInstaller runtime hook —— 让打包后的 AirMouse 正确定位证书与配置文件。

背景：server.py 用 ssl_context=('cert.pem', 'key.pem')，config_manager.py 用
"macro_configs.json" / "gamepad_configs.json"，全部是**相对当前工作目录**的路径。
打包成单文件 exe 后，工作目录不一定是 exe 所在目录，且资源被解包到临时目录，
因此这里做两件事：
  1) 首次运行把打包进去的证书与默认配置释放到 exe 同级目录（用户可读写、能持久化）；
  2) 把工作目录切到 exe 所在目录；若该目录不可写或资源缺失，则退回解包目录。
"""

import os
import shutil
import sys

_ASSETS = (
    "cert.pem",
    "key.pem",
    "macro_configs.json",
    "gamepad_configs.json",
)


def _bootstrap():
    if not getattr(sys, "frozen", False):
        return

    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    bundle_dir = getattr(sys, "_MEIPASS", exe_dir)

    for name in _ASSETS:
        src = os.path.join(bundle_dir, name)
        dst = os.path.join(exe_dir, name)
        if os.path.isfile(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass

    try:
        os.chdir(exe_dir)
    except OSError:
        os.chdir(bundle_dir)

    # 兜底：证书不在当前目录就用解包目录（配置将不持久化，但服务能起来）
    if not os.path.isfile(os.path.join(os.getcwd(), "cert.pem")):
        os.chdir(bundle_dir)


def _fix_console_encoding():
    """Windows 控制台默认是 GBK，而 server.py 启动时会 print("🚀 ...")，
    直接抛 UnicodeEncodeError 让程序崩掉。这里优先把控制台切到 UTF-8；
    若切换失败，则保持原编码并加 errors="replace"，最坏情况只丢个别字符，不会崩。
    """
    if sys.platform != "win32":
        return

    switched = False
    try:
        import ctypes

        switched = bool(ctypes.windll.kernel32.SetConsoleOutputCP(65001))
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        switched = False

    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            if switched:
                stream.reconfigure(encoding="utf-8", errors="replace")
            else:
                stream.reconfigure(errors="replace")
        except Exception:
            pass


_bootstrap()
_fix_console_encoding()
