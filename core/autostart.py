"""
开机自启动管理模块（跨平台）

Windows : 写入 HKEY_CURRENT_USER 注册表（无需管理员权限）
macOS   : 创建 ~/Library/LaunchAgents/com.whisper.stt.plist（用户级 LaunchAgent）

其他平台 : 忽略（无操作）
"""

import sys
import os
from pathlib import Path

APP_NAME = "WhisperSTT"
_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS   = sys.platform == "darwin"


def _get_launch_command() -> str:
    """获取启动命令（打包后用 exe/app 路径，开发时用 python main.py）。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    else:
        main_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py")
        )
        return f'"{sys.executable}" "{main_path}"'


# ═══════════════════════════════════════════════════════════════
# Windows 实现（注册表）
# ═══════════════════════════════════════════════════════════════

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

try:
    import winreg
    _WINREG_OK = True
except ImportError:
    _WINREG_OK = False


def _win_enable() -> bool:
    if not _WINREG_OK:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[自启动/Windows] 启用失败: {e}")
        return False


def _win_disable() -> bool:
    if not _WINREG_OK:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        print(f"[自启动/Windows] 禁用失败: {e}")
        return False


def _win_is_enabled() -> bool:
    if not _WINREG_OK:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# macOS 实现（LaunchAgent plist）
# ═══════════════════════════════════════════════════════════════

_PLIST_LABEL = f"com.whisper.stt"
_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
_PLIST_PATH = _LAUNCH_AGENTS_DIR / f"{_PLIST_LABEL}.plist"

_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>{home}/Library/Logs/WhisperSTT.err</string>
    <key>StandardOutPath</key>
    <string>{home}/Library/Logs/WhisperSTT.out</string>
</dict>
</plist>
"""


def _mac_plist_args() -> str:
    """生成 plist 的 ProgramArguments 数组内容。"""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        return f"        <string>{exe}</string>"
    else:
        main_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py")
        )
        return (f"        <string>{sys.executable}</string>\n"
                f"        <string>{main_path}</string>")


def _mac_enable() -> bool:
    try:
        _LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        content = _PLIST_TEMPLATE.format(
            label=_PLIST_LABEL,
            args=_mac_plist_args(),
            home=str(Path.home()),
        )
        _PLIST_PATH.write_text(content, encoding="utf-8")
        # 告知 launchd 加载（如果失败也没关系，下次重启会生效）
        os.system(f"launchctl load -w '{_PLIST_PATH}' 2>/dev/null")
        return True
    except Exception as e:
        print(f"[自启动/macOS] 启用失败: {e}")
        return False


def _mac_disable() -> bool:
    try:
        if _PLIST_PATH.exists():
            os.system(f"launchctl unload -w '{_PLIST_PATH}' 2>/dev/null")
            _PLIST_PATH.unlink()
        return True
    except Exception as e:
        print(f"[自启动/macOS] 禁用失败: {e}")
        return False


def _mac_is_enabled() -> bool:
    return _PLIST_PATH.exists()


# ═══════════════════════════════════════════════════════════════
# 统一公共接口
# ═══════════════════════════════════════════════════════════════

def enable_autostart() -> bool:
    """启用开机自启动。"""
    if _IS_WINDOWS:
        return _win_enable()
    if _IS_MACOS:
        return _mac_enable()
    return False


def disable_autostart() -> bool:
    """禁用开机自启动。"""
    if _IS_WINDOWS:
        return _win_disable()
    if _IS_MACOS:
        return _mac_disable()
    return False


def is_autostart_enabled() -> bool:
    """检查当前是否已启用开机自启动。"""
    if _IS_WINDOWS:
        return _win_is_enabled()
    if _IS_MACOS:
        return _mac_is_enabled()
    return False
