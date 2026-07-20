# 🚀 Batch Background Remover — 部署指南

本文档提供多种部署方式，从最简单到最专业，按需选择。

---

## 目录

- [方式一：Docker Compose（推荐）](#方式一docker-compose推荐)
- [方式二：手动部署（Python + Node）](#方式二手动部署python--node)
- [方式三：Nginx 反向代理 + HTTPS](#方式三nginx-反向代理--https)
- [方式四：systemd 系统服务](#方式四systemd-系统服务)
- [环境变量](#环境变量)
- [数据持久化](#数据持久化)
- [更新部署](#更新部署)
- [故障排查](#故障排查)

---

## 方式一：Docker Compose（推荐）

最简单、最完整、一条命令搞定。适合大多数服务器。

### 前置要求

- Docker 20+ 和 Docker Compose v2

### 步骤

```bash
# 1. 克隆仓库（或上传项目文件）
git clone https://github.com/zhcnhan/toolbox.git && cd toolbox/apps/batch_bg_remover

# 2. 构建并启动
docker compose up -d --build

# 3. 查看日志
docker compose logs -f

# 4. 验证
curl http://localhost:8001/api/health
# 返回 {"status":"ok","service":"batch-bg-remover"} 即成功
```

### 访问

- **Web 界面**：`http://your-server-ip:8001`
- **API 文档**：`http://your-server-ip:8001/docs`

### 自定义端口

```bash
# 方法1: 环境变量
PORT=9000 docker compose up -d

# 方法2: 修改 docker-compose.yml
ports:
  - "9000:8001"
```

### 停止 / 重启

```bash
docker compose down        # 停止
docker compose restart     # 重启
docker compose up -d --build  # 更新代码后重新构建
```

---

## 方式二：手动部署（Python + Node）

适合无法使用 Docker 的环境。

### 前置要求

- Python 3.10+
- Node.js 20+（仅构建前端时需要）
- 服务器内存 ≥ 2GB（rembg 模型需要）

### 步骤

```bash
# 1. 上传项目文件到服务器
scp -r batch_bg_remover user@server:/opt/

# 2. 安装后端依赖
cd /opt/batch_bg_remover/backend
python -m venv venv
source venv/bin/activate    # Linux
# venv\Scripts\activate     # Windows
pip install -r requirements.txt

# 3. 构建前端
cd /opt/batch_bg_remover/frontend
npm install
npm run build
# 构建产物自动输出到 backend/static/

# 4. 启动服务
cd /opt/batch_bg_remover/backend
python main.py
# 或用启动脚本
cd /opt/batch_bg_remover
python run.py
```

### 后台运行

```bash
# 简单方式：nohup
nohup python run.py > /var/log/bg-remover.log 2>&1 &

# 或用 screen/tmux
screen -S bg-remover
python run.py
# Ctrl+A D 分离
```

### 访问

- **Web 界面**：`http://your-server-ip:8001`

---

## 方式三：Nginx 反向代理 + HTTPS

在方式一或方式二的基础上，用 Nginx 提供域名访问和 HTTPS。

### 步骤

```bash
# 1. 安装 Nginx
sudo apt install nginx

# 2. 复制配置
sudo cp nginx.conf /etc/nginx/sites-available/batch-bg-remover

# 3. 编辑配置，修改 server_name
sudo nano /etc/nginx/sites-available/batch-bg-remover
# 将 your-domain.com 改为你的域名

# 4. 启用站点
sudo ln -s /etc/nginx/sites-available/batch-bg-remover /etc/nginx/sites-enabled/

# 5. 测试配置
sudo nginx -t

# 6. 申请 HTTPS 证书
sudo certbot --nginx -d your-domain.com

# 7. 重载 Nginx
sudo systemctl reload nginx
```

### 访问

- **Web 界面**：`https://your-domain.com`

---

## 方式四：systemd 系统服务

让服务开机自启、崩溃自动重启。配合方式二使用。

### 步骤

```bash
# 1. 复制 service 文件
sudo cp batch-bg-remover.service /etc/systemd/system/

# 2. 编辑文件，修改路径和用户
sudo nano /etc/systemd/system/batch-bg-remover.service
# 修改 WorkingDirectory、ExecStart、ReadWritePaths 为你的实际路径

# 3. 重载 systemd
sudo systemctl daemon-reload

# 4. 启用开机自启
sudo systemctl enable batch-bg-remover

# 5. 启动
sudo systemctl start batch-bg-remover

# 6. 查看状态
sudo systemctl status batch-bg-remover

# 7. 查看日志
sudo journalctl -u batch-bg-remover -f
```

### 常用命令

```bash
sudo systemctl start batch-bg-remover     # 启动
sudo systemctl stop batch-bg-remover      # 停止
sudo systemctl restart batch-bg-remover   # 重启
sudo journalctl -u batch-bg-remover -f    # 实时日志
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8001` | 服务监听端口 |
| `PYTHONUNBUFFERED` | `1` | Python 输出不缓冲（日志实时显示） |

设置方式：

```bash
# Docker
PORT=9000 docker compose up -d

# 手动
export PORT=9000
python run.py

# systemd
# 在 .service 文件中添加 Environment=PORT=9000
```

---

## 数据持久化

### Docker 模式

`docker-compose.yml` 已配置数据卷：

| 容器路径 | 宿主路径 | 说明 |
|----------|----------|------|
| `/app/uploads` | `./data/uploads` | 上传的原始图片 |
| `/app/outputs` | `./data/outputs` | 抠图结果 |
| `/root/.u2net` | `./data/.u2net` | rembg 模型缓存（避免重复下载） |

### 手动模式

上传和输出文件在 `backend/uploads/` 和 `backend/outputs/`。建议定期清理：

```bash
# 清理 7 天前的上传文件
find /opt/batch_bg_remover/backend/uploads -mtime +7 -delete
find /opt/batch_bg_remover/backend/outputs -mtime +7 -delete
```

---

## 更新部署

### Docker

```bash
cd /opt/batch_bg_remover
git pull
docker compose up -d --build
```

### 手动

```bash
cd /opt/batch_bg_remover
git pull

# 重新构建前端（如果前端有更新）
cd frontend && npm install && npm run build

# 重新安装依赖（如果 requirements.txt 有更新）
cd ../backend && pip install -r requirements.txt

# 重启服务
sudo systemctl restart batch-bg-remover
# 或
docker compose restart
```

---

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
lsof -i :8001

# 查看详细日志
docker compose logs -f
# 或
journalctl -u batch-bg-remover -f
```

### rembg 抠图失败

```bash
# 检查 onnxruntime 是否安装
python -c "import onnxruntime; print(onnxruntime.__version__)"

# 如果未安装
pip install onnxruntime

# 检查模型是否已下载
ls ~/.u2net/
# 应该有 u2net.onnx 文件（约 176MB）
```

### 云端引擎报错

- **Gemini 429**：免费额度用完，等待刷新或开启付费
- **remove.bg 429**：50 张/月额度用完
- **擦个图 402**：余额不足，需充值
- **自定义引擎 404**：模型名错误，检查拼写

### 前端白屏

```bash
# 检查前端是否已构建
ls backend/static/
# 应该有 index.html 和 assets/ 目录

# 重新构建
cd frontend && npm run build
```

### 内存不足

rembg + onnxruntime 需要约 1GB 内存。如果服务器内存 < 2GB：

```bash
# 添加 swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 部署检查清单

部署完成后，逐项确认：

- [ ] `curl http://localhost:8001/api/health` 返回 `{"status":"ok"}`
- [ ] `curl http://localhost:8001/api/engines` 返回引擎列表
- [ ] 浏览器访问 `http://your-server-ip:8001` 显示界面
- [ ] 上传图片后能预览
- [ ] 选 rembg 本地引擎能成功抠图
- [ ] 云端引擎填写 API Key 后能调用
- [ ] 抠图结果能下载
- [ ] 打包下载 ZIP 正常
