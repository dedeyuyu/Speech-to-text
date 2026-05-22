# Whisper 语音转文字

基于 [OpenAI Whisper](https://github.com/openai/whisper) 的本地语音识别桌面应用。支持实时转录、多语言检测，所有数据**仅存储在本地**，不上传任何内容。

## ✨ 功能特点

- 🎙 **实时转录** — 边说边显示，VAD 自动检测停顿
- 🌍 **多语言支持** — 中文、英文、日文、韩文等（自动检测）
- 🔒 **完全私密** — 录音和文字均不上传，本地 JSON 存储
- 📊 **音量可视化** — 实时波形显示
- 📁 **历史记录** — 按日期查看，支持导出 TXT
- 🖥 **现代界面** — 深色主题，Material Design 风格

## 🚀 快速开始

### 环境要求

- Python 3.8 或以上
- Windows 10/11（macOS / Linux 理论上也支持）
- 麦克风

### 安装依赖

```bash
pip install -r requirements.txt
```

> **Windows 用户注意**：首次运行时，Whisper 会自动下载 `small` 模型（约 244MB）。
> 如果出现 ffmpeg 相关错误，请安装 FFmpeg：
> ```
> winget install ffmpeg
> ```
> 或从 https://ffmpeg.org/download.html 下载后添加到 PATH。

### 运行

```bash
python main.py
```

## 📦 使用方法

1. 启动后等待模型加载（右上角状态变为"模型加载完成 ✓"）
2. 点击 ⏺ 按钮开始录音
3. 正常说话，停顿后文字自动显示
4. 点击 ⏹ 停止录音
5. 点击"💾 导出文本"可将记录保存为 TXT 文件

## 📁 数据存储

所有转录记录存储在：

```
data/transcripts/YYYY-MM-DD.json
```

格式示例：
```json
[
  {
    "id": "20240522_143025_123456",
    "timestamp": "2024-05-22T14:30:25.123456",
    "text": "你好，这是一段测试语音。",
    "language": "zh"
  }
]
```

## 🔒 隐私说明

| 数据类型 | 处理方式 |
|---------|---------|
| 麦克风音频 | 仅在内存中处理，不写入磁盘 |
| 转录文字 | 仅保存到本地 `data/` 目录 |
| Whisper 模型 | 下载到 `~/.cache/whisper/` 本地缓存 |
| 网络请求 | 仅首次下载模型时联网，之后完全离线 |

## 🛠 项目结构

```
Speech-to-text/
├── main.py                    # 程序入口
├── requirements.txt           # Python 依赖
├── core/
│   ├── recorder.py            # 麦克风录音模块
│   ├── transcriber.py         # Whisper 实时转录模块
│   └── storage.py             # 本地数据存储
├── ui/
│   ├── main_window.py         # 主窗口 UI
│   └── styles.py              # 深色主题样式
├── .github/
│   ├── workflows/
│   │   ├── release.yml        # 发布构建 + SLSA Attestation
│   │   └── codeql.yml         # 代码安全扫描
│   └── dependabot.yml         # 依赖自动更新
└── data/
    └── transcripts/           # 本地转录记录（不提交到 Git）
```

## 📝 开源协议

MIT License
