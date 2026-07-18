# ✂️ Batch Background Remover — 批量抠图工具

**7 引擎 · 本地 + 云端 · 自动抠图 + 提示词修正 · 一键打包下载**

---

## 功能

- 🖥️ **本地抠图**：rembg (U2-Net)，CPU 即可运行，无需联网，无需 API Key
- ✂️ **提示词修正**：自动抠图不满意？输入文本提示词（如"左边的猫"）重新选取主体
- 🎚️ **灵敏度调节**：CLIPSeg 本地引擎支持拖动滑块调节抠图灵敏度
- ☁️ **7 个引擎可选**：rembg / CLIPSeg / Gemini / remove.bg / 擦个图 / Replicate / 自定义
- 🔌 **插件式架构**：新增引擎只需写一个 `*_engine.py` 文件，自动发现注册
- 📦 **批量处理**：一次拖入几十张图，逐张处理
- 💾 **一键打包**：所有结果打包 ZIP 下载
- 🔐 **隐私安全**：API Key 存前端 localStorage，不上传服务器；本地模式完全离线
- 🌐 **代理支持**：支持 HTTP 代理（含 Basic 认证），方便服务器走 VPN 访问云端 API
- 🎀 **可爱界面**：玻璃拟态深色主题，Framer Motion 动画

---

## 引擎一览

| 引擎 | 类型 | 自动抠图 | 提示词分割 | 需要 Key | 价格 |
|------|------|:-------:|:---------:|:--------:|------|
| **rembg** | 本地 | ✅ | ❌ | 否 | 免费 |
| **CLIPSeg** 🆕 | 本地 | ❌ | ✅ | 否 | 免费（可选装 torch） |
| **remove.bg** | 云端 | ✅ | ❌ | [获取](https://www.remove.bg/api) | 50张/月免费，$0.09/张 |
| **擦个图** | 云端 | ✅ | ❌ | [获取](https://cagetu.com) | 0.1元/次 |
| **Gemini** | 云端 | ✅ | ✅ | [获取](https://aistudio.google.com/apikey) | Free Tier 有免费额度 |
| **Replicate** | 云端 | ✅ | ✅ | [获取](https://replicate.com/account/api-tokens) | ~$0.001/秒 |
| **自定义** | 云端 | ✅ | ✅ | 用户自填 | 取决于服务商 |

> **重要**：自定义引擎支持 Gemini 风格、硅基流动风格、OpenAI 兼容风格三种 API 格式（自动识别）。但模型必须支持「图像分割/抠图」，文生图模型（如 FLUX、Stable Diffusion）不能用于抠图。

---

## 快速开始

### 本地开发

```bash
# 开发模式（前后端分离 + 热更新）
python run.py --dev

# 生产模式（单进程，前端已构建）
python run.py

# 仅构建前端
python run.py --build

# 自定义端口
python run.py --port 9000
```

### 服务器部署

#### 方式一：一键部署（推荐）

```bash
chmod +x deploy.sh && ./deploy.sh
```

交互式引导，自动检测环境、可选 CLIPSeg 引擎、可选国内镜像，选择会被记录到 `.env`，后续重建自动沿用。

#### 方式二：手动 Docker

```bash
docker compose build && docker compose up -d

# 如需启用 CLIPSeg 提示词分割引擎
docker compose build --build-arg INSTALL_CLIPSEG=true && docker compose up -d
```

详见 [DEPLOY.md](./DEPLOY.md)，支持 4 种部署方式：

1. **Docker Compose**（推荐）— `deploy.sh` 一键部署
2. **手动部署** — Python + Node 构建
3. **Nginx 反向代理** — 域名 + HTTPS
4. **systemd 系统服务** — 开机自启 + 崩溃重启

---

## 项目结构

```
batch_bg_remover/
├── backend/
│   ├── main.py                      # FastAPI 入口 + 路由 + 静态文件服务
│   ├── engine_base.py               # 引擎抽象基类
│   ├── engine_registry.py           # 引擎注册中心 + 自动发现
│   ├── requirements.txt
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── rembg_local_engine.py    # rembg 本地引擎
│   │   ├── clipseg_local_engine.py  # CLIPSeg 本地引擎
│   │   ├── gemini_engine.py         # Gemini 云端引擎
│   │   ├── removebg_engine.py       # remove.bg 云端引擎
│   │   ├── cagetu_engine.py         # 擦个图云端引擎
│   │   ├── replicate_engine.py      # Replicate 云端引擎
│   │   └── custom_engine.py         # 自定义引擎
│   ├── static/                      # 前端构建产物（自动生成）
│   ├── uploads/                     # 上传文件（自动创建）
│   └── outputs/                     # 结果输出（自动创建）
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # 主应用
│   │   ├── api.js                   # API 客户端
│   │   ├── index.css                # 全局样式
│   │   ├── main.jsx                 # 入口
│   │   └── components/
│   │       ├── SettingsPanel.jsx    # 引擎设置
│   │       ├── DropZone.jsx         # 拖放上传
│   │       ├── ImageGrid.jsx        # 结果网格
│   │       └── PromptPanel.jsx      # 提示词修正
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── deploy.sh                        # 一键部署脚本
├── Dockerfile                       # Docker 构建
├── docker-compose.yml               # Docker Compose 编排
├── nginx.conf                       # Nginx 反代配置
├── batch-bg-remover.service         # systemd 服务文件
├── DEPLOY.md                        # 部署指南
└── README.md
```

---

## 添加新引擎

1. 在 `backend/engines/` 下新建 `xxx_engine.py` 文件
2. 继承 `BaseEngine`，加上 `@register_engine("xxx")` 装饰器
3. 实现 `info()`、`remove_bg()`、`remove_bg_with_prompt()`
4. 重启后端 — 自动发现，零配置

```python
# engines/my_engine.py
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

@register_engine("my_engine")
class MyEngine(BaseEngine):
    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="my_engine",
            name="我的引擎",
            description="...",
            type="cloud",
            supports_auto=True,
            supports_prompt=False,
            needs_api_key=True,
            api_key_label="API Key",
            api_key_help_url="https://...",
            icon="my_engine",
        )

    async def remove_bg(self, image_bytes, api_key=None):
        # 实现抠图逻辑，返回 PNG bytes
        ...

    async def remove_bg_with_prompt(self, image_bytes, prompt, api_key=None):
        # 实现提示词分割，返回 PNG bytes
        ...
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/engines` | 列出所有可用引擎 |
| `POST` | `/api/upload` | 批量上传图片 |
| `POST` | `/api/remove-bg` | 自动抠图 |
| `POST` | `/api/remove-bg-prompt` | 提示词抠图（可选参数 `sensitivity` 调节灵敏度） |
| `GET` | `/api/proxy` | 获取代理配置 |
| `PUT` | `/api/proxy` | 更新代理配置（支持认证） |
| `GET` | `/api/download/{result_id}` | 下载单张结果 |
| `GET` | `/api/download-zip?result_ids=...` | 打包下载 |

API 文档：启动后访问 `http://localhost:8001/docs`（Swagger UI）

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + Python 3.10+ |
| 本地抠图 | rembg (U2-Net, ONNX Runtime) |
| 本地分割 | CLIPSeg (HuggingFace Transformers) |
| 云端 API | requests (Gemini / remove.bg / 擦个图 / Replicate) |
| 前端 | React 18 + Vite + Tailwind CSS + Framer Motion |
| 图片处理 | Pillow |
| 部署 | Docker / systemd / Nginx |

---

## License

MIT
