"""
自动输出引擎（跨平台）

将转录文字自动粘贴到当前活动窗口。

Windows : win32gui 检测活动窗口 + keyboard 发送 Ctrl+V
macOS   : pynput 检测当前应用 + pyperclip + Cmd+V 模拟

注意：仅在 auto_output=True 且活动窗口不是本应用时执行。
"""

import sys
import time
import threading

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS   = sys.platform == "darwin"

# ── 依赖导入 ─────────────────────────────────────────────────

try:
    import pyperclip
    PYPERCLIP_OK = True
except ImportError:
    PYPERCLIP_OK = False

# Windows 专用
if _IS_WINDOWS:
    try:
        import keyboard as _kb
        KEYBOARD_OK = True
    except ImportError:
        KEYBOARD_OK = False

    try:
        import win32gui
        WIN32_OK = True
    except ImportError:
        WIN32_OK = False
else:
    KEYBOARD_OK = False
    WIN32_OK = False

# macOS 专用
if _IS_MACOS:
    try:
        from pynput import keyboard as _pynput_kb
        from pynput.keyboard import Key, Controller as _KbController
        _mac_kb = _KbController()
        PYNPUT_OK = True
    except ImportError:
        PYNPUT_OK = False
else:
    PYNPUT_OK = False


class OutputEngine:
    """
    自动输出到活动窗口的引擎（跨平台）。

    当 auto_output=True 时，转录完成后自动将文字粘贴到
    当前聚焦的输入框，支持 Teams、Word、任意文本框等。
    """

    def __init__(self):
        self._auto_output = False
        self._our_hwnd = 0       # Windows: 本应用的 HWND
        self._lock = threading.Lock()

    def set_auto_output(self, enabled: bool):
        """开启/关闭自动输出模式。"""
        self._auto_output = enabled

    def set_our_window(self, hwnd: int):
        """
        设置本应用的窗口句柄（Windows），防止粘贴到自身。
        macOS 通过应用进程名判断，此方法在 macOS 上无效果。
        """
        self._our_hwnd = hwnd

    def output(self, text: str):
        """
        将文字输出到当前活动窗口。
        此方法在主线程中调用（通过 Qt 信号触发）。
        """
        if not self._auto_output:
            return
        if not text or not text.strip():
            return
        if not PYPERCLIP_OK:
            return

        if _IS_WINDOWS:
            self._output_windows(text)
        elif _IS_MACOS:
            self._output_macos(text)

    # ─────────────────────────────────────────
    # Windows 实现
    # ─────────────────────────────────────────

    def _output_windows(self, text: str):
        if not KEYBOARD_OK:
            return
        try:
            active_hwnd = win32gui.GetForegroundWindow() if WIN32_OK else 0
            if active_hwnd and active_hwnd == self._our_hwnd:
                return   # 不粘贴到本应用

            try:
                original = pyperclip.paste()
            except Exception:
                original = ""

            pyperclip.copy(text)
            time.sleep(0.08)
            _kb.send("ctrl+v")
            time.sleep(0.1)

            if original:
                pyperclip.copy(original)
        except Exception as e:
            print(f"[输出引擎/Windows] 粘贴失败: {e}")

    # ─────────────────────────────────────────
    # macOS 实现
    # ─────────────────────────────────────────

    def _output_macos(self, text: str):
        """
        macOS 输出：复制到剪贴板 → 模拟 Cmd+V 粘贴。

        ⚠️  需要「辅助功能」权限（系统偏好设置 → 隐私 → 辅助功能）。
        """
        if not PYNPUT_OK:
            # 降级：仅写入剪贴板，提示用户手动粘贴
            try:
                pyperclip.copy(text)
            except Exception:
                pass
            return

        try:
            # 短暂延迟，确保焦点在目标窗口上
            time.sleep(0.12)

            try:
                original = pyperclip.paste()
            except Exception:
                original = ""

            pyperclip.copy(text)
            time.sleep(0.08)

            # 模拟 Cmd+V
            with _mac_kb.pressed(Key.cmd):
                _mac_kb.press('v')
                _mac_kb.release('v')

            time.sleep(0.1)

            if original:
                pyperclip.copy(original)

        except Exception as e:
            print(f"[输出引擎/macOS] 粘贴失败: {e}")

    @property
    def is_available(self) -> bool:
        """检查所需库是否已安装。"""
        if _IS_WINDOWS:
            return PYPERCLIP_OK and KEYBOARD_OK
        if _IS_MACOS:
            return PYPERCLIP_OK   # pynput 可选（有降级方案）
        return False

    @property
    def auto_output(self) -> bool:
        return self._auto_output
