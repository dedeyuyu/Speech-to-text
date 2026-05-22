"""
全局快捷键管理模块

使用 keyboard 库注册系统级快捷键，不影响其他应用的焦点。
支持动态注册/注销/更换快捷键。
"""

import threading
import keyboard


class HotkeyManager:
    """
    全局快捷键管理器。
    
    特点：
    - 不抢占焦点（低级键盘钩子）
    - 支持运行时动态更换快捷键
    - 线程安全
    """

    def __init__(self):
        self._hotkey = None          # 当前注册的快捷键字符串
        self._callback = None        # 触发时的回调函数
        self._lock = threading.Lock()
        self._registered = False

    def register(self, hotkey_str: str, callback: callable) -> bool:
        """
        注册全局快捷键。

        Args:
            hotkey_str: 快捷键字符串，如 'ctrl+alt+r'
            callback: 触发时调用的函数（无参数）

        Returns:
            True 表示注册成功，False 表示失败
        """
        with self._lock:
            # 先注销旧的
            self._unregister_locked()
            try:
                keyboard.add_hotkey(
                    hotkey_str,
                    callback,
                    suppress=False,   # 不屏蔽按键传播
                    trigger_on_release=False,
                )
                self._hotkey = hotkey_str
                self._callback = callback
                self._registered = True
                return True
            except Exception as e:
                print(f"[快捷键] 注册失败 '{hotkey_str}': {e}")
                self._registered = False
                return False

    def unregister(self):
        """注销当前快捷键。"""
        with self._lock:
            self._unregister_locked()

    def _unregister_locked(self):
        """内部注销（调用前需持有锁）。"""
        if self._registered and self._hotkey:
            try:
                keyboard.remove_hotkey(self._hotkey)
            except Exception:
                pass
            self._hotkey = None
            self._registered = False

    def update(self, new_hotkey: str, callback: callable = None) -> bool:
        """
        更新快捷键（注销旧的，注册新的）。

        Args:
            new_hotkey: 新的快捷键字符串
            callback: 新的回调（None 则保持原回调）
        """
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
        self.unregister()
