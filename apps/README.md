# apps — 应用程序

Web 应用或桌面应用集合。每个子目录是一个完整的独立项目，自带前端、后端、部署配置和文档。

## 应用列表

| 应用 | 说明 |
|------|------|
| [format-converter](./format_converter/) | 万能格式转换 Web 服务 — 前后端分离，支持文档/图片/音频/视频/数据互转 |

## 约定

- 每个子目录是完整的独立项目
- `backend/` — 后端代码（Python/FastAPI）
- `frontend/` — 前端代码（React/Vite）
- 自带 `Dockerfile`、`docker-compose.yml` 或 `nginx.conf` 用于部署
- 不依赖仓库中的其他模块
