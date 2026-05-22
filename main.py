"""
Whisper 语音转文字 - 程序入口 v2.0

支持 --hidden 参数静默启动（开机自启时使用）。
"""

import sys
import os

os.environ.setdefault("PYTHONWARNINGS", "ignore")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("WhisperSTT")
    app.setApplicationDisplayName("语音转文字")
    app.setOrganizationName("Local")

    # 关闭最后一个窗口不退出（托盘运行）
    app.setQuitOnLastWindowClosed(False)

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    # 设置应用图标
    from pathlib import Path
    icon_path = Path(__file__).parent / "image.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # --hidden 参数：开机自启时不显示窗口
    start_hidden = "--hidden" in sys.argv

    from ui.main_window import MainWindow
    window = MainWindow(start_hidden=start_hidden)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
