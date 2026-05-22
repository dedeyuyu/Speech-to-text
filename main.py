"""
Whisper 语音转文字 - 程序入口

本地运行，所有音频和文字数据仅存储在本地，不进行任何网络上传。
"""

import sys
import os

# 抑制 macOS/Windows 控制台警告
os.environ.setdefault("PYTHONWARNINGS", "ignore")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Whisper 语音转文字")
    app.setApplicationDisplayName("语音转文字")
    app.setOrganizationName("Local")

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
