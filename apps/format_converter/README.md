<p align="center">
  <h1 align="center">🔄 Format Converter</h1>
  <p align="center">
    <b>万能格式转换 Web 服务</b><br/>
    <sub>前后端分离 · 40+ 格式 · 6 大类别 · 171 条转换路径全部通过测试 · 一键部署</sub>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/vite-5-646CFF?logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/three.js-0.170-000000?logo=three.js&logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/tests-171/171-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 简介

Format Converter 是一个**前后端分离**的 Web 格式转换服务，支持文档、图片、音频、视频、数据等多种格式之间的快速互转。采用现代化技术栈，可直接部署至服务器供团队使用。

### 核心特性

- **40+ 格式支持** — 涵盖文档（PDF/Word/Markdown/EPUB/RTF）、图片（JPG/PNG/WebP/GIF/SVG）、音频（MP3/WAV/FLAC等9种）、视频（MP4/MKV/WEBM等7种）、数据（JSON/YAML/CSV/XML/TOML）
- **171 条转换路径** — 全部通过自动化测试验证，覆盖所有格式组合
- **批量处理** — 一次上传多个文件，并行转换
- **实时进度** — WebSocket 实时推送转换进度
- **3D 互动小猫** — 页面右下角的物理小猫，可拖拽、拍打、甩飞，支持多种表情反馈
- **一键部署** — Docker Compose 一条命令上线，FFmpeg + LibreOffice + GTK3 全部内置
- **Auto API Docs** — FastAPI 自动生成 Swagger / ReDoc 文档
- **内置测试** — 部署后可随时运行测试验证所有转换路径

---

## 架构

```
┌──────────────────────────────────────────────────┐
│                    Nginx (可选)                    │
│  /         → 前端静态文件 (React SPA)              │
│  /api/*    → 后端 API (FastAPI)                   │
└──────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐    ┌─────────────────────────┐
│   Frontend      │    │       Backend           │
│   React 18      │    │   FastAPI (Python)      │
│   Vite 5        │◄──►│                         │
│   Tailwind CSS  │REST│   converters/           │
│   Three.js      │    │   ├── document (8种路径) │
│   Framer Motion │    │   ├── image   (Pillow)  │
└─────────────────┘    │   ├── audio   (pydub)   │
                       │   ├── video   (ffmpeg)  │
                       │   └── data    (5种)     │
                       └─────────────────────────┘
                                │
                   ┌────────────┼────────────┐
                   ▼            ▼            ▼
              ┌─────────┐ ┌──────────┐ ┌──────────┐
              │ FFmpeg  │ │LibreOffice│ │ GTK3/    │
              │ (音视频) │ │ (DOC转换) │ │ Cairo    │
              └─────────┘ └──────────┘ │ (SVG/PDF) │
                                       └──────────┘
```

---

## 支持的格式

| 类别 | 输入格式 | 输出格式 | 引擎 |
|------|----------|----------|------|
| 📄 **文档** | PDF, DOCX, DOC, TXT, MD, HTML, RTF, EPUB | PDF, DOCX, TXT, MD, HTML | pdf2docx · python-docx · PyPDF2 · weasyprint · markdown · ebooklib · striprtf |
| 🖼️ **图片** | JPG, PNG, WEBP, BMP, GIF, ICO, TIFF, SVG | JPG, PNG, WEBP, BMP, GIF, ICO, TIFF | Pillow · cairosvg · svglib |
| 🎵 **音频** | MP3, WAV, FLAC, OGG, AAC, WMA, M4A, Opus, AIFF | MP3, WAV, FLAC, OGG, AAC, M4A, Opus | pydub + ffmpeg |
| 🎬 **视频** | MP4, AVI, MKV, MOV, WEBM, FLV, WMV | MP4, AVI, MKV, MOV, WEBM | ffmpeg (subprocess) |
| 📊 **数据** | JSON, YAML, CSV, XML, TOML | JSON, YAML, CSV, XML, TOML | PyYAML · xmltodict · tomli · stdlib |

### 转换路径统计

| 类别 | 路径数 | 测试状态 |
|------|--------|----------|
| 数据格式互转 | 20 | ✅ 全部通过 |
| 图片格式互转 | 49 | ✅ 全部通过（含 SVG → 7 种位图） |
| 音频格式互转 | 56 | ✅ 全部通过 |
| 视频格式互转 | 31 | ✅ 全部通过 |
| 文档格式转换 | 15 | ✅ 全部通过 |
| **合计** | **171** | **✅ 171/171 通过** |

---

## 快速开始

### 方式一：Docker 一键部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/zhcnhan/toolbox.git
cd toolbox/apps/format_converter

# 2. 构建并启动（首次约 5-10 分钟构建镜像）
docker compose up -d

# 3. 访问 http://localhost:8000
```

> Docker 镜像内置了所有依赖：FFmpeg、LibreOffice、GTK3/Cairo、中文字体、全部 Python 库。无需额外安装任何系统软件。

### 方式二：本地开发

#### 环境要求

- Python 3.10+（推荐 3.12）
- Node.js 20+
- FFmpeg（音频/视频转换）
- LibreOffice（DOC→DOCX、高质量 DOCX→PDF）
- GTK3 Runtime（SVG 转换，仅 Windows 需要）

#### 步骤

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 启动后端（开发模式，端口 8000）
uvicorn format_converter.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 新终端，安装前端依赖
cd ../frontend
npm install

# 4. 启动前端开发服务器（端口 5173，自动代理 API 到 8000）
npm run dev

# 5. 浏览器访问 http://localhost:5173
```

#### Windows 额外步骤

```powershell
# FFmpeg
winget install Gyan.FFmpeg

# LibreOffice
winget install TheDocumentFoundation.LibreOffice

# GTK3 Runtime（SVG 转换需要）
winget install tschoonj.GTKForWindows

# Python 3.13+ 额外：pydub 需要 audioop
# 项目已在 backend/ 下提供 pyaudioop.py 垫片，无需额外操作
```

---

## 运行测试

### Docker 环境中运行测试

```bash
# 运行全部 171 条转换路径测试
docker compose run --rm format-converter python test_resources/run_test.py

# 查看测试输出
# 测试结果输出到 test_resources/转换后/ 目录
```

### 本地运行测试

```bash
cd backend

# Windows PowerShell
$env:PYTHONIOENCODING='utf-8'
$env:PATH = 'C:\Program Files\GTK3-Runtime Win64\bin;C:\Program Files\LibreOffice\program;' + $env:PATH
python ../test_resources/run_test.py

# Linux / macOS
cd backend
python ../test_resources/run_test.py
```

测试脚本会读取 `test_resources/转换前/` 中的 37 个样例文件，执行所有 171 条转换路径，输出到 `test_resources/转换后/`。

---

## API 文档

启动后端后访问：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/formats` | 获取所有支持的格式 |
| `POST` | `/api/upload` | 上传文件 |
| `POST` | `/api/convert` | 启动批量转换 |
| `GET` | `/api/task/{id}` | 查询任务进度 |
| `DELETE` | `/api/task/{id}` | 取消任务 |
| `GET` | `/api/download/{id}/{filename}` | 下载单个结果 |
| `POST` | `/api/download-zip/{id}` | 打包下载全部结果 |

---

## 项目结构

```
apps/format_converter/
├── backend/                        # FastAPI 后端
│   ├── format_converter/
│   │   ├── main.py                 #   FastAPI 入口 + 路由
│   │   ├── converters/             #   转换引擎
│   │   │   ├── __init__.py         #     注册表 + 调度
│   │   │   ├── document_converter.py #   文档转换 (15条路径)
│   │   │   ├── image_converter.py  #     图片 (Pillow + cairosvg)
│   │   │   ├── audio_converter.py  #     音频 (pydub + ffmpeg)
│   │   │   ├── video_converter.py  #     视频 (ffmpeg subprocess)
│   │   │   └── data/               #     数据格式 (5个转换器)
│   │   └── utils/                  #   格式映射 + 文件工具
│   ├── pyaudioop.py                #   Python 3.13+ audioop 垫片
│   └── requirements.txt
├── frontend/                       # React 前端
│   ├── src/
│   │   ├── App.jsx                 #   主应用 + 状态管理
│   │   ├── api/index.js            #   API 客户端
│   │   ├── components/             #   组件
│   │   │   ├── Navbar.jsx          #     顶部导航
│   │   │   ├── TabNav.jsx          #     类别标签
│   │   │   ├── FormatSelector.jsx  #     格式选择
│   │   │   ├── DropZone.jsx        #     拖放上传
│   │   │   ├── FileList.jsx        #     文件列表
│   │   │   ├── ProgressPanel.jsx   #     进度面板
│   │   │   ├── LogPanel.jsx        #     日志面板
│   │   │   ├── DownloadPanel.jsx   #     下载面板
│   │   │   ├── InteractivePet.jsx  #     3D 互动小猫（物理引擎）
│   │   │   └── Character3D.jsx     #     3D 人偶（备用皮肤系统）
│   │   └── index.css               #    Tailwind + 自定义样式
│   ├── package.json
│   └── vite.config.js
├── test_resources/                 # 测试资源
│   ├── README.md                   #   测试文件清单
│   ├── run_test.py                 #   自动化测试脚本
│   ├── 转换前/                      #   37 个测试输入文件
│   └── 转换后/                      #   测试输出目录
├── resources/
│   └── licenses/
│       └── THIRD_PARTY.md          #   第三方开源声明
├── Dockerfile                      # Docker 构建
├── docker-compose.yml              # Docker Compose
├── nginx.conf                      # Nginx 配置（可选）
├── DEPLOY.md                       # 部署教程
└── README.md                       # 本文件
```

---

## 3D 互动小猫

页面右下角有一只基于物理引擎（Rapier）的 3D 小猫，支持丰富的互动：

- **拖拽** — 鼠标按住小猫可以拖来拖去
- **拍打** — 用棍子光标点击小猫，它会 squish 变形并露出疼痛表情
- **甩飞** — 快速拖动后松手，小猫会被甩飞并撞墙弹回
- **表情系统** — 小猫会根据互动方式切换表情（开心、疼痛、晕眩、爱心、生气）

小猫使用 `@react-three/rapier` 物理引擎实现真实的碰撞和弹跳效果。

---

## 常见问题

<details>
<summary><b>音频/视频转换报错</b></summary>
需要安装 FFmpeg：
<ul>
  <li>Windows: <code>winget install Gyan.FFmpeg</code></li>
  <li>macOS: <code>brew install ffmpeg</code></li>
  <li>Linux: <code>sudo apt install ffmpeg</code></li>
  <li>Docker: 已内置，无需安装</li>
</ul>
</details>

<details>
<summary><b>DOC → DOCX 转换报错</b></summary>
DOC → DOCX 需要安装 LibreOffice：
<ul>
  <li>Windows: <code>winget install TheDocumentFoundation.LibreOffice</code></li>
  <li>Linux: <code>sudo apt install libreoffice</code></li>
  <li>Docker: 已内置，无需安装</li>
</ul>
</details>

<details>
<summary><b>SVG 转换报错</b></summary>
SVG 转换需要 cairosvg（依赖 GTK3/Cairo）：
<ul>
  <li>Windows: <code>winget install tschoonj.GTKForWindows</code> + <code>pip install cairosvg</code></li>
  <li>Linux: <code>sudo apt install libcairo2 libpango-1.0-0</code> + <code>pip install cairosvg</code></li>
  <li>Docker: 已内置，无需安装</li>
</ul>
</details>

<details>
<summary><b>Markdown → PDF 转换报错</b></summary>
MD → PDF 需要 weasyprint 和 markdown：
<code>pip install weasyprint markdown</code>
<br/>Linux 还需安装系统依赖：<code>sudo apt install libpango-1.0-0 libpangocairo-1.0-0</code>
</details>

<details>
<summary><b>Python 3.13+ pydub 报 No module named 'audioop'</b></summary>
Python 3.13 移除了 <code>audioop</code> 模块。项目已在 <code>backend/pyaudioop.py</code> 中提供纯 Python 垫片。
如果仍报错，请确保从 <code>backend/</code> 目录启动，或将其加入 <code>PYTHONPATH</code>。
</details>

<details>
<summary><b>大文件转换超时</b></summary>
视频、音频等大文件的转换时间取决于文件大小和服务器性能。Docker 部署时可调整 COMPOSE_HTTP_TIMEOUT 或增加 Nginx 的 proxy_read_timeout。
</details>

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | React 18 + Vite 5 | 现代化 SPA |
| UI 样式 | Tailwind CSS 3 | 工具类优先，深色主题 |
| 动效 | Framer Motion 11 | 声明式动画 |
| 3D 渲染 | Three.js + React Three Fiber + Rapier | WebGL 3D 互动小猫（物理引擎） |
| 后端框架 | FastAPI | 异步高性能 Python Web 框架 |
| 文档转换 | pdf2docx · python-docx · PyPDF2 · weasyprint · markdown · ebooklib · striprtf | 8 种文档格式互转 |
| 音频转换 | pydub + ffmpeg | 9 种音频格式互转 |
| 视频转换 | ffmpeg (subprocess) | 7 种视频格式互转 |
| 图片转换 | Pillow + cairosvg + svglib | 8 种图片格式互转（含 SVG） |
| 数据转换 | PyYAML · xmltodict · tomli · stdlib | 5 种数据格式互转 |
| 部署 | Docker + Docker Compose | 一键编排，全依赖内置 |

---

## 许可

MIT License © [zhcnhan](https://github.com/zhcnhan)

第三方依赖许可证详见 [resources/licenses/THIRD_PARTY.md](resources/licenses/THIRD_PARTY.md)
