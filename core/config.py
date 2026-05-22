"""
配置管理模块 - 持久化用户设置到本地 JSON 文件
"""

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "WhisperSTT"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "hotkey": "ctrl+alt+r",
    "auto_output": False,
    "autostart": False,
    "language": None,       # None = 自动检测
    "model": "small",
    "minimize_to_tray": True,
    "show_tray_tip": True,
}


def load_config() -> dict:
    """加载配置，若不存在则返回默认值。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 合并缺失的默认键
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except (json.JSONDecodeError, IOError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """保存配置到文件。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
