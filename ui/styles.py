"""
样式表 - 深色现代主题

基于 HSL 配色系统，使用玻璃态拟物风格。
"""

# 主色调
COLOR_BG_DARK = "#0d0f14"         # 最深背景
COLOR_BG_SURFACE = "#13161e"      # 卡片/面板背景
COLOR_BG_ELEVATED = "#1a1e2a"     # 悬浮元素背景
COLOR_BG_HOVER = "#212636"        # 悬停状态
COLOR_ACCENT = "#5b7fff"          # 主强调色（蓝紫）
COLOR_ACCENT_HOVER = "#7a96ff"    # 强调色悬停
COLOR_ACCENT_GLOW = "rgba(91,127,255,0.25)"  # 发光效果
COLOR_SUCCESS = "#22c55e"         # 录音中（绿）
COLOR_SUCCESS_GLOW = "rgba(34,197,94,0.25)"
COLOR_DANGER = "#ef4444"          # 危险/停止
COLOR_TEXT_PRIMARY = "#e8ecf8"    # 主文字
COLOR_TEXT_SECONDARY = "#8892aa"  # 次要文字
COLOR_TEXT_MUTED = "#4a5268"      # 弱化文字
COLOR_BORDER = "#252a38"          # 边框
COLOR_BORDER_ACTIVE = "#3d4561"   # 激活边框
COLOR_SCROLLBAR = "#252a38"       # 滚动条
COLOR_SCROLLBAR_HANDLE = "#3d4561"

MAIN_STYLE = f"""
/* ─── 全局 ─────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 14px;
}}

/* ─── 顶部标题栏 ─────────────────────── */
#titleBar {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLOR_BG_SURFACE},
        stop:1 {COLOR_BG_ELEVATED}
    );
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 0 20px;
}}

#appTitle {{
    color: {COLOR_TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

#appSubtitle {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
    margin-left: 8px;
}}

/* ─── 状态指示器 ─────────────────────── */
#statusDot {{
    border-radius: 5px;
    min-width: 10px;
    min-height: 10px;
    max-width: 10px;
    max-height: 10px;
}}

#statusLabel {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
}}

/* ─── 主录音按钮 ─────────────────────── */
#recordButton {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLOR_ACCENT},
        stop:1 #4a6ee0
    );
    color: white;
    border: none;
    border-radius: 40px;
    font-size: 16px;
    font-weight: 700;
    min-width: 80px;
    min-height: 80px;
    max-width: 80px;
    max-height: 80px;
    letter-spacing: 0.5px;
}}

#recordButton:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLOR_ACCENT_HOVER},
        stop:1 {COLOR_ACCENT}
    );
}}

#recordButton:pressed {{
    background: #4055cc;
    padding-top: 2px;
}}

#recordButton[recording="true"] {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLOR_SUCCESS},
        stop:1 #16a34a
    );
    border: 2px solid {COLOR_SUCCESS};
}}

#recordButton[recording="true"]:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #4ade80,
        stop:1 {COLOR_SUCCESS}
    );
}}

/* ─── 操作按钮 ──────────────────────── */
#actionButton {{
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}}

#actionButton:hover {{
    background-color: {COLOR_BG_HOVER};
    color: {COLOR_TEXT_PRIMARY};
    border-color: {COLOR_BORDER_ACTIVE};
}}

#actionButton:pressed {{
    background-color: {COLOR_BG_ELEVATED};
    padding-top: 9px;
    padding-bottom: 7px;
}}

/* ─── 文字显示区域 ──────────────────── */
#transcriptArea {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 16px;
    font-size: 15px;
    line-height: 1.8;
    selection-background-color: {COLOR_ACCENT};
}}

#transcriptArea:focus {{
    border-color: {COLOR_BORDER_ACTIVE};
    outline: none;
}}

/* ─── 历史记录面板 ──────────────────── */
#historyPanel {{
    background-color: {COLOR_BG_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}

#historyList {{
    background-color: transparent;
    border: none;
    outline: none;
}}

#historyList::item {{
    background-color: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    margin: 3px 6px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 13px;
}}

#historyList::item:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_BORDER_ACTIVE};
}}

#historyList::item:selected {{
    background-color: rgba(91,127,255,0.15);
    border-color: {COLOR_ACCENT};
    color: {COLOR_TEXT_PRIMARY};
}}

/* ─── 分组标题 ───────────────────────── */
#panelTitle {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 0 4px;
}}

/* ─── 信息标签 ───────────────────────── */
#infoLabel {{
    color: {COLOR_TEXT_MUTED};
    font-size: 12px;
}}

#countLabel {{
    color: {COLOR_ACCENT};
    font-size: 12px;
    font-weight: 600;
}}

/* ─── 模型选择下拉 ──────────────────── */
QComboBox {{
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {COLOR_BORDER_ACTIVE};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER_ACTIVE};
    border-radius: 8px;
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: rgba(91,127,255,0.2);
    outline: none;
    padding: 4px;
}}

/* ─── 滚动条 ─────────────────────────── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 4px 2px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLOR_SCROLLBAR_HANDLE};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLOR_BORDER_ACTIVE};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    height: 0;
}}

/* ─── 分隔线 ─────────────────────────── */
QFrame[frameShape="4"] {{
    color: {COLOR_BORDER};
    max-height: 1px;
}}

/* ─── 进度条（模型加载） ────────────── */
QProgressBar {{
    background-color: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    text-align: center;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
    max-height: 20px;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLOR_ACCENT},
        stop:1 {COLOR_ACCENT_HOVER}
    );
    border-radius: 5px;
}}

/* ─── 工具提示 ───────────────────────── */
QToolTip {{
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_ACTIVE};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ─── 菜单栏 ─────────────────────────── */
QMenuBar {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_SECONDARY};
    border-bottom: 1px solid {COLOR_BORDER};
    font-size: 13px;
    padding: 2px 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border-radius: 4px;
}}

QMenu {{
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_ACTIVE};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
    font-size: 13px;
}}

QMenu::item:selected {{
    background-color: rgba(91,127,255,0.2);
    color: {COLOR_TEXT_PRIMARY};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLOR_BORDER};
    margin: 4px 8px;
}}

/* ─── 音量波形容器 ──────────────────── */
#waveformWidget {{
    background-color: {COLOR_BG_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
"""

# 录音状态样式
STATUS_DOT_IDLE = f"background-color: {COLOR_TEXT_MUTED}; border-radius: 5px;"
STATUS_DOT_RECORDING = f"background-color: {COLOR_SUCCESS}; border-radius: 5px;"
STATUS_DOT_PROCESSING = f"background-color: {COLOR_ACCENT}; border-radius: 5px;"
STATUS_DOT_ERROR = f"background-color: {COLOR_DANGER}; border-radius: 5px;"
