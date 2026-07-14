# Toolbox

<p align="center">
  <b>个人开发者工具箱</b> &mdash; 独立桌面工具、命令行工具、小玩具与代码片段的 Monorepo 合集
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-%3E%3D3.9-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

---

## 设计理念

这是一个**本地优先、工具独立、持续积累**的 Monorepo。仓库本身不定义业务逻辑，只负责收纳和索引。每个子目录承载一类工具的集合，各自拥有独立的依赖、配置和文档，可单独安装运行，也可随仓库整体克隆。

---

## 目录分类

| 目录 | 定位 | 示例 |
|------|------|------|
| [`apps/`](#apps) | GUI 桌面应用 | 格式转换器 |
| [`cli-tools/`](#cli-tools) | 纯命令行工具 | — |
| [`toys/`](#toys) | 小型趣味玩具 | — |
| [`snippets/`](#snippets) | 可复用代码片段 | — |
| [`tests/`](#tests) | 实验性/测试程序 | — |

---

## apps

GUI 桌面应用程序，每个子目录是一个完整的独立项目。

### Format Converter

<p align="center">
  <b>全功能桌面格式转换程序</b><br/>
  <sub>29+ 种格式 · 4 大类别 · 批量处理 · 拖放交互 · 深色 GUI</sub>
</p>

一款跨平台的桌面应用，覆盖日常开发中几乎所有的文件格式转换需求。

| 类别 | 支持格式 | 引擎 |
|------|----------|------|
| 数据 | JSON · YAML · CSV · XML · TOML | PyYAML · xmltodict · tomli |
| 图片 | JPG · PNG · WEBP · BMP · GIF · TIFF · ICO | Pillow |
| 音频 | MP3 · WAV · FLAC · OGG · AAC · M4A · WMA · Opus · AIFF · AC3 | pydub + ffmpeg |
| 视频 | MP4 · AVI · MKV · MOV · WEBM · FLV · WMV | ffmpeg-python |

**功能亮点：**
- 拖拽文件直接添加，支持批量处理
- 多标签页 UI，每种类别独立操作互不干扰
- 异步转换 + 实时进度条 + 日志面板
- 自动检测源格式，智能匹配可转换的目标格式
- 完善的异常捕获：格式不支持、文件不存在、编解码器缺失等均有中文提示

```bash
cd apps/format_converter
pip install -r requirements.txt
python -m format_converter
```

> 音频/视频转换需要安装 FFmpeg 并添加到系统 PATH

详细文档 → [apps/format_converter/README.md](apps/format_converter/README.md)

---

## cli-tools

存放纯命令行工具的目录。每个工具是独立的 Python 包或脚本，通过命令行参数交互，适合自动化流程、批量处理和 CI/CD 集成。

> *暂无工具，待添加。*

---

## toys

小型趣味项目 / 创意玩具 / 一次性脚本。代码量小，功能独立，风格轻松。

> *暂无项目，待添加。*

---

## snippets

可复用的代码片段和实用函数。按语言或用途分类存放，方便跨项目复制使用。

> *暂无片段，待添加。*

---

## tests

实验性项目、技术验证（PoC）和临时测试程序。这里的代码不保证稳定性，主要用于探索新技术、验证方案可行性。

> *暂无内容，待添加。*

---

## 仓库结构

```
toolbox/
├── apps/                                    # GUI 桌面工具
│   └── format_converter/                    #   Format Converter
│       ├── src/format_converter/            #     源码
│       │   ├── gui/                         #     GUI 层
│       │   │   ├── main_window.py           #       QTabWidget 主窗口
│       │   │   ├── styles/theme.py          #       QSS 深色主题
│       │   │   └── widgets/                 #       可复用组件
│       │   ├── converters/                  #     转换器层
│       │   │   ├── data/                    #       数据格式 (5个)
│       │   │   ├── audio_converter.py       #       音频 (pydub)
│       │   │   ├── video_converter.py       #       视频 (ffmpeg)
│       │   │   └── image_converter.py       #       图片 (Pillow)
│       │   └── utils/                       #     工具层
│       ├── resources/licenses/              #     第三方许可证
│       └── pyproject.toml / requirements.txt
│
├── cli-tools/                               # 纯命令行工具
├── toys/                                    # 小型趣味玩具
├── snippets/                                # 可复用代码片段
├── tests/                                   # 实验性/测试程序
│
├── LICENSE                                  # MIT
├── pyproject.toml                           # 仓库级配置
└── README.md                                # 本文件
```

---

## 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| **GUI** | PySide6 (Qt 6) | LGPL 许可，跨平台原生外观，完善的信号/槽机制 |
| **异步** | QThread + Signal | 不阻塞 UI 主线程，信号驱动进度更新 |
| **音频** | pydub + ffmpeg | pydub 提供简洁的 Python API，底层经 ffmpeg 编解码 |
| **视频** | ffmpeg-python | 对 ffmpeg CLI 的 Pythonic 封装，覆盖主流容器格式 |
| **图片** | Pillow | 事实标准的 Python 图像库，支持 30+ 格式 |
| **数据** | PyYAML · xmltodict · tomli | 纯文本格式通过「解析→中间对象→序列化」管道互转 |
| **架构** | 注册表模式 | 新增格式只需注册 loader/dumper，无需修改调度逻辑 |

---

## 贡献新工具

1. 根据工具类型放入对应目录（`apps/`、`cli-tools/`、`toys/`）
2. 按标准 Python 项目结构组织代码
3. 提供独立的 `pyproject.toml`、`requirements.txt` 和 `README.md`
4. 在本 README 的对应章节添加条目并简要描述

保持各工具**自包含**——仓库不设统一的虚拟环境或全局依赖，每个工具独立管理自己的运行时。

---

## 开源合规

每个子项目均在 `resources/licenses/THIRD_PARTY.md` 中完整列出了所有第三方依赖的版权信息和许可证原文摘要，遵守 MIT、LGPL、Apache-2.0、HPND 等开源协议要求。

---

## 许可

MIT License © [zhcnhan](https://github.com/zhcnhan)
