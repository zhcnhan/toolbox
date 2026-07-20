# apps — 应用程序

Web 应用集合。每个子目录是一个**完整的独立项目**，自有前端、后端、部署配置和文档，不依赖仓库中其他模块。

## 应用列表

| 应用 | 端口 | 说明 | 部署方式 |
|------|:----:|------|---------|
| [format_converter](./format_converter/) | 8000 | 万能格式转换 — 文档/图片/音频/视频/数据互转 | systemd / Docker |
| [batch_bg_remover](./batch_bg_remover/) | 8001 | 批量抠图 — 8 引擎（本地 rembg/SAM + 云端），自动抠图+提示词修正 | Docker Compose |

## 端口分配

| 端口 | 应用 | 说明 |
|:----:|------|------|
| 8000 | format_converter | 格式转换 |
| 8001 | batch_bg_remover | 批量抠图 |
| 5174 | batch_bg_remover (dev) | 前端 Vite 开发服务器 |
| 7897 | Clash 混合端口 | 代理（HTTP + SOCKS） |
| 7899 | Clash HTTP 端口 | 代理（仅 HTTP，用于 SSH 隧道） |

## 项目结构约定

```
apps/<app_name>/
├── backend/          # 后端代码（Python/FastAPI）
│   ├── main.py       # 应用入口
│   ├── requirements.txt
│   └── ...
├── frontend/         # 前端代码（React/Vite）
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── Dockerfile        # Docker 构建
├── docker-compose.yml
├── deploy.sh         # 一键部署脚本
├── README.md         # 应用文档
└── DEPLOY.md         # 部署指南
```
