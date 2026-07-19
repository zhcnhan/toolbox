# Toolbox 技术备忘录

> 写在前面：此文档记录 toolbox 项目的全部技术细节、架构设计、已知陷阱和工作流程。
> **目的**：方便后续 AI 换模型后能快速上手，避免踩同样的坑。

---

## 一、项目概览

| 项目 | 版本 | 路径 | 说明 |
|------|------|------|------|
| root | 1.1.0 | `d:/developments/toolbox` | GitHub: [zhcnhan/toolbox](https://github.com/zhcnhan/toolbox), Gitee: [gengzisama/toolbox](https://gitee.com/gengzisama/toolbox) |
| batch_bg_remover | — | `apps/batch_bg_remover/` | 批量抠图 Web 服务，端口 8001 |
| format_converter | — | `apps/format_converter/` | 万能格式转换 Web 服务，端口 8000 |
| cli-tools | — | `cli-tools/` | 命令行工具（含 `git-mirror`） |

### 技术栈

- **后端**：Python 3.9+ / FastAPI / uvicorn
- **前端**：React / Vite / Tailwind
- **部署**：Docker / Docker Compose / nginx / systemd
- **云服务**：硅基流动、remove.bg、擦个图、Replicate、Google Gemini

---

## 二、batch_bg_remover 详解

### 2.1 引擎架构

所有引擎继承自 `BaseEngine`，通过装饰器 `@register_engine("id")` 注册，`engine_registry.py` 自动发现 `engines/` 目录下匹配 `*_engine.py` / `*_local.py` / `*_cloud.py` 的文件。

**7 个引擎一览：**

| ID | 名称 | 类型 | 自动抠图 | 提示词分割 | 需要 Key | 价格 |
|----|------|------|:-------:|:---------:|:--------:|------|
| `rembg_local` | rembg | 本地 | ✅ | ❌ | 否 | 免费 |
| `clipseg_local` | CLIPSeg | 本地 | ❌ | ✅ | 否 | 免费（需 ~1.5GB 模型） |
| `kimi` | Kimi (多边形坐标) | 云端 | ❌ | ✅ | 硅基流动 API Key | 按量计费 |
| `gemini_mask` | Gemini Mask | 云端 | ❌ | ✅ | Google API Key | Free Tier |
| `removebg` | remove.bg | 云端 | ✅ | ❌ | remove.bg API Key | 50张/月免费 |
| `cagetu` | 擦个图 | 云端 | ✅ | ❌ | API Key | 0.1元/次 |
| `replicate` | Replicate | 云端 | ✅ | ✅ | Replicate Token | ~$0.001/秒 |
| `custom` | 自定义 | 云端 | ✅ | ✅ | 用户自填 | 取决于服务商 |

### 2.2 Kimi 引擎（重点！）

**实现位置**：`apps/batch_bg_remover/backend/engines/kimi_engine.py`

**调用链路**：
```
前端 slider(num_points:15-500) → main.py/n_pts clamp(15-500) → remove_bg_with_prompt()
  → _get_polygon(): 固定 API 请求 50 点 → _catmull_rom_spline(): 插值到 num_points → _apply_mask(): 生成掩膜
```

**API 配置**：
- **模型**：`Pro/moonshotai/Kimi-K2.6`（通过硅基流动 API）
- **端点**：`https://api.siliconflow.cn/v1/chat/completions`
- **max_tokens**：4096（够了，不要无限）
- **response_format**：`{"type": "json_object"}`（强制纯 JSON 输出）
- **enable_thinking**：`False`（超关键！关了才快，否则 CoT 思考几十秒）
- **固定 API 点数**：50（不多不少，多了超时、少了不够插值）
- **timeout**：120s

#### 🌟 踩坑历史（必须记住）

| # | 问题 | 原因 | 修复 |
|---|------|------|------|
| 1 | API 请求超时（120s） | Kimi-K2.6 默认开启 Chain-of-Thought 思考模式，每次先推演几十秒 | 加 `enable_thinking: False` |
| 2 | 高点数（70+）超时 | 让 API 直接输出 70+ 个坐标点太多 | 固定 50 点，后端插值到任意精度 |
| 3 | Kimi 返回 "未找到有效 JSON" | 模型可能返回 reasoning_content 而非 content | 已修复 |
| 4 | RGBA 图片上传崩溃 | PNG 透明通道 → 存 JPEG 报错 | 加 `img.convert("RGB")` |
| 5 | 前端滑块最大 100 不够 | 插值后希望更精细 | 改到 500 |
| 6 | 提示词效果差 | 原版提示词太弱，轮廓不在物体边缘 | 通用优化提示词：强调边缘贴合、薄片/凹陷/尖角 |

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

### 2.3 CLIPSeg 引擎（本地）

**实现位置**：`apps/batch_bg_remover/backend/engines/clipseg_local_engine.py`

#### 🌟 踩坑历史

| # | 问题 | 原因 | 修复 |
|---|------|------|------|
| 1 | 安装依赖后自动生图报 `Could not import CLIPSegProcessor` | transformers 5.x 中 CLIPSegProcessor 的导入路径变了 | `try: from transformers import CLIPSegProcessor; except: from transformers.models.clipseg.processing_clipseg import CLIPSegProcessor` |
| 2 | 下载模型报 `snapshot_download() got an unexpected keyword argument 'callback'` | huggingface_hub 新版移除了 callback 参数 | 直接删除 callback 参数，进度简化为固定 50% |

**模型下载**：
- 模型 ID：`CIDAS/clipseg-rd64-refined`（~1.5GB）
- 下载通过 `main.py` 的 `/api/engine/clipseg_local/download` 路由触发
- 缓存检查：`/api/engine/clipseg_local/status`

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
| GET | `/api/engine/clipseg_local/status` | CLIPSeg 缓存状态 |
| POST | `/api/engine/clipseg_local/download` | 触发模型下载 |
| GET | `/api/engine/clipseg_local/download/progress` | 下载进度 |
| GET | `/api/engine/clipseg_local/deps-status` | 依赖状态 |
| POST | `/api/engine/clipseg_local/install-deps` | 安装依赖 |
| POST | `/api/upload` | 上传图片 |
| POST | `/api/remove-bg` | 自动抠图 |
| POST | `/api/remove-bg-prompt` | 提示词抠图 |
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
# Step 1: 本地推送到 GitHub
git push origin main

# Step 2: GitHub → Gitee 自动同步
cd cli-tools/git-mirror && python -m git_mirror sync toolbox

# Step 3: SSH 到服务器拉取
ssh root@server 'cd /opt/toolbox && git pull'
```

### 4.2 硬性禁止

- ❌ 禁止 `git push gitee`（绕过 mirror 同步）
- ❌ 禁止在服务器上执行 `git reset --hard` 或任何破坏性操作
- ❌ 禁止修改服务器的 git remote（origin 就是 Gitee，不可改动）

### 4.3 服务器环境

| 项目 | 值 |
|------|-----|
| 路径 | `/opt/toolbox` |
| 外网 | ❌ 无法访问外网（只能访问 Gitee/码云） |
| format_converter | systemd 服务，端口 8000，非 Docker |
| batch_bg_remover | Docker Compose，端口 8001 |
| git remote origin | Gitee（不是 GitHub） |

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

### 5.2 API Key 管理

**当前有效的 Key**（硅基流动）：
```
sk-lyrexrjbwcaifhcifadhzjkvnyfetiasdfjirlhsaidkucsw
```
测试脚本中千万不要硬编码 Key，用环境变量或命令行参数传入。

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
| 2026-07 | CLIPSeg 导入兼容 `transformers 5.x` | `clipseg_local_engine.py` |
| 2026-07 | CLIPSeg 下载 `callback` 参数移除 | `main.py` |
