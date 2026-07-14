# Format Converter 🛠️

全功能桌面格式转换程序 — 一站式支持**数据格式**、**音频格式**、**视频格式**及**图片格式**的批量相互转换。

## 功能特性

| 功能 | 说明 |
|------|------|
| **数据格式** | JSON、YAML、CSV、XML、TOML 等互转 |
| **音频格式** | MP3、WAV、FLAC、OGG、AAC、M4A、WMA、Opus、AIFF、AC3 |
| **视频格式** | MP4、AVI、MKV、MOV、WEBM、FLV、WMV |
| **图片格式** | JPG、PNG、WEBP、BMP、GIF、TIFF、ICO |
| **批量处理** | 支持一次添加多个文件并批量转换 |
| **拖放支持** | 直接拖拽文件到界面即可添加 |
| **进度反馈** | 实时显示整体进度和单文件进度 |
| **错误处理** | 完善的错误捕获和日志输出 |
| **深色主题** | 现代化深色 UI 界面 |

## 快速开始

### 环境要求

- Python >= 3.9
- [FFmpeg](https://ffmpeg.org/download.html) (音频/视频转换必需，需添加到系统 PATH)

### 安装

```bash
# 1. 进入项目目录
cd apps/format_converter

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. (可选) 安装 FFmpeg
#   Windows: 从 https://ffmpeg.org/download.html 下载并添加到 PATH
#   macOS:   brew install ffmpeg
#   Linux:   sudo apt install ffmpeg
```

### 启动

```bash
# 方式一：作为模块启动
python -m format_converter

# 方式二：直接运行
python src/format_converter/main.py

# 方式三：pip install 后使用命令行
pip install -e .
format-converter
```

## 项目结构

```
format_converter/
├── README.md                       # 项目说明
├── pyproject.toml                  # 项目配置
├── requirements.txt                # Python 依赖
├── src/
│   └── format_converter/           # 主包
│       ├── __init__.py             # 包初始化
│       ├── __main__.py             # python -m 入口
│       ├── main.py                 # 应用入口
│       ├── gui/                    # GUI 层
│       │   ├── main_window.py      # 主窗口
│       │   ├── styles/theme.py     # 深色主题 QSS
│       │   └── widgets/            # UI 组件
│       │       ├── drop_zone.py    # 拖放区域
│       │       ├── format_selector.py # 格式选择器
│       │       ├── progress_panel.py  # 进度面板
│       │       └── task_list.py    # 任务列表
│       ├── converters/             # 转换器层
│       │   ├── __init__.py         # 统一调度
│       │   ├── data/               # 数据格式转换器
│       │   │   ├── json_converter.py
│       │   │   ├── yaml_converter.py
│       │   │   ├── csv_converter.py
│       │   │   ├── xml_converter.py
│       │   │   └── toml_converter.py
│       │   ├── audio_converter.py  # 音频转换器 (pydub)
│       │   ├── video_converter.py  # 视频转换器 (ffmpeg-python)
│       │   └── image_converter.py  # 图片转换器 (Pillow)
│       └── utils/                  # 工具层
│           ├── file_utils.py       # 文件/格式检测工具
│           └── worker.py           # QThread 异步工作线程
└── resources/
    └── licenses/
        └── THIRD_PARTY.md          # 第三方开源许可证声明
```

## 第三方依赖与许可

本项目严格遵守开源规范。依赖关系如下：

| 依赖 | 许可 | 用途 |
|------|------|------|
| [PySide6](https://wiki.qt.io/Qt_for_Python) | LGPL v3 | GUI 框架 |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | YAML 解析 |
| [xmltodict](https://github.com/martinblech/xmltodict) | MIT | XML 解析 |
| [tomli/tomli-w](https://github.com/hukkin/tomli) | MIT | TOML 解析 |
| [Pillow](https://github.com/python-pillow/Pillow) | HPND | 图片处理 |
| [pydub](https://github.com/jiaaro/pydub) | MIT | 音频处理 |
| [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) | Apache-2.0 | 视频转换 |
| [FFmpeg](https://ffmpeg.org/) | LGPL/GPL | 音视频编解码 |

> 详细许可声明见 [resources/licenses/THIRD_PARTY.md](resources/licenses/THIRD_PARTY.md)

## 使用示例

### 数据格式转换
```
选择"数据格式"标签页 → 添加 data.json → 目标格式选 YAML → 点击转换
```

### 音频格式转换
```
选择"音频格式"标签页 → 添加 music.wav → 目标格式选 MP3 → 点击转换
```

### 视频格式转换
```
选择"视频格式"标签页 → 添加 video.mov → 目标格式选 MP4 → 点击转换
```

### 图片格式转换
```
选择"图片格式"标签页 → 添加 photo.png → 目标格式选 WEBP → 点击转换
```

## 许可证

本项目采用 [MIT License](../../LICENSE)。第三方依赖的许可信息详见 [THIRD_PARTY.md](resources/licenses/THIRD_PARTY.md)。
