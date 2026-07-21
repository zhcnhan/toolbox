# Toolbox 技术备忘录

> 写在前面：此文档记录 toolbox 项目的全部技术细节、架构设计、已知陷阱和工作流程。
> **目的**：方便后续 AI 换模型后能快速上手，避免踩同样的坑。
> **使用规则**：每次运行前必须查阅本文档了解上下文，每次运行结束后必须根据本次操作补充/修改/重构本文档。

---

## 〇、核心工作规范

### 0.1 文档维护铁律

1. **每次开始工作前**：先阅读 `TECHNICAL_MEMO.md`，了解当前项目状态和已知陷阱
2. **每次工作结束后**：更新本文档，补充新的发现、修复记录、配置变更
3. **禁止在文档中写入明文密钥/密码**：所有 API Key、Token、密码用 `<REDACTED>` 代替
4. **文档要跟上代码**：改了引擎逻辑、加/删功能、改了部署方式 → 立刻同步更新文档

---

## 一、项目概览

| 项目 | 版本 | 路径 | 说明 |
|------|------|------|------|
| root | 1.2.0 | `d:/developments/toolbox` | GitHub: [zhcnhan/toolbox](https://github.com/zhcnhan/toolbox), Gitee: [gengzisama/toolbox](https://gitee.com/gengzisama/toolbox) |
| batch_bg_remover | — | `apps/batch_bg_remover/` | 批量抠图 Web 服务，端口 8001 |
| format_converter | — | `apps/format_converter/` | 万能格式转换 Web 服务，端口 8000 |
| cli-tools | — | `cli-tools/` | 命令行工具（含 `git-mirror`） |

### 技术栈

- **后端**：Python 3.9+ / FastAPI / uvicorn
- **前端**：React / Vite / Tailwind
- **部署**：Docker / Docker Compose / nginx / systemd
- **云服务**：硅基流动、remove.bg、擦个图、Google Gemini

---

## 二、batch_bg_remover 详解

### 2.1 引擎架构

所有引擎继承自 `BaseEngine`，通过装饰器 `@register_engine("id")` 注册，`engine_registry.py` 自动发现 `engines/` 目录下匹配 `*_engine.py` / `*_local.py` / `*_cloud.py` 的文件。

**8 个引擎一览：**

| ID | 名称 | 类型 | 自动抠图 | 提示词分割 | 需要 Key | 价格 |
|----|------|------|:-------:|:---------:|:--------:|------|
| `rembg_local` | rembg | 本地 | ✅ | ❌ | 否 | 免费 |
| `sam_local` | SAM 1 ViT-L | 本地 | ❌ (需Qwen3-VL定位，每次花钱) | ✅ | 硅基流动 API Key | 按量计费 |
| `icon_bg` | 图标抠图 | 本地 | ✅ | ❌ | 否 | 免费 |
| `kimi` | Kimi (多边形坐标) | 云端 | ❌ | ✅ | 硅基流动 API Key | 按量计费 |
| `gemini_mask` | Gemini Mask | 云端 | ❌ | ✅ | Google API Key | Free Tier |
| `removebg` | remove.bg | 云端 | ✅ | ❌ | remove.bg API Key | 50张/月免费 |
| `cagetu` | 擦个图 | 云端 | ✅ | ❌ | API Key | 0.1元/次 |
| `custom` | 自定义 | 云端 | ✅ | ✅ | 用户自填 | 取决于服务商 |

### 2.1.5 macOS 部署注意事项 ⚠️

**位置**：`apps/batch_bg_remover/make-mac-app.sh`（生成 `.command` 启动器）

| 问题 | 现象 | 原因 | 修复 |
|------|------|------|------|
| `.command` 双击不等待输入 | SAM 下载询问跳过，不等 Y/N | macOS Finder 双击 `.command` 时 stdin 未挂载，`read -p` 无效 | 改用 `osascript` macOS 原生弹窗 |
| SAM 弹窗不出来 | 弹窗完全不显示 | 旧模型文件 `~/.cache/sam/sam_vit_l_0b3195.pth` 还在，`if [ ! -f "$SAM_PATH" ]` 为假跳过整个块 | 改为先检测 Python 包是否 importable，再检查模型文件 |
| `onnxruntime-silicon` 装完 rembg 报错"缺少后端" | rembg 无法使用 | 先 `uninstall onnxruntime` 再装 `onnxruntime-silicon`，安装失败后 onnxruntime 也没了 | 不卸直接装，装不上也不影响 |
| `segment-anything` 提示"未安装"但明明装过 | SAM 不可用 | **缺 `torchvision`**。`pip install segment-anything` 只拉 `torch` 不拉 `torchvision`，`segment_anything.predictor` 内部 import `torchvision.transforms` 炸了 | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` 一起装 |
| pip 静默安装后无反馈 | 装了没装不知道 | `-q` 标志 + `2>&1 \| tail -1` 截掉了 pip 原生进度条 | 去掉 `-q` 和 `tail`，pip 自带进度条（显示 MB/s + ETA） |
| `&&`/`||` 链式判断吞错误 | torch 装完 segment-anything 失败看不到 | `cmd1 && cmd2 && cmd3 \|\| echo fail` 中任何命令 exit code 意外就中断 | 改为 `if/else` 每步独立判断 |
| Finder 显示 toolbox 文件夹 | 桌面有两个东西嫌乱 | 无 | 加 `chflags hidden` 自动隐藏 |
| torch 太大安装慢 | 干等没反馈 | pip 输出被截 | pip 默认进度条自带网速和倒计时 |

**Apple Silicon 加速**：
- M1/M2/M3/M4 可装 `onnxruntime-silicon` 替代 `onnxruntime`，推理速度翻倍
- 清华镜像可能没有 `onnxruntime-silicon`，脚本先试官方源再试镜像再兜底
- `torch` + `torchvision` 从 PyTorch 官方源装（`--index-url https://download.pytorch.org/whl/cpu`）

### 2.2 SAM 1 ViT-L 引擎

**实现位置**：`apps/batch_bg_remover/backend/engines/sam_local_engine.py`

**管线**：
```
用户图片 + 提示词 → Qwen3-VL-32B (硅基流动) Box 定位 → SAM 1 ViT-L (本地) 分割 → 透明 PNG
```

**模型管理（关键改进！）**：
- 模型文件：`sam_vit_l_0b3195.pth`（1.25GB）
- 默认下载路径：`~/.cache/sam/sam_vit_l_0b3195.pth`
- **后端 API**（`main.py` 中）：
  - `GET /api/engine/sam_local/status` — 检查模型是否存在 + 下载任务状态
  - `POST /api/engine/sam_local/download` — 触发后台下载
  - `GET /api/engine/sam_local/download/progress` — 获取实时进度
- **自动下载**：引擎首次调用时若模型不存在，前端弹出下载对话框
- **镜像轮询**（`_download_sam_model_background`）：ghproxy.net → gh-proxy.com → mirror.ghproxy.com → github.moeyy.xyz → 直连
- **校验**：下载完成后检查文件大小 ≥ 1GB，否则重试下一个镜像

**GPU 加速**：代码中无硬编码 `device='cpu'`，`segment-anything` 自动利用 CUDA（NVIDIA）、MPS（Apple Silicon）或 CPU（AMD/集成显卡）进行推理。Docker 镜像为 CPU 版本（`python:3.12-slim`），服务器无 GPU 时自动 CPU 推理。

**SAM 分割策略**：
1. 单 mask 模式 + box + 角点 negative 提示 → 快速出结果
2. 可疑结果（大框 + 低分/框内前景少）→ 多候选兜底
3. 最佳 mask 主要在框外 → 翻转
4. 去除面积 < 1% 的孤立碎片

**预设提示词**（自动抠图用 `_PRESET_PROMPTS` 中的 key）：
- 默认"画面中的主体"
- 针对 `icon_bg` 等场景有专用预设

#### API 配置

| 项目 | 值 |
|------|-----|
| VL 模型 | `Qwen/Qwen3-VL-32B-Instruct` |
| 端点 | `https://api.siliconflow.cn/v1/chat/completions` |
| 超时 | 300s（5分钟），自动重试 3 次 |
| 温度 | 0.1 |
| max_tokens | 512 |

#### 预处理优化

- `_resize_for_api`：API 图片自动缩放到 800px 以内
- `_box_to_pixels`：普通框外扩 12%，超大框内缩防全选
- `_keep_large_components`：scipy 连通域过滤，去除微小碎片

### 2.3 Kimi 引擎（重点！）

**实现位置**：`apps/batch_bg_remover/backend/engines/kimi_engine.py`

**调用链路**：
```
前端 slider(num_points:15-500) → main.py/n_pts clamp(15-500) → remove_bg_with_prompt()
  → _get_polygon(): 固定 API 请求 50 点（自动重试 3 次） → matting_cut(): 预处理 + 插值 + 掩膜
```

**API 配置**：
- **模型**：`Pro/moonshotai/Kimi-K2.6`（通过硅基流动 API）
- **端点**：`https://api.siliconflow.cn/v1/chat/completions`
- **max_tokens**：2048（够了，不要无限）
- **response_format**：**不设置**（之前加了但 Kimi-K2.6 偶发因此返回空 content，改为手动 JSON 提取）
- **enable_thinking**：`False`（超关键！关了才快，否则 CoT 思考几十秒）
- **固定 API 点数**：50（不多不少，多了超时、少了不够插值）
- **timeout**：120s
- **重试机制**：自动重试 3 次（Kimi-K2.6 偶发返回空 content 或无效 JSON，重试通常能解决）

**JSON 提取逻辑**（`_extract_json`）：
- 兼容纯 JSON、markdown 包裹、前后多余文字
- 用花括号深度计数找到最外层 `{}`
- 同时兜底检查 `reasoning_content` 字段（Kimi 有时放这里）

#### 🌟 踩坑历史（必须记住）

| # | 问题 | 原因 | 修复 |
|---|------|------|------|
| 1 | API 请求超时（120s） | Kimi-K2.6 默认开启 Chain-of-Thought 思考模式，每次先推演几十秒 | 加 `enable_thinking: False` |
| 2 | 高点数（70+）超时 | 让 API 直接输出 70+ 个坐标点太多 | 固定 50 点，后端插值到任意精度 |
| 3 | Kimi 返回 "未找到有效 JSON" | 模型可能返回 reasoning_content 而非 content | 已修复 |
| 4 | RGBA 图片上传崩溃 | PNG 透明通道 → 存 JPEG 报错 | 加 `img.convert("RGB")` |
| 5 | 前端滑块最大 100 不够 | 插值后希望更精细 | 改到 500 |
| 6 | 提示词效果差 | 原版提示词太弱，轮廓不在物体边缘 | 通用优化提示词：强调边缘贴合、薄片/凹陷/尖角 |
| 7 | Kimi 间歇性返回无效 JSON | Kimi-K2.6 偶发波动：空 content、无效 JSON | 添加 3 次自动重试 + `_extract_json()` 花括号深度解析 + 兜底 `reasoning_content` |

#### 提示词优化要点

所有 polygon/mask 类引擎的提示词都按照以下原则统一优化：
1. **像素级边缘贴合**：每个点必须坐在物体和背景的分界线上
2. **关注薄片延伸**：翅膀、尾巴、喙、耳朵、手指、发丝、树叶——这些最容易漏
3. **关注凹陷区域**：肢体之间、关节周围——多边形要跟着凹进去
4. **不要光滑尖锐角**：模型倾向把锐角磨平，要明确禁止
5. **曲率高的地方多布点**：头、尖端、角落多放点，长直边少放

**涉及的引擎文件**：
- `kimi_engine.py` — `_POLYGON_PROMPT`
- `gemini_mask_engine.py` — `_POLYGON_PROMPT` 和 `_MASK_PROMPT`
- `custom_engine.py` — `remove_bg` 和 `remove_bg_with_prompt` 中的 prompt

### 2.4 速率限制器

**位置**：`apps/batch_bg_remover/backend/rate_limiter.py`

**算法**：
- 按 API Key 独立追踪（SHA256 哈希，仅存前 12 字符）
- 自适应 RPM：初始 5 → 每次成功 +1 → 遇 429 -5（最低 2，最高 30）
- 滑动窗口 1 分钟
- RPD（每日计数）跨日自动重置
- 线程安全（threading.Lock）

**重要原则**：代码中不硬编码额度上限，永远不说"额度用尽"。

### 2.5 代理管理

**位置**：`apps/batch_bg_remover/backend/proxy.py`
**存储**：`backend/data/proxy.json`（Docker volume 持久化）

支持配置：enabled、url、auth_type(none/basic)、username、password

### 2.6 API 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/proxy` | 获取代理配置 |
| PUT | `/api/proxy` | 更新代理配置 |
| POST | `/api/proxy/test` | 测试代理连通性 |
| GET | `/api/engines` | 列出所有引擎 |
| POST | `/api/engine/gemini/usage` | Gemini Key 今日用量 |
| GET | `/api/engine/sam_local/status` | SAM 模型缓存状态 + 下载进度 |
| POST | `/api/engine/sam_local/download` | 触发 SAM 模型下载 |
| GET | `/api/engine/sam_local/download/progress` | SAM 下载实时进度 |
| POST | `/api/upload` | 上传图片 |
| POST | `/api/remove-bg` | 自动抠图 |
| POST | `/api/remove-bg-prompt` | 提示词抠图 |
| GET | `/api/original/{file_id}` | 获取上传的原图预览 |
| GET | `/api/download/{result_id}` | 下载单张 |
| GET | `/api/download-zip` | 批量打包下载 |

---

## 三、format_converter 简介

万能格式转换 Web 服务。支持文档/图片/音频/视频/数据格式互转。

**部署**：Docker Compose 运行，端口 8000，systemd 服务（非 Docker 方式）

---

## 四、部署流程（必须严格遵守！）

### 4.1 部署三步走

```
# Step 1: 本地推送到 GitHub（所有分支）
git push origin main
git push origin friend  # 如果有 friend 分支

# Step 2: GitHub → Gitee 自动同步（所有分支 + 标签）
python -m git_mirror.cli sync toolbox
# 或：cd cli-tools/git-mirror && python -m git_mirror sync toolbox

# Step 3: SSH 到服务器拉取
ssh root@server 'cd /opt/toolbox && git pull'
```

#### git-mirror 已知陷阱

| 问题 | 说明 |
|------|------|
| `push --mirror` 被 Gitee 拒绝 | bare repo 里的 remote tracking refs（`github/main`）也会被推送，Gitee 拒绝更新 hidden ref。**已修复**：改 `push --all + --tags` |
| 凭据认证失败 | bare repo 没有 cached credential，首次推送需要交互式输入。已在 `_push_all` 中增加凭据管理 |
| `pip install -e .` 后 `git-mirror` 命令找不到 | Windows PowerShell 下 entry point 可能不在 PATH，可用 `python -m git_mirror.cli` 代替 |

### 4.2 硬性禁止

- ❌ 禁止 `git push gitee`（绕过 mirror 同步）
- ❌ 禁止在服务器上执行 `git reset --hard` 或任何破坏性操作
- ❌ 禁止修改服务器的 git remote（origin 就是 Gitee，不可改动）

### 4.3 服务器环境

| 项目 | 值 |
|------|-----|
| 路径 | `/opt/toolbox` |
| 外网 | ❌ **无法访问外网**（只能访问 Gitee/码云） |
| 服务器 IP | `<REDACTED>` |
| SSH 端口 | `43521` |
| SSH 用户 | `root` |
| SSH 命令 | `ssh root@<SERVER_IP> -p 43521` |
| format_converter | systemd 服务，端口 8000，非 Docker |
| batch_bg_remover | Docker Compose，端口 8001 |
| git remote origin | Gitee（不是 GitHub） |

### 4.4 代理穿透（服务器访问外网）

服务器无法直连外网 API（硅基流动、remove.bg 等），需要通过本机（Windows 开发机）的代理做 SSH 反向隧道。

#### 建立代理隧道（本机执行）

前提：本机已开启 Clash/代理客户端。

**Clash 端口分配（本机）：**

| 用途 | 端口 |
|------|------|
| HTTP 代理 | `7899` |
| 混合端口 | `7897` |
| SOCKS5 | （其他） |

SSH 反向隧道**只能用 HTTP 端口 7899**（混合端口 7897 不支持隧道转发）：

```bash
# 隧道用 HTTP 端口 7899
ssh -R 7899:localhost:7899 root@<SERVER_IP> -p 43521
```

执行后需要保持 SSH 窗口不关闭。

**原理**：服务器访问 `localhost:7899` → SSH 隧道 → 本机 `localhost:7899`（Clash HTTP 代理）

#### 在程序设置页配置

隧道建立后，在抠图应用的「代理设置」中填写：

```
http://host.docker.internal:7899
```

因为 `docker-compose.yml` 已配置 `extra_hosts: host.docker.internal:host-gateway`，
Docker 容器内的 `host.docker.internal` 会解析到服务器的 localhost。

#### 网络故障排查

```
# 服务器上验证代理：可用 7899（HTTP 端口）或 7897（混合端口，两者都支持 HTTP）
curl -x http://localhost:7899 https://api.siliconflow.cn/v1/chat/completions

# 检查 SSH 隧道是否还在
ss -tlnp | grep 7899
```

> ⚠️ SSH 隧道断开后需要重新执行 `ssh -R` 命令。代理断了 → Kimi/Gemini 等云端引擎全部不可用。

### 4.4 本地开发启动

```bash
cd apps/batch_bg_remover
$env:PYTHONIOENCODING='utf-8'  # Windows 必须，否则 emoji 报错

# 后端
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
# 或 python run.py --dev

# 前端
cd frontend && npx vite --host 0.0.0.0 --port 5174
```

---

## 五、Windows 本地开发注意事项

### 5.1 Python 编码

Windows 默认 console 编码是 GBK。包含 emoji/unicode 字符的 Python 输出会炸。

**务必**：`$env:PYTHONIOENCODING='utf-8'` 放在所有 python 命令前。

如果装的是 Python 3.14（太新），某些包（如 `tokenizers`）可能需要编译，编译工具链不全就装不上。建议用 Python 3.12。

### 5.2 macOS 开发注意事项

| 注意点 | 说明 |
|--------|------|
| Python 版本 | macOS 自带 Python 通常是 2.x 或 3.9，脚本会自动下载安装 3.12 |
| 路径格式 | 全部使用 `pathlib.Path`，跨平台兼容。**没有** Windows 特有的 `C:\` 硬编码 |
| 子进程 | 全部使用 `sys.executable`（当前 Python 解释器路径），没有 Windows-only 的 `cmd.exe` 调用 |
| 编码 | 全部 `utf-8`，无 `gbk/cp936` 依赖 |
| 多进程 | macOS 默认事件循环 `SelectorEventLoop` 兼容，代码中无 `ProactorEventLoop` 依赖 |
| 字体 | 仅在 `tests/` 调试脚本中有 Windows 字体路径（`C:/Windows/Fonts/`），生产代码无此问题 |
| SAM 模型路径 | `~/.cache/sam/sam_vit_l_0b3195.pth`（跨平台） |
| rembg 模型路径 | `~/.u2net/u2net.onnx`（跨平台） |
| 启动器 | `.command` 文件 + `open http://localhost:8001`（macOS 特有） |
| Apple Silicon | `onnxruntime-silicon` 可用；torch 需从 `--index-url https://download.pytorch.org/whl/cpu` 装；**必须同时装 torchvision** |

### 5.3 照片融合/差异分析（附注）

本会话中完成了一套照片像素级差异分析 + 光流变形 + 人脸特征点 Delaunay 变形的工作流：

**差异分析**：
- 三张图（原片/身材好/脸好）逐像素 RGB 差异、LAB 色彩空间对比、SSIM 结构相似性
- 鬼影检测（梯度差 + 色差双阈值）、Laplacian 鬼影、频域高频能量比
- 分区域（脸/身体/腿部/背景）差异统计

**融合技术**（从原片无损恢复修图版效果）：
- Farneback 前后向光流 + 一致性检查 + 多尺度细化
- InsightFace 106 特征点检测 → Delaunay 三角网格 → 仿射变形
- **全部在 LAB L* 通道处理，a*/b* 完全不动**，避免修图导致色偏
- 亮度补偿使用双边滤波边缘保持 + 椭圆面部掩码
- 最终输出 656KB 无损 PNG，PSNR 42.3dB，SSIM 0.9815

### 5.2 API Key 管理

当前所有 API Key 由用户通过前端 Settings 面板填写，代码中**不硬编码任何密钥**。
测试脚本通过环境变量或命令行参数传入 Key，切勿明文写在脚本文件或本文档中。

### 5.3 模型信息（硅基流动）

| 项目 | 值 |
|------|-----|
| 平台 | [https://cloud.siliconflow.cn](https://cloud.siliconflow.cn) |
| 文档 | [https://api-docs.siliconflow.cn/docs/api/chat-completions-post](https://api-docs.siliconflow.cn/docs/api/chat-completions-post) |
| Kimi 模型 | `Pro/moonshotai/Kimi-K2.6` |
| 注册地址 | [https://cloud.siliconflow.cn](https://cloud.siliconflow.cn) |

### 5.4 测试命令速查

```bash
# 健康检查
curl http://127.0.0.1:8001/api/health

# 上传图片
curl -X POST -F "files=@test_bird_kimi_debug.png" http://127.0.0.1:8001/api/upload

# Kimi 抠图
curl -X POST -d "file_id=xxx&engine_id=kimi&prompt=the bird&api_key=sk-xxx&num_points=100" http://127.0.0.1:8001/api/remove-bg-prompt
```

---

## 六、类似平台（备选 API 提供商）

| 平台 | 地址 | 特点 |
|------|------|------|
| 硅基流动 | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) | 目前使用中，Kimi-K2.6 效果最好 |
| OpenRouter | [openrouter.ai](https://openrouter.ai) | 国际平台，模型最全，支持图片+JSON |
| 阿里百炼 | [bailian.aliyun.com](https://bailian.aliyun.com) | Qwen2.5-VL 视觉能力强 |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | 价格极低，仅自家模型 |
| Google Gemini | [aistudio.google.com](https://aistudio.google.com) | Gemini Mask 引擎已在用 |

---

## 七、git 工作流速查

```bash
# 查看状态
git status

# 查看最近提交
git log --oneline -5

# 查看某次提交包含的文件
git log --oneline -1 --name-only

# 推送（仅限 GitHub，Gitee 走 mirror）
git push origin main

# mirror 同步
cd cli-tools/git-mirror && python -m git_mirror sync toolbox
```

---

## 八、历史重要修复记录

| 日期 | 修复 | 涉及文件 |
|------|------|---------|
| 2026-07 | Kimi 超时修复：添加 `enable_thinking: False` | `kimi_engine.py` |
| 2026-07 | Kimi 高点数超时：固定 50 点 API，Catmull-Rom 插值 | `kimi_engine.py` |
| 2026-07 | RGBA→JPEG 崩溃修复：`convert("RGB")` | `kimi_engine.py` |
| 2026-07 | Kinect滑块 100→500 | `SettingsPanel.jsx`, `main.py`, `App.jsx` |
| 2026-07 | 提示词通用优化：所有 polygon/mask 引擎 | `kimi_engine.py`, `gemini_mask_engine.py`, `custom_engine.py` |
| 2026-07 | 提取公共掩膜处理到 `matting.py`，Gemini Mask 支持 `num_points` | `matting.py`, `gemini_mask_engine.py`, `kimi_engine.py`, `main.py` |
| 2026-07 | macOS 部署修复：启动器改为生产模式单进程、添加国内镜像源、补充安全弹窗说明 | `make-mac-app.sh`, `batch-bg-mac.sh`, `MAC.md` |
| 2026-07 | Kimi 间歇性无效 JSON：添加 3 次自动重试 + 花括号深度解析 + reasoning_content 兜底 | `kimi_engine.py` |
| 2026-07 | 移除 Replicate 和 CLIPSeg 引擎（体积大/云端依赖/不常用），清理全部文档和部署配置 | 12 个文件 |
| 2026-07 | SAM 引擎添加自动下载：后台线程 + 5 镜像轮询 + 1GB 校验 + Web 进度对话框 | `sam_local_engine.py`, `main.py`, `App.jsx`, `api.js` |
| 2026-07 | SAM 模型下载集成到部署：Dockerfile build arg、deploy.sh 交互选择、make-mac-app.sh 首次安装 | `Dockerfile`, `deploy.sh`, `make-mac-app.sh` |
| 2026-07 | SAM 模型不存在时 `FileNotFoundError` → `RuntimeError`（500→400 前端友好）；下载失败对话框不关闭+重试按钮 | `sam_local_engine.py`, `App.jsx` |
| 2026-07 | 上传后直接显示原图预览（`GET /api/original/{file_id}`），替代「等待处理」文字占位 | `main.py`, `ImageGrid.jsx`, `App.jsx` |
| 2026-07 | **git-mirror 推送被 Gitee 拒绝**：`push --mirror` 会把 bare repo 里的 remote tracking refs（`github/main`、`gitee/main`）一并推送，Gitee 拒绝更新 hidden ref。改为 `push --all + --tags`，只推真实分支和标签 | `sync.py` |
| 2026-07 | **SAM 类型注解导致导入崩溃**：`def _get_predictor() -> SamPredictor` 在导入时求值，而 `SamPredictor` 的 import 在 `try/except` 内，若 segment-anything 未安装则 `NameError`。改为 `-> "SamPredictor"`（字符串 forward reference）| `sam_local_engine.py` |
| 2026-07 | **main.py 硬 import SAM 引擎**：`from engines.sam_local_engine import get_sam_status, trigger_sam_download` 在模块顶层，SAM 一炸整个程序起不来。改为 `try/except` + 条件注册路由 | `main.py` |
| 2026-07 | **make-mac-app.sh `.command` 双击 read 不生效**：macOS Finder 双击 `.command` 文件时 stdin 未挂载，`read -p` 不等输入直接跳过。改为 `osascript` macOS 原生弹窗 | `make-mac-app.sh` |
| 2026-07 | **onnxruntime-silicon 安装失败导致丢包**：旧逻辑先 `pip uninstall onnxruntime` 再装 `onnxruntime-silicon`，装失败后 onnxruntime 也没了。改为不预卸，装不上也不影响现有包 | `make-mac-app.sh` |
| 2026-07 | **pip -q 静默吞掉 segment-anything 报错**：`pip install -r requirements.txt -q` 在 tsinghua 镜像上 torch 下载失败，-q 吞了所有输出，用户不知道装没装上。改为显式分段安装 + 去掉 `-q` + pip 原生进度条 | `make-mac-app.sh` |
| 2026-07 | **`&&`/`||` 链式判断脆弱**：`pip install torch && pip install segment-anything && echo ✅ || echo ⚠` 中任何命令返回非预期 exit code 都会导致链断。改为 `if/else` 每步独立判断 | `make-mac-app.sh` |
| 2026-07 | **`segment-anything` 缺 `torchvision` 依赖**：`pip install segment-anything` 只拉 `torch` 不拉 `torchvision`，但 `segment_anything.predictor` 内部 import `torchvision.transforms`，导入时 `ImportError` 被 catch 但用户看到的是"未安装"。改为 `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` 一起装 | `make-mac-app.sh`, `sam_local_engine.py` |
