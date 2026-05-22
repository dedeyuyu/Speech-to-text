"""
悬浮音频指示器

录音时显示在屏幕底部中间，让用户随时知道录音状态。
特点：
  - 渐变颜色频率条（青色 → 紫色）
  - 脉冲动画（即使静音也有呼吸效果）
  - 半透明圆角胶囊形背景
  - 不抢焦点，不出现在任务栏
  - 点击可切换录音状态
"""

import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import (
    QPainter, QLinearGradient, QColor, QPen, QBrush,
    QFont, QPainterPath, QRadialGradient, QFontMetrics,
)


class FloatingIndicator(QWidget):
    """
    屏幕底部居中的悬浮音频频率指示器。

    仅在录音激活时可见。使用 WA_ShowWithoutActivating
    确保不抢占焦点（自动输出才能继续工作）。
    """

    # 外观常量
    W = 300
    H = 62
    MARGIN_BOTTOM = 20     # 距任务栏距离
    BAR_COUNT = 28         # 频率条数量

    def __init__(self, toggle_callback=None, parent=None):
        super().__init__(parent, 
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(self.W, self.H)

        self._toggle_callback = toggle_callback
        self._levels = [0.0] * self.BAR_COUNT
        self._phase = 0.0          # 动画相位
        self._is_recording = False
        self._device_label = ""    # 如 "GPU" 或 "CPU"

        # 动画定时器（50ms = 20 fps，流畅但不耗电）
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

        self._reposition()

    # ─────────────────────────────────────────
    # 公共接口
    # ─────────────────────────────────────────

    def start_recording(self):
        """开始录音时调用：显示并启动动画。"""
        self._is_recording = True
        self._timer.start()
        self._reposition()
        self.show()
        self.raise_()

    def stop_recording(self):
        """停止录音时调用：停止动画并隐藏。"""
        self._is_recording = False
        self._timer.stop()
        self.hide()

    def update_level(self, level: float):
        """接收来自录音模块的音量级别（0.0 ~ 1.0）。"""
        self._levels.append(min(1.0, max(0.0, level)))
        if len(self._levels) > self.BAR_COUNT:
            self._levels.pop(0)
        self.update()

    def set_device_label(self, label: str):
        """设置设备标签（如 'GPU ⚡' 或 'CPU'）。"""
        self._device_label = label
        self.update()

    # ─────────────────────────────────────────
    # 内部逻辑
    # ─────────────────────────────────────────

    def _reposition(self):
        """定位到主屏幕底部中央。"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()  # 排除任务栏
        x = geom.center().x() - self.W // 2
        y = geom.bottom() - self.H - self.MARGIN_BOTTOM
        self.move(x, y)

    def _tick(self):
        """动画帧：推进相位并重绘。"""
        self._phase += 0.12
        if self._phase > 2 * math.pi * 100:
            self._phase -= 2 * math.pi * 100
        self.update()

    # ─────────────────────────────────────────
    # 绘制
    # ─────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.W, self.H
        r = h // 2  # 胶囊圆角半径

        # ── 背景（半透明深色胶囊）───────────────────────
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, r, r)

        # 背景渐变：左深右稍亮
        bg_grad = QLinearGradient(0, 0, w, 0)
        bg_grad.setColorAt(0.0, QColor(10, 12, 22, 210))
        bg_grad.setColorAt(1.0, QColor(18, 20, 38, 210))
        painter.setBrush(QBrush(bg_grad))

        # 边框微光
        border_grad = QLinearGradient(0, 0, w, 0)
        border_grad.setColorAt(0.0, QColor(0, 220, 255, 80))
        border_grad.setColorAt(0.5, QColor(170, 50, 255, 80))
        border_grad.setColorAt(1.0, QColor(0, 220, 255, 80))
        painter.setPen(QPen(QBrush(border_grad), 1.2))
        painter.drawPath(path)

        # ── 频率条 ───────────────────────────────────────
        PAD_LEFT = 14
        PAD_RIGHT = 90    # 右侧留给状态文字
        bar_area_w = w - PAD_LEFT - PAD_RIGHT
        spacing = bar_area_w / self.BAR_COUNT
        bar_w = max(2.0, spacing - 1.5)
        center_y = h / 2

        for i, raw_level in enumerate(self._levels):
            progress = i / max(1, self.BAR_COUNT - 1)   # 0.0 → 1.0

            # 呼吸 + 实际音量叠加
            breath = 0.12 * math.sin(self._phase + i * 0.35)
            level = raw_level * 0.85 + breath + 0.06
            level = max(0.06, min(1.0, level))

            bar_h = max(4, int(level * (h - 14)))

            x = PAD_LEFT + i * spacing

            # 渐变色：青色 (#00e5ff) → 蓝紫 (#7c4dff) → 亮紫 (#ea00ff)
            if progress < 0.5:
                t = progress * 2
                rc = int(0   + t * 80)
                gc = int(229 - t * 155)
                bc = 255
            else:
                t = (progress - 0.5) * 2
                rc = int(80  + t * 170)
                gc = int(74  - t * 74)
                bc = int(255 - t * 50)

            # 透明度随音量增强
            alpha = int(140 + 115 * level)
            color = QColor(rc, gc, bc, alpha)

            # 顶部发光效果（亮一个档）
            glow = QColor(rc, gc, bc, min(255, alpha + 60))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, center_y - bar_h / 2, bar_w, 3, 1, 1)

            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(x, center_y - bar_h / 2, bar_w, bar_h, 1.5, 1.5)

        # ── 右侧状态区 ───────────────────────────────────
        text_x = w - PAD_RIGHT + 4
        text_w = PAD_RIGHT - 10

        # 脉冲红点
        dot_alpha = int(180 + 75 * math.sin(self._phase * 1.8))
        painter.setBrush(QBrush(QColor(255, 70, 70, dot_alpha)))
        dot_size = 9
        painter.drawEllipse(
            int(text_x + 2), int(center_y - dot_size / 2),
            dot_size, dot_size
        )

        # "录音中" 文字
        painter.setPen(QColor(210, 215, 240, 230))
        font = QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(
            QRect(int(text_x + 14), int(center_y - 11), text_w - 14, 14),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "录音中"
        )

        # 设备标签（GPU/CPU）
        if self._device_label:
            painter.setPen(QColor(0, 220, 255, 160))
            small_font = QFont("Microsoft YaHei UI", 7)
            painter.setFont(small_font)
            painter.drawText(
                QRect(int(text_x + 14), int(center_y + 2), text_w - 14, 12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._device_label
            )

        painter.end()

    # ─────────────────────────────────────────
    # 鼠标交互（点击切换录音）
    # ─────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._toggle_callback:
                self._toggle_callback()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setToolTip("点击可停止录音")
        super().enterEvent(event)
