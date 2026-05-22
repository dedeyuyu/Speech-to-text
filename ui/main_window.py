"""
主窗口模块 - Whisper 实时语音转文字应用 UI

功能：
  - 实时录音与 Whisper 转录
  - 边说边显示文字（VAD 驱动）
  - 音量波形可视化
  - 历史记录查看
  - 本地 JSON/TXT 导出
"""

import sys
import time
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QComboBox, QProgressBar, QFileDialog,
    QMenuBar, QMenu, QStatusBar, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QAction, QIcon,
    QTextCursor, QPalette, QLinearGradient,
)

from core.recorder import AudioRecorder, SAMPLE_RATE
from core.transcriber import RealtimeTranscriber
from core.storage import TranscriptStorage
from ui.styles import (
    MAIN_STYLE,
    STATUS_DOT_IDLE, STATUS_DOT_RECORDING,
    STATUS_DOT_PROCESSING, STATUS_DOT_ERROR,
    COLOR_ACCENT, COLOR_SUCCESS, COLOR_DANGER, COLOR_BG_SURFACE,
    COLOR_TEXT_MUTED, COLOR_BORDER,
)


# ─────────────────────────────────────────────────────────
# 波形可视化组件
# ─────────────────────────────────────────────────────────

class WaveformWidget(QWidget):
    """
    实时音频波形可视化组件。
    
    绘制滚动的音量波形图，反映当前录音音量。
    """

    HISTORY_LEN = 80   # 保留多少帧历史

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("waveformWidget")
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)
        self._levels = [0.0] * self.HISTORY_LEN
        self._is_recording = False

    def update_level(self, level: float):
        """更新音量级别（0.0 ~ 1.0）。"""
        self._levels.append(min(1.0, max(0.0, level)))
        if len(self._levels) > self.HISTORY_LEN:
            self._levels.pop(0)
        self.update()

    def set_recording(self, recording: bool):
        self._is_recording = recording
        if not recording:
            self._levels = [0.0] * self.HISTORY_LEN
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        center_y = h // 2

        # 背景
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_SURFACE))

        if not self._levels:
            return

        bar_w = max(2, w // self.HISTORY_LEN - 1)
        spacing = w // self.HISTORY_LEN

        accent = QColor(COLOR_ACCENT if not self._is_recording else COLOR_SUCCESS)

        for i, level in enumerate(self._levels):
            x = i * spacing
            bar_h = max(3, int(level * (h - 12)))
            alpha = int(80 + 175 * (i / self.HISTORY_LEN))
            color = QColor(accent)
            color.setAlpha(alpha)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            # 对称绘制（上下）
            painter.drawRoundedRect(
                x, center_y - bar_h // 2,
                bar_w, bar_h,
                1, 1
            )


# ─────────────────────────────────────────────────────────
# 模型加载线程
# ─────────────────────────────────────────────────────────

class ModelLoaderThread(QThread):
    """在后台线程加载 Whisper 模型，完成后发出信号。"""
    loaded = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, transcriber: RealtimeTranscriber):
        super().__init__()
        self._transcriber = transcriber

    def run(self):
        try:
            self._transcriber._load_model()
            self.loaded.emit()
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    应用主窗口。
    
    协调录音器、转录器和存储器，呈现完整的 UI 界面。
    """

    # Qt 信号（用于线程安全的 UI 更新）
    sig_transcript_received = pyqtSignal(str)
    sig_status_update = pyqtSignal(str, str)   # (message, state)
    sig_level_update = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self._is_recording = False
        self._model_loaded = False
        self._record_start_time = None

        # 核心组件
        self._recorder = AudioRecorder(
            on_audio_chunk=self._on_audio_chunk,
            on_error=self._on_recorder_error,
        )
        self._transcriber = RealtimeTranscriber(
            model_name="small",
            language=None,              # 自动检测语言
            on_final=self._on_transcript_final,
            on_error=self._on_transcriber_error,
        )
        self._storage = TranscriptStorage()

        # 波形平滑用
        self._level_history = []
        self._level_lock = threading.Lock()

        self._setup_ui()
        self._connect_signals()
        self._setup_menu()
        self._load_model()

    # ─────────────────────────────────────────
    # UI 构建
    # ─────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("Whisper 语音转文字")
        self.setMinimumSize(900, 650)
        self.resize(1100, 720)
        self.setStyleSheet(MAIN_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 标题栏 ────────────────────────────
        title_bar = self._build_title_bar()
        root_layout.addWidget(title_bar)

        # ── 主体内容（分栏） ──────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {COLOR_BORDER}; }}")

        # 左侧：转录区
        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)

        # 右侧：历史记录
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([680, 320])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        root_layout.addWidget(splitter, 1)

        # ── 状态栏 ────────────────────────────
        self._build_status_bar()

    def _build_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)

        # 图标 + 标题
        icon_label = QLabel("🎙")
        icon_label.setStyleSheet("font-size: 28px;")

        title = QLabel("语音转文字")
        title.setObjectName("appTitle")

        subtitle = QLabel("· Powered by OpenAI Whisper（本地运行）")
        subtitle.setObjectName("appSubtitle")

        layout.addWidget(icon_label)
        layout.addSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()

        # 状态指示器
        self._status_dot = QLabel()
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(STATUS_DOT_IDLE)

        self._status_label = QLabel("正在加载模型…")
        self._status_label.setObjectName("statusLabel")

        layout.addWidget(self._status_dot)
        layout.addSpacing(6)
        layout.addWidget(self._status_label)

        return bar

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 12, 20)
        layout.setSpacing(12)

        # ── 录音控制区 ────────────────────────
        control_row = QHBoxLayout()
        control_row.setSpacing(16)

        # 录音按钮（大圆形）
        self._record_btn = QPushButton("⏺")
        self._record_btn.setObjectName("recordButton")
        self._record_btn.setProperty("recording", "false")
        self._record_btn.setToolTip("点击开始录音")
        self._record_btn.setEnabled(False)
        self._record_btn.clicked.connect(self._toggle_recording)
        control_row.addWidget(self._record_btn)

        # 右侧信息列
        info_col = QVBoxLayout()
        info_col.setSpacing(8)

        self._record_status_label = QLabel("等待模型加载…")
        self._record_status_label.setObjectName("infoLabel")
        self._record_status_label.setStyleSheet("font-size: 14px; color: #8892aa;")

        self._timer_label = QLabel("00:00")
        self._timer_label.setStyleSheet(
            f"font-size: 32px; font-weight: 700; color: #e8ecf8; "
            f"font-family: 'Courier New', monospace;"
        )

        self._mic_label = QLabel(f"🎤 {AudioRecorder.get_default_input_device()}")
        self._mic_label.setObjectName("infoLabel")

        info_col.addWidget(self._record_status_label)
        info_col.addWidget(self._timer_label)
        info_col.addWidget(self._mic_label)
        info_col.addStretch()
        control_row.addLayout(info_col)
        control_row.addStretch()

        # 操作按钮组
        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._clear_btn = QPushButton("🗑  清空记录")
        self._clear_btn.setObjectName("actionButton")
        self._clear_btn.setToolTip("清空当前文字区域")
        self._clear_btn.clicked.connect(self._clear_transcript)

        self._export_btn = QPushButton("💾  导出文本")
        self._export_btn.setObjectName("actionButton")
        self._export_btn.setToolTip("将今日记录导出为 TXT 文件")
        self._export_btn.clicked.connect(self._export_transcript)

        btn_col.addWidget(self._clear_btn)
        btn_col.addWidget(self._export_btn)
        control_row.addLayout(btn_col)

        layout.addLayout(control_row)

        # ── 波形可视化 ────────────────────────
        self._waveform = WaveformWidget()
        layout.addWidget(self._waveform)

        # ── 模型加载进度条 ────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)   # 不定进度（旋转效果）
        self._progress_bar.setFormat("正在加载 Whisper small 模型…")
        self._progress_bar.setVisible(True)
        layout.addWidget(self._progress_bar)

        # ── 分隔线 ────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # ── 转录文字区域标题 ──────────────────
        text_header = QHBoxLayout()
        text_title = QLabel("转录内容")
        text_title.setObjectName("panelTitle")
        self._word_count_label = QLabel("0 条记录")
        self._word_count_label.setObjectName("countLabel")
        text_header.addWidget(text_title)
        text_header.addStretch()
        text_header.addWidget(self._word_count_label)
        layout.addLayout(text_header)

        # ── 转录文字区域 ──────────────────────
        self._transcript_area = QTextEdit()
        self._transcript_area.setObjectName("transcriptArea")
        self._transcript_area.setReadOnly(False)
        self._transcript_area.setPlaceholderText(
            "点击录音按钮开始说话，文字将实时显示在这里…\n\n"
            "所有录音和文字均仅存储在本地，不会上传到任何服务器。"
        )
        layout.addWidget(self._transcript_area, 1)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("historyPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 标题行
        header = QHBoxLayout()
        title = QLabel("历史记录")
        title.setObjectName("panelTitle")
        self._history_count = QLabel("今日 0 条")
        self._history_count.setObjectName("countLabel")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._history_count)
        layout.addLayout(header)

        # 日期选择
        date_row = QHBoxLayout()
        date_lbl = QLabel("日期：")
        date_lbl.setObjectName("infoLabel")
        self._date_combo = QComboBox()
        self._date_combo.addItem(f"今天 ({datetime.now().strftime('%Y-%m-%d')})")
        self._date_combo.currentIndexChanged.connect(self._on_date_changed)
        date_row.addWidget(date_lbl)
        date_row.addWidget(self._date_combo, 1)
        layout.addLayout(date_row)

        # 历史列表
        self._history_list = QListWidget()
        self._history_list.setObjectName("historyList")
        self._history_list.setAlternatingRowColors(False)
        self._history_list.itemClicked.connect(self._on_history_item_clicked)
        layout.addWidget(self._history_list, 1)

        # 底部提示
        privacy_label = QLabel("🔒 所有数据仅存储在本地")
        privacy_label.setObjectName("infoLabel")
        privacy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        privacy_label.setStyleSheet("color: #22c55e; font-size: 11px; padding: 6px;")
        layout.addWidget(privacy_label)

        return panel

    def _build_status_bar(self):
        self._status_bar = self.statusBar()
        self._status_bar.setStyleSheet(
            f"QStatusBar {{ background: #0d0f14; color: #4a5268; "
            f"border-top: 1px solid #252a38; font-size: 12px; padding: 0 12px; }}"
        )
        self._status_bar.showMessage("就绪  ·  数据存储路径：" +
                                     str(self._storage.data_dir))

    # ─────────────────────────────────────────
    # 菜单栏
    # ─────────────────────────────────────────

    def _setup_menu(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        export_action = QAction("导出今日记录 (TXT)", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self._export_transcript)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        open_dir_action = QAction("打开数据文件夹", self)
        open_dir_action.triggered.connect(self._open_data_dir)
        file_menu.addAction(open_dir_action)

        file_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置")

        lang_menu = settings_menu.addMenu("识别语言")
        for lang_name, lang_code in [
            ("自动检测", None),
            ("中文", "zh"),
            ("英文", "en"),
            ("日文", "ja"),
            ("韩文", "ko"),
        ]:
            action = QAction(lang_name, self)
            action.triggered.connect(
                lambda checked, lc=lang_code: self._set_language(lc)
            )
            lang_menu.addAction(action)

        # 关于菜单
        about_menu = menubar.addMenu("关于")
        about_action = QAction("关于 Whisper 转写", self)
        about_action.triggered.connect(self._show_about)
        about_menu.addAction(about_action)

    # ─────────────────────────────────────────
    # 信号连接
    # ─────────────────────────────────────────

    def _connect_signals(self):
        self.sig_transcript_received.connect(self._append_transcript)
        self.sig_status_update.connect(self._update_status)
        self.sig_level_update.connect(self._waveform.update_level)

        # 计时器（每秒更新录音时长）
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_timer)

        # 波形刷新计时器（60fps）
        self._level_timer = QTimer(self)
        self._level_timer.setInterval(50)
        self._level_timer.timeout.connect(self._flush_level)

    # ─────────────────────────────────────────
    # 模型加载
    # ─────────────────────────────────────────

    def _load_model(self):
        self._loader_thread = ModelLoaderThread(self._transcriber)
        self._loader_thread.loaded.connect(self._on_model_loaded)
        self._loader_thread.error.connect(self._on_model_error)
        self._loader_thread.start()

    def _on_model_loaded(self):
        self._model_loaded = True
        self._record_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._record_status_label.setText("就绪，点击开始录音")
        self._update_status("模型加载完成 ✓", "idle")
        self._transcriber.start_worker()
        self._load_history()

    def _on_model_error(self, err_msg: str):
        self._progress_bar.setVisible(False)
        self._record_status_label.setText("模型加载失败！")
        self._update_status(f"错误：{err_msg}", "error")
        QMessageBox.critical(self, "模型加载失败",
                             f"无法加载 Whisper 模型：\n{err_msg}\n\n"
                             "请确保已安装 openai-whisper 并有网络连接（首次下载模型需要联网）。")

    # ─────────────────────────────────────────
    # 录音控制
    # ─────────────────────────────────────────

    def _toggle_recording(self):
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self._is_recording = True
        self._record_start_time = time.time()

        # 更新 UI
        self._record_btn.setProperty("recording", "true")
        self._record_btn.style().unpolish(self._record_btn)
        self._record_btn.style().polish(self._record_btn)
        self._record_btn.setText("⏹")
        self._record_btn.setToolTip("点击停止录音")
        self._record_status_label.setText("正在录音…")
        self._waveform.set_recording(True)
        self._update_status("录音中…", "recording")

        # 启动录音和计时
        self._elapsed_timer.start()
        self._level_timer.start()
        self._transcriber.reset_buffer()
        self._recorder.start()

    def _stop_recording(self):
        self._is_recording = False

        # 停止录音
        self._recorder.stop()
        self._elapsed_timer.stop()
        self._level_timer.stop()

        # 刷新剩余音频
        self._transcriber.flush()

        # 更新 UI
        self._record_btn.setProperty("recording", "false")
        self._record_btn.style().unpolish(self._record_btn)
        self._record_btn.style().polish(self._record_btn)
        self._record_btn.setText("⏺")
        self._record_btn.setToolTip("点击开始录音")
        self._record_status_label.setText("就绪，点击开始录音")
        self._timer_label.setText("00:00")
        self._waveform.set_recording(False)
        self._update_status("识别完成", "idle")

    # ─────────────────────────────────────────
    # 音频回调（录音线程 → UI 线程）
    # ─────────────────────────────────────────

    def _on_audio_chunk(self, chunk: np.ndarray):
        """接收音频块，同时送入转录器和音量计算。"""
        # 送入转录器
        self._transcriber.feed_audio(chunk)

        # 计算 RMS 音量
        energy = float(np.sqrt(np.mean(chunk ** 2)))
        level = min(1.0, energy * 8)   # 放大系数

        with self._level_lock:
            self._level_history.append(level)

    def _flush_level(self):
        """将最新音量级别发送到波形组件（在 UI 线程执行）。"""
        with self._level_lock:
            if self._level_history:
                avg_level = sum(self._level_history) / len(self._level_history)
                self._level_history.clear()
                self.sig_level_update.emit(avg_level)

    def _on_recorder_error(self, err: Exception):
        self._update_status(f"录音错误：{err}", "error")

    # ─────────────────────────────────────────
    # 转录结果回调（转录线程 → UI 线程）
    # ─────────────────────────────────────────

    def _on_transcript_final(self, text: str):
        """Whisper 返回最终识别结果（在转录线程中调用）。"""
        if text.strip():
            # 保存到本地
            self._storage.save_entry(text)
            # 通过信号更新 UI（线程安全）
            self.sig_transcript_received.emit(text)

    def _on_transcriber_error(self, err: Exception):
        self.sig_status_update.emit(f"识别错误：{err}", "error")

    # ─────────────────────────────────────────
    # UI 更新槽函数（主线程）
    # ─────────────────────────────────────────

    def _append_transcript(self, text: str):
        """将识别文字追加到文字区域。"""
        cursor = self._transcript_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 添加时间戳前缀
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}]  {text}\n\n"

        self._transcript_area.insertPlainText(formatted)
        self._transcript_area.ensureCursorVisible()

        # 更新计数
        count = self._storage.get_total_count()
        self._word_count_label.setText(f"{count} 条记录")

        # 刷新历史面板
        self._load_history()

    def _update_status(self, message: str, state: str = "idle"):
        """更新顶部状态指示器。"""
        dot_styles = {
            "idle": STATUS_DOT_IDLE,
            "recording": STATUS_DOT_RECORDING,
            "processing": STATUS_DOT_PROCESSING,
            "error": STATUS_DOT_ERROR,
        }
        self._status_dot.setStyleSheet(dot_styles.get(state, STATUS_DOT_IDLE))
        self._status_label.setText(message)

    def _update_timer(self):
        """更新录音计时显示。"""
        if self._record_start_time:
            elapsed = int(time.time() - self._record_start_time)
            m, s = divmod(elapsed, 60)
            self._timer_label.setText(f"{m:02d}:{s:02d}")

    # ─────────────────────────────────────────
    # 历史记录面板
    # ─────────────────────────────────────────

    def _load_history(self):
        """加载并显示历史记录。"""
        records = self._storage.get_today_records()
        self._history_list.clear()

        for rec in reversed(records[-50:]):   # 最多显示最新 50 条
            ts = datetime.fromisoformat(rec["timestamp"])
            time_str = ts.strftime("%H:%M:%S")
            text = rec["text"]
            display = f"{time_str}\n{text[:60]}{'…' if len(text) > 60 else ''}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, rec["text"])
            self._history_list.addItem(item)

        count = len(records)
        self._history_count.setText(f"今日 {count} 条")

        # 刷新日期下拉
        current_dates = [
            self._date_combo.itemText(i)
            for i in range(self._date_combo.count())
        ]
        all_dates = self._storage.get_all_dates()
        for date_str in all_dates:
            if date_str not in current_dates:
                self._date_combo.addItem(date_str)

    def _on_date_changed(self, index: int):
        """切换历史日期。"""
        if index == 0:
            self._load_history()
        else:
            date_str = self._date_combo.currentText()
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                records = self._storage.get_records_for_date(date)
                self._history_list.clear()
                for rec in reversed(records[-50:]):
                    ts = datetime.fromisoformat(rec["timestamp"])
                    display = f"{ts.strftime('%H:%M:%S')}\n{rec['text'][:60]}"
                    item = QListWidgetItem(display)
                    item.setData(Qt.ItemDataRole.UserRole, rec["text"])
                    self._history_list.addItem(item)
            except ValueError:
                pass

    def _on_history_item_clicked(self, item: QListWidgetItem):
        """点击历史记录，将完整文字复制到剪贴板。"""
        from PyQt6.QtWidgets import QApplication
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            QApplication.clipboard().setText(text)
            self._status_bar.showMessage(f"已复制到剪贴板：{text[:40]}…", 3000)

    # ─────────────────────────────────────────
    # 操作按钮
    # ─────────────────────────────────────────

    def _clear_transcript(self):
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空当前文字区域吗？\n（历史记录文件不会被删除）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._transcript_area.clear()
            self._word_count_label.setText("0 条记录")

    def _export_transcript(self):
        """导出今日记录为 TXT 文件。"""
        default_path = str(Path.home() / "Desktop" /
                          f"转录记录_{datetime.now().strftime('%Y%m%d')}.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出转录记录", default_path,
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if path:
            try:
                txt_path = self._storage.export_txt()
                import shutil
                shutil.copy(txt_path, path)
                self._status_bar.showMessage(f"已导出到：{path}", 5000)
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def _open_data_dir(self):
        """用资源管理器打开数据目录。"""
        import subprocess
        subprocess.Popen(f'explorer "{self._storage.data_dir}"')

    def _set_language(self, lang_code):
        """设置识别语言。"""
        self._transcriber.language = lang_code
        lang_names = {
            None: "自动检测",
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韩文",
        }
        name = lang_names.get(lang_code, lang_code)
        self._status_bar.showMessage(f"识别语言已切换为：{name}", 3000)

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "<h3>Whisper 语音转文字</h3>"
            "<p>基于 OpenAI Whisper 模型的本地语音识别软件。</p>"
            "<p><b>隐私声明：</b>本软件完全在本地运行，<br>"
            "您的录音和转录文字<b>不会上传到任何服务器</b>。</p>"
            "<p>Whisper 模型：small<br>"
            "数据存储：本地 JSON 文件</p>"
        )

    # ─────────────────────────────────────────
    # 窗口关闭
    # ─────────────────────────────────────────

    def closeEvent(self, event):
        """关闭窗口时安全停止所有线程。"""
        if self._is_recording:
            self._stop_recording()
        self._transcriber.stop_worker()
        event.accept()
