# Format Converter 完整部署教程

本教程涵盖从零到上线的全部部署方式：Docker 一键部署、OpenResty/Nginx 反向代理、Let's Encrypt HTTPS，以及云平台部署。

---

## 目录

- [快速决策：我该用哪种方式](#快速决策我该用哪种方式)
- [环境要求](#环境要求)
- [方式一：Docker Compose 一键部署（最简）](#方式一docker-compose-一键部署最简)
- [方式二：OpenResty + 手动部署（生产级）](#方式二openresty--手动部署生产级)
- [方式三：Nginx + 手动部署](#方式三nginx--手动部署)
- [HTTPS 配置](#https-配置)
- [云平台部署](#云平台部署)
- [后台服务管理](#后台服务管理)
- [性能优化](#性能优化)
- [监控与运维](#监控与运维)
- [故障排查](#故障排查)

---

## 快速决策：我该用哪种方式

```
┌─────────────────────────────────────────────────────┐
│                    你想怎么部署？                      │
└─────────────────────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
      5 分钟上线    有域名/HTTPS   已经有 OpenResty
            │            │            │
            ▼            ▼            ▼
      Docker        Nginx/        OpenResty
      Compose     OpenResty      + 手动
      (方式一)    + 手动         (方式二)
                  (方式二/三)
```

- **只想快速跑起来** → 方式一
- **有域名要配 HTTPS** → 方式二（OpenResty）或方式三（Nginx）
- **已经装了 OpenResty** → 方式二
- **服务器干净从零配** → 方式二或三都行，推荐方式二

---

## 环境要求

### 最低配置

| 项目 | 要求 |
|------|------|
| CPU | 2 核 |
| 内存 | 2 GB |
| 磁盘 | 10 GB（不含上传/输出文件） |
| 操作系统 | Linux (Ubuntu 20.04+ / Debian 11+ / CentOS 8+) |
| 外部依赖 | FFmpeg, LibreOffice (→DOC 路径必要) |

### 推荐配置

| 项目 | 要求 |
|------|------|
| CPU | 4 核+ |
| 内存 | 4 GB+ |
| 磁盘 | 50 GB+ SSD |

---

## 方式一：Docker Compose 一键部署（最简）

所有依赖（FFmpeg、LibreOffice）已打包在镜像中，无需手动安装任何系统软件。

### 1. 安装 Docker

```bash
# 官方一键脚本（Ubuntu / Debian）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 安装 Docker Compose v2
sudo apt update && sudo apt install docker-compose-plugin -y

# 退出重新登录
exit
```

### 2. 克隆项目

```bash
git clone https://github.com/zhcnhan/toolbox.git
cd toolbox/apps/format_converter
```

### 3. 启动

```bash
docker compose up -d
```

### 4. 访问

```
http://<服务器IP>:8000
```

### 5. 常用命令

```bash
# 查看日志
docker compose logs -f --tail=50

# 重启
docker compose restart

# 重新构建（代码更新后）
docker compose build --no-cache && docker compose up -d

# 停止
docker compose down

# 进入容器排查
docker exec -it format-converter bash

# 清理上传临时文件（7 天以上）
docker exec format-converter find /tmp/format_converter_uploads -mtime +7 -delete
```

### 6. 环境变量

在 `docker-compose.yml` 中可配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PYTHONUNBUFFERED` | `1` | Python 实时输出日志 |
| `FORMAT_CONVERTER_ENV` | `production` | 运行环境标识 |

---

## 方式二：OpenResty + 手动部署（生产级）

适合有域名、需要 HTTPS、或服务器已有 OpenResty 的场景。

### 架构总览

```
浏览器 (HTTPS)
    │
    ▼
OpenResty (:443)
    ├── /          → 前端静态文件 (React SPA)
    ├── /api/*     → FastAPI (:8000)
    └── SSL 终止 (Let's Encrypt)
                    │
                    ▼
              FastAPI (systemd 管理)
                    │
                    ├── FFmpeg
                    ├── LibreOffice
                    └── Python 3.12+
```

### 第一步：安装系统依赖

```bash
# Ubuntu 22.04+ / Debian 12
sudo apt update
sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    ffmpeg \
    libreoffice-writer \
    git curl wget

# 验证安装
python3.12 --version
ffmpeg -version | head -1
libreoffice --version | head -1
```

### 第二步：安装 OpenResty

```bash
# 导入 GPG 密钥和仓库（Ubuntu/Debian）
wget -qO - https://openresty.org/package/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/openresty.gpg

echo "deb [signed-by=/usr/share/keyrings/openresty.gpg] https://openresty.org/package/ubuntu $(lsb_release -sc) main" \
    | sudo tee /etc/apt/sources.list.d/openresty.list

sudo apt update
sudo apt install openresty -y

# 验证
openresty -v
```

### 第三步：部署后端

```bash
# 创建工作目录
sudo mkdir -p /opt/format-converter
sudo chown $USER:$USER /opt/format-converter

# 克隆项目
cd /opt
git clone https://github.com/zhcnhan/toolbox.git
cd toolbox/apps/format_converter
```

```bash
# 安装 Python 依赖
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 第四步：构建前端

```bash
cd /opt/toolbox/apps/format_converter/frontend
npm install
npm run build
# 产物在 frontend/dist/
```

### 第五步：配置 OpenResty

```bash
# 备份默认配置
sudo cp /usr/local/openresty/nginx/conf/nginx.conf \
        /usr/local/openresty/nginx/conf/nginx.conf.bak
```

编辑 `/usr/local/openresty/nginx/conf/nginx.conf`：

```nginx
worker_processes auto;
error_log /usr/local/openresty/nginx/logs/error.log warn;
pid /usr/local/openresty/nginx/logs/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout 65;
    gzip            on;
    gzip_types      text/plain text/css application/json
                    application/javascript text/xml application/xml
                    image/svg+xml;
    gzip_min_length 1000;

    # ============================================================
    # 格式转换服务
    # ============================================================
    server {
        listen 80;
        server_name converter.example.com;  # ← 改成你的域名

        client_max_body_size 500M;
        client_body_timeout 300s;

        # ---- 前端静态文件 ----
        root /opt/toolbox/apps/format_converter/frontend/dist;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        # ---- API 代理 ----
        location /api/ {
            proxy_pass http://127.0.0.1:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 60s;
            proxy_buffering off;          # 实时进度传输
            client_max_body_size 500M;    # 上传文件大小限制
        }
    }
}
```

### 第六步：配置 systemd 管理后端

```bash
sudo tee /etc/systemd/system/format-converter.service << 'EOF'
[Unit]
Description=Format Converter API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/toolbox/apps/format_converter/backend
Environment="PATH=/opt/toolbox/apps/format_converter/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/toolbox/apps/format_converter/backend/venv/bin/uvicorn \
    format_converter.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

```bash
# 创建日志目录
sudo mkdir -p /var/log/format-converter

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable format-converter
sudo systemctl start format-converter

# 检查状态
sudo systemctl status format-converter
curl http://127.0.0.1:8000/api/health
```

### 第七步：启动

```bash
# 启动 OpenResty
sudo systemctl start openresty
sudo systemctl enable openresty

# 验证
curl http://localhost/api/health
```

### 第八步：访问

```
http://<服务器IP或域名>
```

### 常用运维命令

```bash
# 查看后端日志
sudo journalctl -u format-converter -f

# 查看 OpenResty 日志
sudo tail -f /usr/local/openresty/nginx/logs/access.log

# 重启后端
sudo systemctl restart format-converter

# 重载 OpenResty（修改配置后）
sudo openresty -s reload

# 测试配置语法
sudo openresty -t
```

---

## 方式三：Nginx + 手动部署

与方式二完全相同，只需将 OpenResty 替换为 Nginx：

```bash
# 安装 Nginx（替代 OpenResty）
sudo apt install nginx -y

# 配置文件路径
sudo vim /etc/nginx/sites-available/format-converter

# 启用
sudo ln -s /etc/nginx/sites-available/format-converter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

后端部分（第三步到第六步）完全相同。

---

## HTTPS 配置

### 使用 Certbot + Let's Encrypt（免费）

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx -y

# 自动配置 HTTPS（确保域名已解析到服务器）
sudo certbot --nginx -d converter.example.com

# 测试自动续期
sudo certbot renew --dry-run
```

certbot 自动修改 Nginx/OpenResty 配置，添加 443 端口和证书路径。

### 手动配置 HTTPS（如已有证书）

```nginx
server {
    listen 443 ssl http2;
    server_name converter.example.com;

    ssl_certificate     /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # ... 其余配置同方式二
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name converter.example.com;
    return 301 https://$host$request_uri;
}
```

---

## 云平台部署

### 阿里云 ECS / 腾讯云 CVM

```bash
# 1. 购买 ECS（Ubuntu 22.04，2核4G 起步）
# 2. 安全组放行 80/443 端口
# 3. SSH 登录后按「方式二」部署
```

### Railway / Render

```bash
# 自动检测 Dockerfile，直接部署
# 设置启动命令: uvicorn format_converter.main:app --host 0.0.0.0 --port $PORT
```

---

## 后台服务管理

### 常用 systemd 命令

```bash
sudo systemctl start format-converter    # 启动
sudo systemctl stop format-converter     # 停止
sudo systemctl restart format-converter  # 重启
sudo systemctl status format-converter   # 状态
sudo journalctl -u format-converter -f   # 实时日志
sudo journalctl -u format-converter --since "1 hour ago"  # 近 1 小时日志
```

### 定时清理临时文件

```bash
# 编辑器打开 crontab
crontab -e

# 添加：每天凌晨 3 点清理 24 小时以上的临时文件
0 3 * * * find /tmp/format_converter_* -type f -mtime +1 -delete
```

---

## 性能优化

### 1. 调整 Worker 数量

`/etc/systemd/system/format-converter.service`：

```ini
ExecStart=... --workers $(nproc)   # 使用所有 CPU 核心
```

### 2. OpenResty 缓存静态文件

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### 3. 负载均衡多实例

```nginx
upstream backend_pool {
    least_conn;
    server 127.0.0.1:8000 weight=3;
    server 127.0.0.1:8001 weight=3;
}
```

配合第二个 systemd 服务绑定 8001 端口。

---

## 监控与运维

### 健康检查

```bash
curl http://localhost:8000/api/health
# {"status": "ok"}
```

### 磁盘空间

```bash
# 查看上传/输出目录占用
du -sh /tmp/format_converter_*

# Docker 方式
docker exec format-converter du -sh /tmp/format_converter_*
```

---

## 故障排查

| 现象 | 检查方法 |
|------|---------|
| 端口被占用 | `sudo ss -tlnp \| grep 8000` |
| 后端无法启动 | `sudo journalctl -u format-converter -n 50` |
| 502 Bad Gateway | 后端没启动，`sudo systemctl status format-converter` |
| 文件上传失败 | 检查 Nginx `client_max_body_size`；检查磁盘空间 |
| 视频转换失败 | `ffmpeg -version` 确认已安装 |
| DOC 相关路径失败 | `libreoffice --version` 确认已安装 |
| 磁盘爆满 | `du -sh /tmp/format_converter_*`，检查定时任务 |

---

## 总结

| 方式 | 时间 | 难度 | 适用场景 |
|------|------|------|----------|
| Docker Compose | 5 分钟 | ⭐ | 快速上线、个人/小团队 |
| OpenResty + 手动 | 20 分钟 | ⭐⭐ | 生产环境、有域名和 HTTPS |
| Nginx + 手动 | 20 分钟 | ⭐⭐ | 同上，轻量替代 OpenResty |

**推荐路线**：先用 Docker 快速跑通 → 需要 HTTPS 时切到方式二/三。
