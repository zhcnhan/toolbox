# Toolbox

<p align="center">
  <b>个人开发者工具箱</b> &mdash; Web 应用、命令行工具、自动化脚本的 Monorepo 合集
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

这是一个**本地优先、工具独立、持续积累**的 Monorepo。仓库本身不定义业务逻辑，只负责收纳和索引。每个子目录承载一个独立工具，各自拥有独立的依赖、配置和文档，可单独安装运行，也可随仓库整体克隆。

---

## 目录分类

| 目录 | 定位 | 内容 |
|------|------|------|
| [`apps/`](#apps) | Web 应用 / CLI 工具 | Format Converter · Batch Background Remover |
| [`cli-tools/`](#cli-tools) | 纯命令行工具 | Git Mirror |
| [`toys/`](#toys) | 小型趣味玩具 | 待添加 |
| [`snippets/`](#snippets) | 可复用代码片段 | 待添加 |
| [`tests/`](#tests) | 实验性/测试程序 | 待添加

---

## apps

每个子目录是一个完整的独立项目，自带 `README`、依赖配置，可单独安装部署。

### Format Converter

万能格式转换 Web 服务，前后端分离。

| 类别 | 支持格式 | 引擎 |
|------|----------|------|
| 📄 文档 | PDF · DOCX · DOC · TXT · MD · HTML · EPUB · RTF | pdf2docx · PyPDF2 · python-docx · weasyprint |
| 🖼️ 图片 | JPG · PNG · WEBP · BMP · GIF · ICO · TIFF · SVG | Pillow |
| 🎵 音频 | MP3 · WAV · FLAC · OGG · AAC · M4A · WMA · Opus · AIFF | pydub + ffmpeg |
| 🎬 视频 | MP4 · AVI · MKV · MOV · WEBM · FLV · WMV | ffmpeg-python |
| 📊 数据 | JSON · YAML · CSV · XML · TOML | PyYAML · xmltodict · tomli |

**功能亮点：**
- 🚀 **前后端分离** — React 18 + FastAPI，RESTful 架构
- 🎨 **极致 UI** — 玻璃拟态、Framer Motion 动画、深色主题
- 🤖 **3D 互动角色** — Three.js 渲染，多模型切换，可拖拽甩飞/点击敲打/自动睡觉/心情系统/叫声
- 📦 **一键部署** — Docker Compose 或 OpenResty + systemd
- 📚 **Auto API Docs** — Swagger / ReDoc

```bash
cd apps/format_converter
# Docker 方式
docker compose up -d
# 或手动部署 → 详见 DEPLOY.md
```

[完整文档](apps/format_converter/README.md) · [部署教程](apps/format_converter/DEPLOY.md)

### Batch Background Remover

批量抠图 Web 服务，8 引擎可选（本地 + 云端）。

| 引擎 | 类型 | 自动抠图 | 提示词分割 | 价格 |
|------|------|:-------:|:---------:|------|
| rembg | 本地 | ✅ | ❌ | 免费 |
| SAM 1 ViT-L 🆕 | 本地 | ❌ | ✅ | 硅基流动按量计费 |
| 图标抠图 🆕 | 本地 | ✅ | ❌ | 免费 |
| **Kimi (多边形坐标)** ✨ | 云端坐标 | ❌ | ✅ | 硅基流动按量计费 |
| **Gemini Mask** ✨ | 云端坐标 | ❌ | ✅ | 极低 Token 成本 |
| remove.bg | 云端 | ✅ | ❌ | 50张/月免费 |
| 擦个图 | 云端 | ✅ | ❌ | 0.1元/次 |
| 自定义 | 云端 | ✅ | ✅ | 取决于服务商 |

**功能亮点：**
- ✂️ **2 种提示词模式** — Gemini Mask 支持「多边形坐标」和「掩膜 PNG」两种输出
- ⚡ **Gemini Mask (本地切割)** — 利用 Gemini 视觉定位 → 本地保留原图分辨率抠图
- 🧪 **代理连通性测试** — 设置页一键测试多个网站（Google/Baidu/GitHub/Bing）
- 🌐 **代理支持** — HTTP 代理（含 Basic 认证），方便服务器走 VPN
- 🔌 **插件式架构** — 新增引擎只需写一个 `*_engine.py` 文件
- 📦 **批量处理** — 一次拖入多张图，逐张抠图，一键打包
- 🍎 **macOS 原生支持** — `.command` 桌面启动器 / PWA 添加到程序坞
- 🎀 **可爱界面** — 玻璃拟态深色主题，Framer Motion 动画

```bash
cd apps/batch_bg_remover
# 一键部署（推荐）
chmod +x deploy.sh && ./deploy.sh
# macOS 原生运行
bash make-mac-app.sh  # 生成桌面启动器，之后双击即可
# 或手动启动
python run.py
```

[完整文档](apps/batch_bg_remover/README.md) · [部署教程](apps/batch_bg_remover/DEPLOY.md)

---

## cli-tools

存放纯命令行工具的目录。每个工具是独立的 Python 包或脚本，通过命令行参数交互，适合自动化流程和 CI/CD 集成。

### Git Mirror

通用 Git 仓库双向镜像同步工具。在任意两个 Git remote（如 Gitee ↔ GitHub）之间同步代码，支持自动凭据管理。

```bash
cd cli-tools/git-mirror
pip install -e .

git-mirror add <name> -r gitee=<url> -r github=<url>
git-mirror sync <name> --from gitee --to github
git-mirror sync --all
```

**功能亮点：**
- 🔄 **双向同步** — 任意两个 remote 之间的全量镜像
- 🔐 **自动凭据** — push 失败时交互式询问 token，保存复用
- 📦 **多仓库** — 同时管理多个仓库的同步规则
- ⏰ **定时运行** — 配合 crontab 实现自动同步

[完整文档](cli-tools/git-mirror/README.md)

---

## toys

小型趣味项目 / 创意玩具 / 一次性脚本。代码量小，功能独立，风格轻松。

> *待添加*

---

## snippets

可复用的代码片段和实用函数。按语言或用途分类存放，方便跨项目复制使用。

> *待添加*

---

## tests

实验性项目、技术验证（PoC）和临时测试程序。代码不保证稳定性，主要用于探索新技术。

> *待添加*

---

## 仓库结构

```
toolbox/
├── apps/
│   ├── README.md                                           # 应用目录概览
│   ├── format_converter/       # 万能格式转换 Web 服务
│   │   ├── backend/            #   FastAPI 后端 + 转换引擎
│   │   ├── frontend/           #   React 前端 + 3D 互动
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── nginx.conf
│   │   ├── DEPLOY.md
│   │   └── README.md
│   └── batch_bg_remover/       # 批量抠图 Web 服务
│       ├── backend/            #   FastAPI 后端 + 8 引擎
│       ├── frontend/           #   React 前端 + PWA 支持
│       ├── run.py              #   一键启动脚本
│       ├── deploy.sh           #   一键部署脚本（Docker）
│       ├── batch-bg-mac.sh     #   macOS 一键启动脚本
│       ├── make-mac-app.sh     #   生成 macOS .app 桌面应用
│       ├── MAC.md              #   macOS 白痴教程
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── nginx.conf
│       ├── batch-bg-remover.service  # systemd 服务
│       ├── DEPLOY.md
│       └── README.md
├── cli-tools/
│   ├── README.md                                           # 命令行工具概览
│   └── git-mirror/             # Git 仓库双向镜像同步
│       ├── git_mirror/         #   Python 包
│       ├── pyproject.toml
│       └── README.md
├── toys/                       # 小型趣味玩具（待添加）
├── snippets/                   # 可复用代码片段（待添加）
├── tests/                      # 实验性/测试程序（待添加）
├── resources/                  # 第三方声明
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## 技术栈

| 层 | 选型 |
|----|------|
| 前端框架 | React 18 + Vite 5 |
| UI 样式 | Tailwind CSS 3 + Framer Motion |
| 3D 渲染 | Three.js + React Three Fiber |
| 后端框架 | FastAPI |
| 文档转换 | pdf2docx · python-docx · PyPDF2 · weasyprint |
| 音视频 | pydub + ffmpeg |
| 图片 | Pillow · cairosvg |
| 部署 | Docker + OpenResty + systemd |
| CLI | Python argparse (git-mirror) |

---

## 贡献新工具

1. 根据工具类型放入对应目录（`apps/`、`cli-tools/`、`toys/`）
2. 按标准 Python 项目结构组织代码
3. 提供独立的 `pyproject.toml`、`requirements.txt` 和 `README.md`
4. 在本 README 的对应章节添加条目并简要描述

保持各工具**自包含**——不设统一的虚拟环境或全局依赖。

---

## 开源合规

第三方依赖的版权信息和许可证摘要见 `resources/licenses/THIRD_PARTY.md`。

---

## 许可

MIT License © [zhcnhan](https://github.com/zhcnhan)
