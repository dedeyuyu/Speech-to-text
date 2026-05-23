"""
全局快捷键管理模块（跨平台）

Windows : 使用 keyboard 库（低级键盘钩子，无需权限）
macOS   : 使用 pynput 库（需在系统偏好设置 → 隐私 → 辅助功能中授权）

支持动态注册/注销/更换快捷键。
"""

import sys
import threading


# ── 平台检测 ────────────────────────────────────────────────
_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS   = sys.platform == "darwin"


class HotkeyManager:
    """
    全局快捷键管理器（跨平台）。

    快捷键字符串格式与平台无关，统一使用：
      'ctrl+alt+r', 'cmd+shift+r'（macOS 上 ctrl 也映射到 Cmd）

    特点：
      - 不抢占焦点
      - 支持运行时动态更换
      - 线程安全
    """

    def __init__(self):
        self._hotkey = None
        self._callback = None
        self._lock = threading.Lock()
        self._registered = False
        self._impl = self._create_impl()

    def _create_impl(self):
        """根据当前平台创建具体实现。"""
        if _IS_WINDOWS:
            return _WindowsHotkeyImpl()
        elif _IS_MACOS:
            return _MacOSHotkeyImpl()
        else:
            return _NullHotkeyImpl()

    # ─────────────────────────────────────────
    # 公共接口
    # ─────────────────────────────────────────

    def register(self, hotkey_str: str, callback: callable) -> bool:
        """注册全局快捷键。"""
        with self._lock:
            self._impl.unregister()
            ok = self._impl.register(hotkey_str, callback)
            if ok:
                self._hotkey = hotkey_str
                self._callback = callback
                self._registered = True
            else:
                self._registered = False
            return ok

    def unregister(self):
        """注销当前快捷键。"""
        with self._lock:
            self._impl.unregister()
            self._hotkey = None
            self._registered = False

    def update(self, new_hotkey: str, callback: callable = None) -> bool:
        """更新快捷键（注销旧的，注册新的）。"""
        cb = callback or self._callback
        if cb is None:
            return False
        return self.register(new_hotkey, cb)

    @property
    def current_hotkey(self) -> str:
        return self._hotkey or ""

    @property
    def is_registered(self) -> bool:
        return self._registered

    def __del__(self):
        try:
            self.unregister()
        except Exception:
            pass


# ── Windows 实现（keyboard 库）────────────────────────────────

class _WindowsHotkeyImpl:
    def __init__(self):
        self._hotkey = None
        try:
            import keyboard as _kb
            self._kb = _kb
            self._ok = True
        except ImportError:
            self._ok = False

    def register(self, hotkey_str: str, callback: callable) -> bool:
        if not self._ok:
            return False
        try:
            self._kb.add_hotkey(hotkey_str, callback,
                                suppress=False, trigger_on_release=False)
            self._hotkey = hotkey_str
            return True
        except Exception as e:
            print(f"[快捷键/Windows] 注册失败 '{hotkey_str}': {e}")
            return False

    def unregister(self):
        if not self._ok or not self._hotkey:
            return
        try:
            self._kb.remove_hotkey(self._hotkey)
        except Exception:
            pass
        self._hotkey = None


# ── macOS 实现（pynput 库）────────────────────────────────────

class _MacOSHotkeyImpl:
    """
    使用 pynput.keyboard.GlobalHotKeys 实现 macOS 全局快捷键。

    快捷键字符串转换：
      'ctrl+alt+r'   → '<cmd>+<alt>+r'
      'ctrl+shift+r' → '<cmd>+<shift>+r'
      'cmd+shift+r'  → '<cmd>+<shift>+r'

    ⚠️  需要在「系统偏好设置 → 隐私与安全 → 辅助功能」中授权本应用。
    """

    def __init__(self):
        self._listener = None
        try:
            from pynput import keyboard as _pk
            self._pk = _pk
            self._ok = True
        except ImportError:
            self._ok = False

    def _to_pynput_hotkey(self, hotkey_str: str) -> str:
        """将通用格式转换为 pynput GlobalHotKeys 格式。"""
        mapping = {
            "ctrl":  "<cmd>",    # macOS 上 Ctrl 习惯映射到 Cmd
            "cmd":   "<cmd>",
            "alt":   "<alt>",
            "option":"<alt>",
            "shift": "<shift>",
        }
        parts = hotkey_str.lower().split("+")
        converted = []
        for p in parts:
            p = p.strip()
            if p in mapping:
                converted.append(mapping[p])
            else:
                # 单字符键
                converted.append(p)
        return "+".join(converted)

    def register(self, hotkey_str: str, callback: callable) -> bool:
        if not self._ok:
            return False
        self.unregister()
        try:
            pynput_key = self._to_pynput_hotkey(hotkey_str)
            hotkeys = {pynput_key: callback}
            self._listener = self._pk.GlobalHotKeys(hotkeys)
            self._listener.daemon = True
            self._listener.start()
            return True
        except Exception as e:
            print(f"[快捷键/macOS] 注册失败 '{hotkey_str}': {e}")
            return False

    def unregister(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


# ── 空实现（不支持的平台）──────────────────────────────────────

class _NullHotkeyImpl:
    def register(self, hotkey_str: str, callback: callable) -> bool:
        print(f"[快捷键] 当前平台不支持全局快捷键")
        return False

    def unregister(self):
        pass
