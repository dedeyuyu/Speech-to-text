"""
Windows 开机自启动管理模块

通过写入 HKEY_CURRENT_USER 注册表实现开机自启，
无需管理员权限。
"""

import sys
import os

try:
    import winreg
    WINREG_OK = True
except ImportError:
    WINREG_OK = False

APP_NAME = "WhisperSTT"
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_launch_command() -> str:
    """获取启动命令（打包后用 exe 路径，开发时用 python main.py）。"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后
        return f'"{sys.executable}"'
    else:
        # 开发模式
        main_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py")
        )
        return f'"{sys.executable}" "{main_path}"'


def enable_autostart() -> bool:
    """
    启用开机自启动。

    Returns:
        True 表示成功
    """
    if not WINREG_OK:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[自启动] 启用失败: {e}")
        return False


def disable_autostart() -> bool:
    """
    禁用开机自启动。

    Returns:
        True 表示成功（包括原本未启用的情况）
    """
    if not WINREG_OK:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True   # 原本就没有，视为成功
    except Exception as e:
        print(f"[自启动] 禁用失败: {e}")
        return False


def is_autostart_enabled() -> bool:
    """检查当前是否已启用开机自启动。"""
    if not WINREG_OK:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY, 0, winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False
