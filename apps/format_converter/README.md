<p align="center">
  <h1 align="center">🔄 Format Converter</h1>
  <p align="center">
    <b>万能格式转换 Web 服务</b><br/>
    <sub>前后端分离 · 40+ 格式 · 6 大类别 · 批量处理 · 一键部署</sub>
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
- **批量处理** — 一次上传多个文件，并行转换
- **实时进度** — WebSocket 实时推送转换进度
- **3D 互动人偶** — 页面右下角可点击互动的 3D 角色，支持皮肤切换
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
| 📄 **文档** | PDF, DOCX, DOC, TXT, MD, HTML, RTF, EPUB | PDF, DOCX, TXT, MD, HTML | pdf2docx · python-docx · PyPDF2 · weasyprint |
| 🖼️ **图片** | JPG, PNG, WEBP, BMP, GIF, ICO, TIFF, SVG | JPG, PNG, WEBP, BMP, GIF, ICO, TIFF | Pillow |
| 🎵 **音频** | MP3, WAV, FLAC, OGG, AAC, WMA, M4A, Opus, AIFF | MP3, WAV, FLAC, OGG, AAC, M4A, Opus | pydub + ffmpeg |
| 🎬 **视频** | MP4, AVI, MKV, MOV, WEBM, FLV, WMV | MP4, AVI, MKV, MOV, WEBM | ffmpeg-python |
| 📊 **数据** | JSON, YAML, CSV, XML, TOML | JSON, YAML, CSV, XML, TOML | PyYAML · xmltodict · tomli |

### 文档转换路径

| 源格式 → 目标格式 | 方法 |
|-------------------|------|
| PDF → DOCX | pdf2docx |
| PDF → TXT | PyPDF2 文本提取 |
| PDF → 图片 | PyPDF2 + Pillow 渲染 |
| DOCX → PDF | python-docx + reportlab / LibreOffice |
| DOCX → TXT | python-docx 段落提取 |
| DOCX → HTML | python-docx 结构转换 |
| MD → PDF | weasyprint |
| MD → HTML | markdown |
| HTML → PDF | weasyprint |
| EPUB → TXT | ebooklib + BeautifulSoup |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+（仅开发时需要）
- FFmpeg（音频/视频转换需要）
- LibreOffice（可选，用于 DOC→DOCX、更好的 DOCX→PDF）

### 本地开发

```bash
# 1. 克隆仓库
git clone <repo-url> && cd toolbox/apps/format_converter

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 启动后端（开发模式，端口 8000）
uvicorn format_converter.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 新终端，安装前端依赖
cd ../frontend
npm install

# 5. 启动前端开发服务器（端口 5173，自动代理 API 到 8000）
npm run dev

# 6. 浏览器访问 http://localhost:5173
```

### Docker 部署（推荐）

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
│   │   │   └── Character3D.jsx     #     3D 人偶
│   │   └── index.css               #    Tailwind + 自定义样式
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                      # Docker 构建
├── docker-compose.yml              # Docker Compose
├── nginx.conf                      # Nginx 配置（可选）
├── DEPLOY.md                       # 部署教程
└── README.md                       # 本文件
```

---

## 3D 人偶自定义

页面右下角的 3D 小人偶支持皮肤切换。内置 6 套皮肤：**赛博蓝、霓虹粉、森林绿、日落橙、幽灵白、璀璨金**。

### 添加自定义皮肤

编辑 `frontend/src/components/Character3D.jsx`，在 `SKIN_REGISTRY` 中添加：

```js
'my-skin': {
  id: 'my-skin',
  name: '我的皮肤',
  head: '#ff6b6b',     // 头部颜色
  body: '#ee5a24',     // 身体颜色
  limbs: '#d63031',    // 四肢颜色
  eyes: '#ffffff',     // 眼睛颜色
  accent: '#fab1a0',   // 装饰色
  emissive: '#ff6b6b', // 发光色
},
```

重新构建前端即可生效（`npm run build`）。

自定义 3D 模型：将 `CharacterModel` 组件中的几何体替换为 `useGLTF` 加载的自定义 `.glb` 模型。

---

## 常见问题

<details>
<summary><b>音频/视频转换报错</b></summary>
需要安装 FFmpeg：
<ul>
  <li>Windows: <code>winget install ffmpeg</code> 或从 <a href="https://ffmpeg.org">ffmpeg.org</a> 下载</li>
  <li>macOS: <code>brew install ffmpeg</code></li>
  <li>Linux: <code>sudo apt install ffmpeg</code></li>
</ul>
</details>

<details>
<summary><b>DOCX → PDF 效果不理想</b></summary>
默认使用 python-docx + reportlab 进行基本转换（文本为主）。要获得最佳效果，请安装 LibreOffice：
<br/>
<br/>Linux: <code>sudo apt install libreoffice</code>
<br/>Docker 镜像中如需 LibreOffice，需在 Dockerfile 中添加安装命令。
</details>

<details>
<summary><b>大文件转换超时怎么办</b></summary>
视频、音频等大文件的转换时间取决于文件大小和服务器性能。Docker 部署时可调整 COMPOSE_HTTP_TIMEOUT 或增加 Nginx 的 proxy_read_timeout。
</details>

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | React 18 + Vite 5 | 现代化 SPA |
| UI 样式 | Tailwind CSS 3 | 工具类优先，深色主题 |
| 动效 | Framer Motion 11 | 声明式动画 |
| 3D 渲染 | Three.js + React Three Fiber | WebGL 3D 人偶 |
| 后端框架 | FastAPI | 异步高性能 Python Web 框架 |
| 部署 | Docker + Docker Compose | 一键编排 |
| 反向代理 | Nginx（可选） | 生产环境静态文件 + API 代理 |

---

## 许可

MIT License © [zhcnhan](https://github.com/zhcnhan)
