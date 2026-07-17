<p align="center">
  <h1 align="center">🔄 Format Converter</h1>
  <p align="center">
    <b>万能格式转换 Web 服务</b><br/>
    <sub>前后端分离 · 37 输入格式 · 5 大类别 · 批量处理 · 一键部署 · →DOC 支持</sub>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/vite-5-646CFF?logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/three.js-0.170-000000?logo=three.js&logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 简介

Format Converter 是一个**前后端分离**的 Web 格式转换服务，支持文档、图片、音频、视频、数据等多种格式之间的快速互转。采用现代化技术栈，可直接部署至服务器供团队使用。

### 核心特性

- **40+ 格式支持** — 涵盖文档（PDF/Word/Markdown/EPUB）、图片（JPG/PNG/WebP/GIF）、音频（MP3/WAV/FLAC）、视频（MP4/MKV/WEBM）、数据（JSON/YAML/CSV/XML/TOML）
- **批量处理** — 一次上传多个文件，顺序转换，实时进度反馈
- **实时进度** — 转换进度条实时更新（含视频转换的逐帧进度），上传阶段也有动画反馈
- **格式互斥** — 源格式与目标格式自动互斥禁用，防止重复选择
- **全局日志监控** — 左下角可折叠的实时日志面板，监测所有 API 请求和后端转换输出
- **3D 互动猫咪** — 全屏可拖拽的 3D 猫咪模型，支持点击敲打、拖拽甩飞、弹簧物理回归，伴有神圣背光和"林参"卫星文字环绕
- **一键部署** — Docker Compose 一条命令上线
- **Auto API Docs** — FastAPI 自动生成 Swagger / ReDoc 文档

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
│   Three.js      │    │   ├── document (PDF⇄DOCX)│
│   Framer Motion │    │   ├── image   (Pillow)  │
└─────────────────┘    │   ├── audio   (pydub)   │
                       │   ├── video   (ffmpeg)  │
                       │   └── data    (5种)     │
                       └─────────────────────────┘
```

---

## 支持的格式

| 类别 | 输入格式 | 输出格式 | 引擎 |
|------|----------|----------|------|
| 📄 **文档** | PDF, DOCX, DOC, TXT, MD, HTML, RTF, EPUB | PDF, DOCX, **DOC**, TXT, MD, HTML, RTF, EPUB | pdf2docx · python-docx · PyPDF2 · weasyprint · LibreOffice† |
| 🖼️ **图片** | JPG, PNG, WEBP, BMP, GIF, ICO, TIFF, SVG | JPG, PNG, WEBP, BMP, GIF, ICO, TIFF | Pillow · cairosvg |
| 🎵 **音频** | MP3, WAV, FLAC, OGG, AAC, WMA, M4A, Opus, AIFF | MP3, WAV, FLAC, OGG, AAC, M4A, Opus, AIFF | pydub + ffmpeg |
| 🎬 **视频** | MP4, AVI, MKV, MOV, WEBM, FLV, WMV | MP4, AVI, MKV, MOV, WEBM, FLV, WMV | ffmpeg-python |
| 📊 **数据** | JSON, YAML, CSV, XML, TOML | JSON, YAML, CSV, XML, TOML | PyYAML · xmltodict · tomli |

> † **→DOC 路径** 需要 LibreOffice。Docker 镜像已内置，本地开发需自行安装。

---

## 快速开始

### 一键开发（Windows）

```bash
# 双击运行 dev.bat，或命令行执行：
dev.bat
```

脚本会自动启动后端（端口 8000）和前端（端口 5173），并打开浏览器。

### 一键开发（Linux / macOS）

```bash
chmod +x dev.sh
./dev.sh
```

### 手动启动

```bash
# 1. 克隆仓库
git clone <repo-url> && cd toolbox/apps/format_converter

# 2. 启动后端
cd backend
pip install -r requirements.txt
uvicorn format_converter.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 新终端，启动前端
cd ../frontend
npm install
npm run dev

# 4. 浏览器访问 http://localhost:5173
```

### Docker 部署（推荐生产环境）

```bash
cd apps/format_converter

# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 访问 http://localhost:8000
```

### 生产部署

详见 [DEPLOY.md](./DEPLOY.md)

---

## 环境要求

- Python 3.10+
- Node.js 20+（仅开发时需要）
- FFmpeg（音频/视频转换必要）
- LibreOffice（→DOC 路径必要，建议本地开发时安装）

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
| `POST` | `/api/upload` | 上传文件（分块写入，500MB 限制） |
| `POST` | `/api/convert` | 启动批量转换 |
| `GET` | `/api/task/{id}` | 查询任务进度（含实时进度） |
| `DELETE` | `/api/task/{id}` | 取消任务 |
| `GET` | `/api/download/{id}/{filename}` | 下载单个结果 |
| `GET` | `/api/download-zip/{id}` | 打包下载全部结果 |

---

## 项目结构

```
apps/format_converter/
├── backend/                        # FastAPI 后端
│   ├── format_converter/
│   │   ├── main.py                 #   FastAPI 入口 + 路由 + 任务管理
│   │   ├── converters/             #   转换引擎
│   │   │   ├── __init__.py         #     注册表 + 调度 + 进度回调
│   │   │   ├── document_converter.py #   PDF/Word/MD/EPUB
│   │   │   ├── image_converter.py  #     图片 (Pillow)
│   │   │   ├── audio_converter.py  #     音频 (pydub)
│   │   │   ├── video_converter.py  #     视频 (ffmpeg)
│   │   │   └── data/               #     数据格式 (5个)
│   │   └── utils/                  #   格式映射 + 文件工具
│   └── requirements.txt
├── frontend/                       # React 前端
│   ├── src/
│   │   ├── App.jsx                 #   主应用 + 状态管理
│   │   ├── api/index.js            #   API 客户端（含日志拦截）
│   │   ├── logStore.js             #   全局日志存储（pub/sub）
│   │   ├── components/
│   │   │   ├── Navbar.jsx          #     顶部导航
│   │   │   ├── TabNav.jsx          #     类别标签
│   │   │   ├── FormatSelector.jsx  #     格式选择（含互斥逻辑）
│   │   │   ├── DropZone.jsx        #     拖放上传
│   │   │   ├── FileList.jsx        #     文件列表
│   │   │   ├── ProgressPanel.jsx   #     转换进度面板
│   │   │   ├── LogPanel.jsx        #     转换日志面板
│   │   │   ├── DownloadPanel.jsx   #     下载面板（无弹窗下载）
│   │   │   ├── GlobalLogPanel.jsx  #     全局日志监控（可折叠）
│   │   │   └── InteractivePet.jsx  #     3D 互动猫咪
│   │   └── index.css               #    Tailwind + 自定义样式
│   ├── public/
│   │   └── cat_model.glb           #    3D 猫咪模型
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                      # Docker 构建
├── docker-compose.yml              # Docker Compose
├── nginx.conf                      # Nginx 配置（可选）
├── dev.bat                         # Windows 一键开发脚本
├── dev.sh                          # Linux/macOS 一键开发脚本
├── DEPLOY.md                       # 部署教程
└── README.md                       # 本文件
```

---

## 3D 互动猫咪

页面右下角有一只 3D 猫咪，基于自定义 GLB 模型渲染，具有以下交互：

- **点击** — 棒子敲打动画，猫咪做出疼痛/生气反应
- **拖拽** — 抓住猫咪甩飞，全屏物理弹射后弹簧回归原位
- **神圣背光** — 猫咪身后有金色光晕，呼吸式脉动
- **"林参"卫星** — 两个发光文字绕猫咪椭圆轨道旋转，随物理移动
- **自动任务清理** — 后端自动清理超过 1 小时的已完成任务及其临时文件

### 替换 3D 模型

将 `.glb` 文件放到 `frontend/public/cat_model.glb`，模型会自动通过迭代质心算法居中并缩放到合适大小。

---

## 常见问题

<details>
<summary><b>音频/视频转换报错</b></summary>
需要安装 FFmpeg：
<ul>
  <li>Windows: <code>winget install ffmpeg</code></li>
  <li>macOS: <code>brew install ffmpeg</code></li>
  <li>Linux: <code>sudo apt install ffmpeg</code></li>
</ul>
</details>

<details>
<summary><b>DOCX → PDF 效果不理想</b></summary>
默认使用 python-docx + reportlab 进行基本转换。要获得最佳效果，请安装 LibreOffice：
<br/>Linux: <code>sudo apt install libreoffice</code>
</details>

<details>
<summary><b>开发时后端端口是多少</b></summary>
后端默认运行在 <code>8000</code> 端口。Vite 开发服务器的 API 代理指向 <code>127.0.0.1:8000</code>。生产环境中 Docker 也使用 <code>8000</code> 端口。
</details>

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | React 18 + Vite 5 | 现代化 SPA |
| UI 样式 | Tailwind CSS 3 | 工具类优先，深色主题 |
| 动效 | Framer Motion 11 | 声明式动画 |
| 3D 渲染 | Three.js + React Three Fiber | WebGL 3D 猫咪 |
| 后端框架 | FastAPI | 异步高性能 Python Web 框架 |
| 部署 | Docker + Docker Compose | 一键编排 |
| 反向代理 | Nginx（可选） | 生产环境静态文件 + API 代理 |

---

## 许可

MIT License © [zhcnhan](https://github.com/zhcnhan)
