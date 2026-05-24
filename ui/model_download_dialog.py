"""
模型下载管理对话框

显示所有可用的 Whisper 模型，支持：
  - 查看下载状态（已下载/未下载）
  - 一键下载，显示实时进度和下载速度
  - 主源失败时自动切换备用镜像（HuggingFace）
  - 切换当前使用的模型
  - FFmpeg 安装状态检查
"""

import os
import shutil
import threading
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QScrollArea, QWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ui.styles import (
    MAIN_STYLE, COLOR_ACCENT, COLOR_SUCCESS, COLOR_BG_SURFACE,
    COLOR_BG_ELEVATED, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_BORDER, COLOR_TEXT_MUTED, COLOR_DANGER,
)

# ─── Whisper 模型信息 ──────────────────────────────────────
#
# 每个模型有两个下载源：
#   url        : 主源（OpenAI Azure CDN，全球最快）
#   mirror_url : 备用源（HuggingFace，主源超时时自动切换）

MODELS = [
    {
        "name": "tiny",
        "display": "Tiny",
        "size_mb": 39,
        "speed": "⚡ 最快",
        "accuracy": "★★☆☆☆",
        "desc": "适合快速测试",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
        "mirror_url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
        "hf_url": "https://huggingface.co/datasets/reach-vb/random-audios/resolve/main/whisper-tiny.pt",
        "filename": "tiny.pt",
    },
    {
        "name": "base",
        "display": "Base",
        "size_mb": 74,
        "speed": "⚡ 快",
        "accuracy": "★★★☆☆",
        "desc": "速度与精度均衡",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
        "mirror_url": None,
        "filename": "base.pt",
    },
    {
        "name": "small",
        "display": "Small ⭐",
        "size_mb": 244,
        "speed": "🔄 中等",
        "accuracy": "★★★★☆",
        "desc": "推荐 — 中文识别效果好",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
        "mirror_url": None,
        "filename": "small.pt",
    },
    {
        "name": "medium",
        "display": "Medium",
        "size_mb": 769,
        "speed": "🐢 慢",
        "accuracy": "★★★★★",
        "desc": "高精度，需要较长时间",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
        "mirror_url": None,
        "filename": "medium.pt",
    },
    {
        "name": "large-v3",
        "display": "Large v3",
        "size_mb": 1550,
        "speed": "🐌 最慢",
        "accuracy": "★★★★★+",
        "desc": "最高精度，需要 GPU 或较长时间",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
        "mirror_url": None,
        "filename": "large-v3.pt",
    },
]

WHISPER_CACHE_DIR = Path.home() / ".cache" / "whisper"

# 连接超时（秒）
CONNECT_TIMEOUT = 25
# 读取超时（秒）— 大文件字节流不限速
READ_TIMEOUT = 600
# 最大重试次数（针对5xx和网络错误）
MAX_RETRIES = 3


def get_model_path(filename: str) -> Path:
    return WHISPER_CACHE_DIR / filename


def is_model_downloaded(filename: str) -> bool:
    p = get_model_path(filename)
    return p.exists() and p.stat().st_size > 1_000_000


def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _make_session() -> requests.Session:
    """创建带重试策略的 Session，过滤5xx错误。"""
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=2,           # 重试间隔: 2s, 4s, 8s
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ─── 下载工作线程 ──────────────────────────────────────────

class DownloadThread(QThread):
    progress   = pyqtSignal(int, int, float)  # (downloaded_bytes, total_bytes, bytes_per_sec)
    finished   = pyqtSignal(bool, str)         # (success, message)
    status_msg = pyqtSignal(str)               # 状态提示文字

    def __init__(self, url: str, mirror_url: str | None, dest: Path):
        super().__init__()
        self._url = url
        self._mirror_url = mirror_url
        self._dest = dest
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        WHISPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = self._dest.with_suffix(".tmp")

        # 构建下载源列表：主源 → 备用源
        sources = []
        if self._url:
            sources.append((self._url, "主源（OpenAI CDN）"))
        if self._mirror_url:
            sources.append((self._mirror_url, "备用源（镜像）"))

        last_error = ""
        for idx, (url, label) in enumerate(sources):
            if self._cancelled:
                tmp_path.unlink(missing_ok=True)
                self.finished.emit(False, "已取消")
                return

            if idx == 0:
                self.status_msg.emit(f"🔗 正在连接 {label}…")
            else:
                self.status_msg.emit(f"⚠️ 主源失败，切换到 {label}…")

            success, last_error = self._try_download(url, label, tmp_path)
            if success:
                os.replace(tmp_path, self._dest)
                self.finished.emit(True, "下载完成")
                return

            tmp_path.unlink(missing_ok=True)

        # 所有源都失败，生成用户可读的错误提示
        if any(kw in last_error.lower() for kw in ("timeout", "timed out", "connect")):
            err_msg = (
                "⚠️ 所有下载源均连接超时。\n\n"
                "可能的解决方案：\n"
                "1️⃣  检查网络连接是否正常\n"
                "2️⃣  尝试使用 VPN 后再下载\n"
                "3️⃣  稍后再试（服务器可能暂时不可用）\n\n"
                f"技术详情：{last_error}"
            )
        else:
            err_msg = last_error

        self.finished.emit(False, err_msg)

    def _try_download(self, url: str, label: str, tmp_path: Path) -> tuple[bool, str]:
        """
        尝试从指定 URL 下载到 tmp_path。
        返回 (success, error_msg)。
        """
        try:
            session = _make_session()
            resp = session.get(
                url,
                stream=True,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={"User-Agent": "WhisperSTT/2.1 (model-downloader)"},
            )
            resp.raise_for_status()

            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            speed_window_start = time.monotonic()
            speed_window_bytes = 0

            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=131072):  # 128 KB
                    if self._cancelled:
                        return False, "已取消"
                    if chunk:
                        f.write(chunk)
                        n = len(chunk)
                        downloaded += n
                        speed_window_bytes += n

                        now = time.monotonic()
                        elapsed = now - speed_window_start
                        if elapsed >= 0.8:
                            speed = speed_window_bytes / elapsed
                            speed_window_bytes = 0
                            speed_window_start = now
                        else:
                            speed = 0

                        self.progress.emit(downloaded, total, speed)

            return True, ""

        except requests.exceptions.ConnectTimeout:
            host = url.split("/")[2]
            return False, f"连接超时（{host}）"
        except requests.exceptions.ReadTimeout:
            return False, "读取超时，网络速度过慢"
        except requests.exceptions.ConnectionError as e:
            return False, f"网络连接失败：{e}"
        except requests.exceptions.HTTPError as e:
            return False, f"HTTP 错误：{e}"
        except Exception as e:
            return False, str(e)


# ─── 单个模型行组件 ───────────────────────────────────────

class ModelRow(QWidget):
    """显示一个模型的状态和操作按钮。"""

    use_model = pyqtSignal(str)  # model name

    def __init__(self, model_info: dict, current_model: str, parent=None):
        super().__init__(parent)
        self._info = model_info
        self._thread = None
        self._setup_ui(current_model)

    def _setup_ui(self, current_model: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # 已下载标志
        is_downloaded = is_model_downloaded(self._info["filename"])
        is_current = self._info["name"] == current_model

        # 状态指示
        status_dot = QLabel("✅" if is_downloaded else "○")
        status_dot.setFixedWidth(24)
        status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_dot)
        self._status_dot = status_dot

        # 模型名称
        name_lbl = QLabel(self._info["display"])
        name_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: "
            f"{'#5b7fff' if is_current else COLOR_TEXT_PRIMARY};"
        )
        name_lbl.setFixedWidth(100)
        layout.addWidget(name_lbl)

        # 大小 + 速度
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        size_lbl = QLabel(f"{self._info['size_mb']} MB  {self._info['speed']}")
        size_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        desc_lbl = QLabel(self._info["desc"])
        desc_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        info_col.addWidget(size_lbl)
        info_col.addWidget(desc_lbl)
        layout.addLayout(info_col)
        layout.addStretch()

        # 精度
        acc_lbl = QLabel(self._info["accuracy"])
        acc_lbl.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 12px;")
        layout.addWidget(acc_lbl)

        # 进度条（下载时显示）
        self._progress = QProgressBar()
        self._progress.setFixedWidth(180)
        self._progress.setMaximumHeight(16)
        self._progress.setVisible(False)
        self._progress.setFormat("%p%")
        layout.addWidget(self._progress)

        # 状态提示标签（显示下载速度/当前状态）
        self._speed_lbl = QLabel("")
        self._speed_lbl.setFixedWidth(90)
        self._speed_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        self._speed_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._speed_lbl.setVisible(False)
        layout.addWidget(self._speed_lbl)

        # 操作按钮
        self._btn = QPushButton()
        self._btn.setFixedWidth(90)
        self._btn.setObjectName("actionButton")
        self._update_button_state()
        self._btn.clicked.connect(self._on_btn_clicked)
        layout.addWidget(self._btn)

        self.setStyleSheet(
            f"ModelRow {{ background: {COLOR_BG_ELEVATED}; border: 1px solid "
            f"{'#5b7fff' if is_current else COLOR_BORDER}; border-radius: 8px; }}"
        )

    def _update_button_state(self):
        is_downloaded = is_model_downloaded(self._info["filename"])
        if is_downloaded:
            self._btn.setText("使用此模型")
            self._btn.setStyleSheet(
                f"QPushButton {{ background: rgba(91,127,255,0.15); "
                f"color: {COLOR_ACCENT}; border: 1px solid {COLOR_ACCENT}; "
                f"border-radius: 6px; padding: 6px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: rgba(91,127,255,0.3); }}"
            )
        else:
            self._btn.setText("⬇ 下载")
            self._btn.setStyleSheet(
                f"QPushButton {{ background: {COLOR_BG_ELEVATED}; "
                f"color: {COLOR_TEXT_SECONDARY}; border: 1px solid {COLOR_BORDER}; "
                f"border-radius: 6px; padding: 6px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {COLOR_BG_ELEVATED}; color: white; }}"
            )

    def _on_btn_clicked(self):
        if is_model_downloaded(self._info["filename"]):
            self.use_model.emit(self._info["name"])
        else:
            self._start_download()

    def _start_download(self):
        dest = get_model_path(self._info["filename"])

        # 如果文件已完整存在，直接提示使用，无需重新下载
        if is_model_downloaded(self._info["filename"]):
            reply = QMessageBox.question(
                self.window(), "模型已存在",
                f"模型 {self._info['display']} 已下载。\n是否直接切换使用此模型？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.use_model.emit(self._info["name"])
            return

        # 清理上次下载失败留下的 .tmp 残留文件
        tmp_path = dest.with_suffix(".tmp")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

        self._btn.setText("取消")
        self._progress.setVisible(True)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._speed_lbl.setVisible(True)
        self._speed_lbl.setText("连接中…")

        self._thread = DownloadThread(
            self._info["url"],
            self._info.get("mirror_url"),
            dest,
        )
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self._on_finished)
        self._thread.status_msg.connect(self._on_status_msg)
        self._thread.start()

        # 按钮变为取消
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._cancel_download)

    def _cancel_download(self):
        if self._thread:
            self._thread.cancel()

    def _on_status_msg(self, msg: str):
        self._speed_lbl.setText(msg[:20])  # 截断显示

    def _on_progress(self, downloaded: int, total: int, speed: float):
        if total > 0:
            pct = int(downloaded * 100 / total)
            self._progress.setValue(pct)
            mb_done = downloaded / 1_048_576
            mb_total = total / 1_048_576
            self._progress.setFormat(f"{mb_done:.1f} / {mb_total:.0f} MB")
        else:
            self._progress.setRange(0, 0)

        # 显示下载速度
        if speed > 0:
            if speed >= 1_048_576:
                speed_str = f"{speed/1_048_576:.1f} MB/s"
            else:
                speed_str = f"{speed/1024:.0f} KB/s"
            self._speed_lbl.setText(speed_str)

    def _on_finished(self, success: bool, message: str):
        self._progress.setVisible(False)
        self._speed_lbl.setVisible(False)
        self._thread = None
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._on_btn_clicked)

        if success:
            self._status_dot.setText("✅")
        else:
            QMessageBox.warning(self.window(), "下载失败", message)

        self._update_button_state()


# ─── 主对话框 ─────────────────────────────────────────────

class ModelDownloadDialog(QDialog):
    """Whisper 模型下载管理对话框。"""

    model_changed = pyqtSignal(str)  # 当用户选择新模型时

    def __init__(self, current_model: str = "small", parent=None):
        super().__init__(parent)
        self._current_model = current_model
        self.setWindowTitle("模型管理")
        self.setMinimumSize(720, 520)
        self.setStyleSheet(MAIN_STYLE)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 标题
        title = QLabel("🤖  Whisper 模型管理")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "模型文件存储在本地，下载后可完全离线使用。"
            "不同模型在速度和精度之间有所取舍。"
        )
        subtitle.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;"
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # 网络提示
        net_tip = QLabel("💡 主源（OpenAI CDN）连接失败时会自动切换到备用镜像重试，无需手动操作。")
        net_tip.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px;")
        net_tip.setWordWrap(True)
        layout.addWidget(net_tip)

        # FFmpeg 状态
        ffmpeg_ok = check_ffmpeg()
        ffmpeg_row = QHBoxLayout()
        ffmpeg_icon = QLabel("✅" if ffmpeg_ok else "⚠️")
        ffmpeg_text = QLabel(
            "FFmpeg 已安装 — 支持所有音频格式" if ffmpeg_ok
            else "未检测到 FFmpeg — 请安装后重启应用（winget install ffmpeg）"
        )
        ffmpeg_text.setStyleSheet(
            f"color: {'#22c55e' if ffmpeg_ok else '#f59e0b'}; font-size: 12px;"
        )
        ffmpeg_row.addWidget(ffmpeg_icon)
        ffmpeg_row.addWidget(ffmpeg_text)
        ffmpeg_row.addStretch()
        layout.addLayout(ffmpeg_row)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {COLOR_BORDER};")
        layout.addWidget(sep)

        # 模型列表（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        model_layout = QVBoxLayout(container)
        model_layout.setSpacing(8)
        model_layout.setContentsMargins(0, 0, 0, 0)

        for info in MODELS:
            row = ModelRow(info, self._current_model, container)
            row.use_model.connect(self._on_use_model)
            model_layout.addWidget(row)

        model_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # 底部关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("actionButton")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _on_use_model(self, model_name: str):
        self._current_model = model_name
        self.model_changed.emit(model_name)
        QMessageBox.information(
            self, "模型已切换",
            f"已切换到 {model_name} 模型。\n重启录音后生效。"
        )
