# Toolbox

<p align="center">
  <b>个人开发者工具箱</b> &mdash; Web 应用、命令行工具、小玩具与代码片段的 Monorepo 合集
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 设计理念

这是一个**本地优先、工具独立、持续积累**的 Monorepo。仓库本身不定义业务逻辑，只负责收纳和索引。每个子目录承载一类工具的集合，各自拥有独立的依赖、配置和文档，可单独安装运行，也可随仓库整体克隆。

---

## 目录分类

| 目录 | 定位 | 示例 |
|------|------|------|
| [`apps/`](#apps) | Web 应用 / 桌面应用 | Format Converter |
| [`cli-tools/`](#cli-tools) | 纯命令行工具 | — |
| [`toys/`](#toys) | 小型趣味玩具 | — |
| [`snippets/`](#snippets) | 可复用代码片段 | — |
| [`tests/`](#tests) | 实验性/测试程序 | — |

---

## apps

Web 应用或桌面应用程序，每个子目录是一个完整的独立项目。

### Format Converter

<p align="center">
  <b>万能格式转换 Web 服务</b><br/>
  <sub>前后端分离 · 40+ 格式 · 6 大类别 · 批量处理 · Docker 一键部署</sub>
</p>

一款前后端分离的 Web 格式转换服务，支持文档、图片、音频、视频、数据等格式之间的快速互转。

| 类别 | 支持格式 | 引擎 |
|------|----------|------|
| 📄 文档 | PDF · DOCX · DOC · TXT · MD · HTML · EPUB · RTF | pdf2docx · PyPDF2 · python-docx · weasyprint |
| 🖼️ 图片 | JPG · PNG · WEBP · BMP · GIF · ICO · TIFF · SVG | Pillow |
| 🎵 音频 | MP3 · WAV · FLAC · OGG · AAC · M4A · WMA · Opus · AIFF | pydub + ffmpeg |
| 🎬 视频 | MP4 · AVI · MKV · MOV · WEBM · FLV · WMV | ffmpeg-python |
| 📊 数据 | JSON · YAML · CSV · XML · TOML | PyYAML · xmltodict · tomli |

**功能亮点：**
- 🚀 **前后端分离** — React 18 + FastAPI，标准的 RESTful 架构
- 🎨 **极致 UI** — 玻璃拟态设计、Framer Motion 动画、Tailwind CSS 深色主题
- 🤖 **3D 互动人偶** — Three.js 渲染的页角角色，支持皮肤切换
- 📦 **一键部署** — Docker Compose 一条命令上线
- 📚 **Auto API Docs** — FastAPI 自动生成 Swagger / ReDoc 文档
- 📁 **批量处理** — 拖放上传，实时进度追踪

```bash
cd apps/format_converter
docker compose up -d
# 访问 http://localhost:8000
```

> 音频/视频转换需要 FFmpeg（Docker 镜像已内置）

详细文档 → [apps/format_converter/README.md](apps/format_converter/README.md)
部署教程 → [apps/format_converter/DEPLOY.md](apps/format_converter/DEPLOY.md)

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
├── apps/                                         # Web / 桌面应用
│   └── format_converter/                         #   Format Converter
│       ├── backend/                              #     FastAPI 后端
│       │   ├── format_converter/
│       │   │   ├── main.py                       #       FastAPI 入口 + 路由
│       │   │   ├── converters/                   #       转换引擎
│       │   │   │   ├── document_converter.py     #         文档 (PDF/Word/MD)
│       │   │   │   ├── image_converter.py        #         图片 (Pillow)
│       │   │   │   ├── audio_converter.py        #         音频 (pydub)
│       │   │   │   ├── video_converter.py        #         视频 (ffmpeg)
│       │   │   │   └── data/                     #         数据格式 (5个)
│       │   │   └── utils/                        #       格式映射 + 工具
│       │   └── requirements.txt
│       ├── frontend/                             #     React 前端
│       │   ├── src/
│       │   │   ├── App.jsx                       #       主应用
│       │   │   ├── api/                          #       API 客户端
│       │   │   └── components/                   #       组件库
│       │   │       ├── Character3D.jsx           #         3D 互动人偶
│       │   │       ├── Navbar.jsx                #         导航栏
│       │   │       ├── DropZone.jsx              #         拖放上传
│       │   │       ├── FormatSelector.jsx        #         格式选择
│       │   │       ├── FileList.jsx              #         文件列表
│       │   │       ├── ProgressPanel.jsx         #         进度面板
│       │   │       ├── LogPanel.jsx              #         日志面板
│       │   │       └── DownloadPanel.jsx         #         下载面板
│       │   └── vite.config.js
│       ├── Dockerfile                            #     Docker 构建
│       ├── docker-compose.yml                    #     Docker Compose
│       ├── nginx.conf                            #     Nginx 配置
│       ├── DEPLOY.md                             #     部署教程
│       ├── README.md                             #     项目文档
│       └── pyproject.toml
│
├── cli-tools/                                    # 纯命令行工具
├── toys/                                         # 小型趣味玩具
├── snippets/                                     # 可复用代码片段
├── tests/                                        # 实验性/测试程序
│
├── LICENSE                                       # MIT
├── pyproject.toml                                # 仓库级配置
└── README.md                                     # 本文件
```

---

## 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| **前端框架** | React 18 + Vite 5 | 业界主流 SPA 方案，极快的 HMR 和构建速度 |
| **UI 样式** | Tailwind CSS 3 | 原子化 CSS，深色主题，玻璃拟态设计 |
| **动画** | Framer Motion 11 | 声明式动画库，流畅的页面过渡 |
| **3D 渲染** | Three.js + React Three Fiber | WebGL 3D 角色渲染，声明式 3D 场景 |
| **后端框架** | FastAPI | 异步高性能 Python Web 框架，自动生成 API 文档 |
| **文档转换** | pdf2docx · python-docx · PyPDF2 · weasyprint | PDF/Word/Markdown/HTML 互转 |
| **音频** | pydub + ffmpeg | 简洁 Python API + 强大编解码后端 |
| **视频** | ffmpeg-python | ffmpeg CLI 的 Pythonic 封装 |
| **图片** | Pillow | Python 图像处理事实标准 |
| **数据** | PyYAML · xmltodict · tomli | 纯文本格式互转管道 |
| **部署** | Docker + Docker Compose | 一键编排，环境一致 |

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
