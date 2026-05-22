"""
自动输出引擎 - 将转录文字自动粘贴到当前活动窗口

工作原理：
1. 将转录文字复制到剪贴板
2. 向当前活动窗口发送 Ctrl+V 粘贴
3. 恢复剪贴板原内容

注意：仅在 auto_output=True 且活动窗口不是本应用时执行。
"""

import time
import threading

try:
    import pyperclip
    PYPERCLIP_OK = True
except ImportError:
    PYPERCLIP_OK = False

try:
    import keyboard as kb
    KEYBOARD_OK = True
except ImportError:
    KEYBOARD_OK = False

try:
    import win32gui
    WIN32_OK = True
except ImportError:
    WIN32_OK = False


class OutputEngine:
    """
    自动输出到活动窗口的引擎。

    当 auto_output=True 时，转录完成后自动将文字粘贴到
    当前活动（焦点）窗口，支持 Teams、Word、任意文本框等。
    """

    def __init__(self):
        self._auto_output = False
        self._our_hwnd = 0          # 本应用的窗口句柄
        self._lock = threading.Lock()

    def set_auto_output(self, enabled: bool):
        """开启/关闭自动输出模式。"""
        self._auto_output = enabled

    def set_our_window(self, hwnd: int):
        """
        设置本应用的窗口句柄，防止粘贴到自身。

        Args:
            hwnd: 主窗口的 Windows HWND
        """
        self._our_hwnd = hwnd

    def output(self, text: str):
        """
        将文字输出到当前活动窗口（通过剪贴板粘贴）。

        此方法在主线程中调用（通过 Qt 信号触发）。
        若当前活动窗口是本应用，则跳过（UI 已通过信号更新）。
        """
        if not self._auto_output:
            return
        if not text or not text.strip():
            return
        if not PYPERCLIP_OK or not KEYBOARD_OK:
            return

        try:
            # 获取当前活动窗口
            active_hwnd = win32gui.GetForegroundWindow() if WIN32_OK else 0

            # 如果活动窗口是本应用，不执行粘贴（应用内已显示）
            if active_hwnd and active_hwnd == self._our_hwnd:
                return

            # 保存当前剪贴板内容
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                original_clipboard = ""

            # 写入转录文字到剪贴板
            pyperclip.copy(text)
            time.sleep(0.08)

            # 发送 Ctrl+V 到当前活动窗口
            kb.send("ctrl+v")
            time.sleep(0.1)

            # 恢复剪贴板原内容
            if original_clipboard:
                pyperclip.copy(original_clipboard)

        except Exception as e:
            print(f"[输出引擎] 粘贴失败: {e}")

    @property
    def is_available(self) -> bool:
        """检查所需库是否已安装。"""
        return PYPERCLIP_OK and KEYBOARD_OK

    @property
    def auto_output(self) -> bool:
        return self._auto_output
