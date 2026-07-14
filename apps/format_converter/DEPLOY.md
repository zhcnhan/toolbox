# Format Converter 部署教程

本教程详细介绍如何将 Format Converter 部署到服务器上。

---

## 目录

- [环境要求](#环境要求)
- [方式一：Docker 部署（推荐）](#方式一docker-部署推荐)
- [方式二：手动部署](#方式二手动部署)
- [方式三：Nginx 反向代理](#方式三nginx-反向代理)
- [云平台部署](#云平台部署)
- [HTTPS 配置](#https-配置)
- [性能优化](#性能优化)
- [监控与运维](#监控与运维)
- [故障排查](#故障排查)

---

## 环境要求

### 最低配置

| 项目 | 要求 |
|------|------|
| CPU | 2 核 |
| 内存 | 2 GB |
| 磁盘 | 10 GB（不含上传文件的存储） |
| 操作系统 | Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+) / macOS / Windows |
| Docker | 20.10+（Docker 部署时需要） |
| Docker Compose | v2.0+（Docker 部署时需要） |

### 推荐配置

| 项目 | 要求 |
|------|------|
| CPU | 4 核+ |
| 内存 | 4 GB+ |
| 磁盘 | 50 GB+ SSD |

> 视频批量转换对 CPU 要求较高，建议核心数越多越好。

---

## 方式一：Docker 部署（推荐）

这是最简单快捷的部署方式，所有依赖（包括 FFmpeg）已打包在镜像中。

### 1. 安装 Docker

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 安装 Docker Compose v2
sudo apt install docker-compose-plugin
```

退出重新登录以使用户组生效。

### 2. 克隆项目

```bash
git clone https://github.com/zhcnhan/toolbox.git
cd toolbox/apps/format_converter
```

### 3. 启动服务

```bash
# 构建镜像并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 检查状态
docker compose ps
```

### 4. 访问服务

```
http://<服务器IP>:8000
```

### 5. 常用运维命令

```bash
# 停止服务
docker compose down

# 重新构建（代码更新后）
docker compose build --no-cache
docker compose up -d

# 查看资源占用
docker stats format-converter

# 进入容器排查
docker exec -it format-converter bash

# 清理上传临时文件
docker exec format-converter rm -rf /tmp/format_converter_uploads/*
```

### 6. 环境变量

可在 `docker-compose.yml` 中配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PYTHONUNBUFFERED` | `1` | Python 不缓冲输出 |
| `FORMAT_CONVERTER_ENV` | `production` | 运行环境 |

---

## 方式二：手动部署

适用于不想使用 Docker 的场景。

### 1. 安装系统依赖

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip \
    ffmpeg nodejs npm

# CentOS / RHEL
sudo dnf install -y python3.12 python3.12-pip \
    ffmpeg nodejs npm

# macOS
brew install python@3.12 ffmpeg node
```

### 2. 构建前端

```bash
cd apps/format_converter/frontend
npm install
npm run build
# 输出在 frontend/dist/
```

### 3. 安装后端依赖

```bash
cd apps/format_converter/backend
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 启动服务

```bash
# 开发模式
uvicorn format_converter.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式（推荐使用 gunicorn）
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    format_converter.main:app
```

### 5. 使用 systemd 管理（Linux）

创建服务文件 `/etc/systemd/system/format-converter.service`：

```ini
[Unit]
Description=Format Converter API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/format-converter/backend
Environment="PATH=/opt/format-converter/backend/venv/bin:/usr/bin"
ExecStart=/opt/format-converter/backend/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    --access-logfile /var/log/format-converter/access.log \
    --error-logfile /var/log/format-converter/error.log \
    format_converter.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo mkdir -p /var/log/format-converter
sudo systemctl daemon-reload
sudo systemctl enable --now format-converter
sudo systemctl status format-converter
```

---

## 方式三：Nginx 反向代理

生产环境推荐在前端加一层 Nginx，用于：
- 托管前端静态文件
- 反向代理 API 请求
- 负载均衡
- SSL 终止

### Nginx 配置

```nginx
# /etc/nginx/sites-available/format-converter

upstream format_converter_backend {
    server 127.0.0.1:8000;
    # 多实例时可添加更多 server
    # server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name converter.example.com;

    client_max_body_size 500M;
    client_body_timeout 300s;

    # 前端静态文件
    root /opt/format-converter/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://format_converter_backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_buffering off;
    }

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
    gzip_min_length 1000;
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/format-converter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 云平台部署

### Railway / Render / Fly.io

1. 确保项目根目录有 `Dockerfile`
2. 设置启动命令：`uvicorn format_converter.main:app --host 0.0.0.0 --port $PORT`
3. 环境变量中设置 `PORT=8000`
4. 部署后会自动构建 Docker 镜像

### 阿里云 ECS / 腾讯云 CVM

推荐使用 Docker Compose 方式：

```bash
# 1. 安装 Docker + Compose（见上方教程）
# 2. 上传项目到服务器
scp -r apps/format_converter user@server:/opt/

# 3. SSH 到服务器
ssh user@server
cd /opt/format_converter
docker compose up -d

# 4. 配置安全组，放行 8000 端口
```

### Vercel（仅前端）+ 独立后端

前端可以单独部署到 Vercel（静态站点），后端部署到任意 VPS：

```bash
# 前端部署到 Vercel
cd frontend
npx vercel --prod

# 设置环境变量 VITE_API_BASE_URL 指向后端 API 地址
```

> 注意：前端 Vite 开发代理仅在开发环境生效。部署到 Vercel 后需修改 `src/api/index.js` 中的 `BASE` 为后端完整地址。

### 腾讯云 CloudBase / EdgeOne Pages

1. **前端**：部署到 EdgeOne Pages（静态站点托管）
2. **后端**：部署到 CloudBase 云托管（容器服务）

---

## HTTPS 配置

### 使用 Certbot（Let's Encrypt）

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 自动配置 HTTPS
sudo certbot --nginx -d converter.example.com

# 自动续期
sudo certbot renew --dry-run
```

Nginx 配置中需要先配置好 `server_name` 指向你的域名。

### 自签名证书（内网使用）

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/converter.key \
    -out /etc/nginx/ssl/converter.crt
```

然后修改 Nginx 配置的 `listen 443 ssl;` 并添加证书路径。

---

## 性能优化

### 1. 增加 Worker 数量

```bash
gunicorn -w $(nproc) -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 format_converter.main:app
```

### 2. 使用多实例 + 负载均衡

在 Nginx upstream 中配置多个后端实例：

```nginx
upstream format_converter_backend {
    least_conn;
    server 127.0.0.1:8000 weight=3;
    server 127.0.0.1:8001 weight=3;
    server 127.0.0.1:8002 weight=2;
}
```

### 3. 调整上传限制

```bash
# Docker Compose
environment:
  - MAX_UPLOAD_SIZE=1073741824  # 1GB
```

### 4. 定期清理临时文件

添加定时任务：

```bash
# crontab -e
0 3 * * * find /tmp/format_converter_* -mtime +1 -delete
```

### 5. 使用 CDN 加速前端

前端静态文件可以上传到 CDN（阿里云 OSS、腾讯云 COS 等），配合 Nginx 的 `try_files` 回源。

---

## 监控与运维

### 健康检查

```bash
curl http://localhost:8000/api/health
# 返回: {"status":"ok","version":"2.0.0"}
```

### 日志

```bash
# Docker
docker compose logs -f --tail=100

# systemd
sudo journalctl -u format-converter -f
```

### Prometheus + Grafana（可选）

FastAPI 可集成 `prometheus_fastapi_instrumentator` 暴露指标：

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

---

## 故障排查

### 端口被占用

```bash
# 查看占用 8000 端口的进程
sudo lsof -i :8000
# 或
sudo ss -tlnp | grep 8000

# 杀掉进程
sudo kill -9 <PID>
```

### Docker 容器无法启动

```bash
docker compose logs format-converter
# 常见问题：
# - 端口冲突 → 修改 docker-compose.yml 中的端口映射
# - 磁盘空间不足 → docker system prune -a
```

### 文件上传失败

```bash
# 检查上传目录权限
docker exec format-converter ls -la /tmp/format_converter_uploads

# 检查 Nginx client_max_body_size
# 默认 500M，大文件需增大此值
```

### 视频转换失败

```bash
# 确认 FFmpeg 已安装
docker exec format-converter ffmpeg -version
# 或
ffmpeg -version

# 测试转码
ffmpeg -i test.mp4 -c:v libx264 test_output.mp4
```

### 内存不足

视频转换会消耗大量内存。如果服务器内存有限：
1. 减少并发 worker 数量
2. 限制视频文件大小
3. 使用更高效的编码参数

---

## 总结

部署方式对比：

| 方式 | 难度 | 适用场景 |
|------|------|----------|
| Docker Compose | ⭐ 简单 | 个人/小团队，快速上线 |
| 手动 + systemd | ⭐⭐ 中等 | 需要精细控制的传统部署 |
| Nginx 反向代理 | ⭐⭐⭐ 较复杂 | 生产环境，需要域名/HTTPS |
| 云平台 | ⭐⭐ 中等 | 不想管服务器的场景 |

推荐新手从 **Docker Compose** 开始，有域名再叠加 **Nginx 反向代理 + HTTPS**。
