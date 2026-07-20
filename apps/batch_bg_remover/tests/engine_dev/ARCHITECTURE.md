# 轻量定位 + 局部 SAM 2 抠图引擎 — 架构文档

## 一、整体设计

### 核心理念

传统云端抠图（Gemini、Kimi 等）是一次性把整张原图丢到 API，既慢又贵。  
本引擎采用 **"先定位、后分割"** 的两段式方案（模式 A）：

```text
原图 ──[Step 1: Box 定位]──> BBox ──[Step 2: SAM 2 Box Prompt]──> Mask ──[Step 3: 合成]──> 透明 PNG
       轻量视觉模型                 专业分割模型                本地合成
```

| 步骤 | 干什么 | 用到什么 | 成本 |
|------|--------|---------|------|
| Step 1 | 根据文字提示，定位目标 BBox | Qwen3-VL-32B（硅基流动） | ~¥0.003/次 |
| Step 2 | 全图 + BBox → SAM 2 精准分割 | SAM 2（Replicate） | ~$0.012/次 (≈¥0.09) |
| Step 3 | Mask 合成透明 PNG | 本地 Pillow | 免费 |

### 为什么选择模式 A（全图 + Box Prompt）？

SAM 2 原生支持 Box Prompt 模式：给它一张图 + 一个矩形框，它自动分割框内物体。  
这比"裁剪 → SAM 2 → 贴回"的模式更简单可靠：

1. **代码量少**：省去裁剪 + 坐标还原逻辑，直接利用 SAM 2 的 Box Prompt 能力
2. **精度更高**：Box Prompt 是 SAM 2 的强项，能精准排除框外干扰物
3. **处理简单**：Mask 返回即为原图分辨率，不需要缩放贴回

---

## 二、数据流与接口设计

### 2.1 坐标体系

```
┌─────────────────────────────────────┐
│  (0,0)                    (1000,0)  │
│    ┌─────────────────────┐         │
│    │     BBox            │         │
│    │  (x_min, y_min)     │         │
│    │          (x_max, y_max)        │
│    └─────────────────────┘         │
│  (0,1000)                (1000,1000)│
└─────────────────────────────────────┘
```

- 所有坐标 **归一化到 0-1000 范围**，与图片实际尺寸无关
- Qwen3-VL 返回格式：`<box>[[x_min, y_min, x_max, y_max]]</box>`
- 内部统一格式：`[ymin, xmin, ymax, xmax]`（兼容 Google Gemini 传统）

**坐标转换**：
```python
# 归一化 → 像素
x_px = int(x_norm / 1000 * img_width)
y_px = int(y_norm / 1000 * img_height)

# 像素 → 归一化
x_norm = int(x_px / img_width * 1000)
y_norm = int(y_px / img_height * 1000)
```

### 2.2 裁剪 Margin 策略

```
原图 BBox: [ymin, xmin, ymax, xmax]
外扩 12%:  margin = (ymax - ymin) * 0.12

裁剪区域:
  crop_ymin = max(0, ymin - margin)
  crop_xmin = max(0, xmin - margin)
  crop_ymax = min(img_h, ymax + margin)
  crop_xmax = min(img_w, xmax + margin)
```

- 外扩 10%-15% Margin 防止切断头发、尾巴等细长结构
- 裁剪坐标 clamp 到图片边界内

### 2.3 引擎注册

最终引擎将实现为标准的 `BaseEngine` 子类，通过 `@register_engine("bbox_sam2")` 装饰器注册：

| 属性 | 值 |
|------|-----|
| `id` | `bbox_sam2` |
| `type` | `cloud` |
| `supports_auto` | `true`（不传 prompt 时自动检出最大前景物体） |
| `supports_prompt` | `true` |
| `needs_api_key` | `true`（需要 SILICONFLOW_API_KEY） |

核心方法：
- `remove_bg(image_bytes, api_key)` — 自动抠图（不传 prompt）
- `remove_bg_with_prompt(image_bytes, prompt, api_key)` — 按文字提示定向抠图

---

## 三、Step 1 实现细节 — Box 定位

### 3.1 模型选择历程

| 尝试 | 结果 |
|------|------|
| Gemini 3.1-flash-lite | 国外 API，用户偏好国产 |
| Qwen2.5-VL-7B-Instruct | 模型名在硅基流动不存在 |
| **Qwen/Qwen3-VL-32B-Instruct** ✅ | 国产、便宜、定位精准 |

### 3.2 Prompt 工程踩坑

**第一版（JSON 格式）**：
```
返回格式：{"box_2d": [ymin, xmin, ymax, xmax], "label": "描述"}
```
❌ 问题：框偏到右上角天空，Qwen 对自定义 JSON 坐标顺序理解有偏差。

**第二版（Qwen 原生 `<box>` 格式）**：
```
返回格式：<box>[[x_min, y_min], [x_max, y_max]]</box>
```
❌ 问题：Qwen3-VL 实际返回的是扁平的 4 数格式 `<box>[[42, 420, 630, 860]]</box>`，而非 2×2 格式。

**第三版（最终版）** — 匹配 Qwen3-VL 原生格式：
```
返回格式：<box>[[x_min, y_min, x_max, y_max]]</box>
```
✅ **完美收敛**。使用 `<box>` 标签是 Qwen 的 grounding 训练格式，比 JSON 更可靠。

### 3.3 API 调用

```
POST https://api.siliconflow.cn/v1/chat/completions
Headers: Authorization: Bearer {SILICONFLOW_API_KEY}
Body: OpenAI Chat API 格式，multimodal content
```

关键参数：
- `temperature: 0.1` — 低温度保证定位稳定
- `max_tokens: 512` — 只需返回一个 box，足够
- `timeout: 120s` — 32B 模型偶尔响应较慢（实际平均 15-30s）

### 3.4 图片预处理

```python
_MAX_IMG_SIZE = 800  # 压缩到最长边 800px
```
- 避免大图超时，800px 对视觉定位足够
- 压缩后的 base64 传给 API，原始尺寸在本地用于坐标还原

---

## 四、测试脚本使用

### 4.1 单图测试

**文件**：`step1_box_detection.py`

```powershell
cd apps/batch_bg_remover
$env:SILICONFLOW_API_KEY="你的Key"
python tests/engine_dev/step1_box_detection.py
```

修改测试目标（脚本顶部）：
```python
IMAGE_PATH = Path(...) / "test_bird.jpg"
OBJECT_PROMPT = "左边那只鸟"
```

输出：`tests/engine_dev/debug_box.jpg`

### 4.2 批量测试

**文件**：`step1_batch.py`

```powershell
cd apps/batch_bg_remover
$env:SILICONFLOW_API_KEY="你的Key"
python tests/engine_dev/step1_batch.py
```

添加新测试用例：
```python
TEST_CASES = [
    (_BASE_DIR / "test_bird.jpg", "左边那只鸟", "bird_left"),
    # ↑ (图片路径, 提示词, 输出文件名后缀)
]
```

输出：`tests/engine_dev/debug_box_{suffix}.jpg`

### 4.3 输出解读

- **红色半透明框**：BBox 区域（含 40% 透明度蒙版）
- **左上角文字**：`提示词 | box: [ymin, xmin, ymax, xmax]`
- 归一化坐标范围 0-1000，与图片尺寸无关

---

## 五、Step 1 测试结果汇总

| # | 图片 | 提示词 | Box `[ymin, xmin, ymax, xmax]` | 结果 |
|---|------|--------|------|------|
| 1 | test_bird.jpg | 左边那只鸟 | `[420, 40, 860, 630]` | ✅ 只框红头鸟 |
| 2 | test_bird.jpg | 右边那只鸟 | `[611, 500, 850, 840]` | ✅ 只框黑头鸟 |
| 3 | test_bird.jpg | 两只鸟 | `[425, 42, 862, 842]` | ✅ 框住整体 |
| 4 | test_cat.jpg | 猫的绿色帽子 | `[0, 73, 830, 975]` | ✅ 框住猫头+帽子 |
| 5 | test_cat.jpg | 整只猫 | `[0, 68, 1000, 998]` | ✅ 猫占满画面 |
| 6 | test_person_pc.jpg | 人 | `[0, 240, 998, 1000]` | ✅ 右侧人物全身 |
| 7 | test_person_pc.jpg | 电脑 | `[145, 63, 795, 596]` | ✅ 左侧笔记本电脑 |

**结论**：7/7 条测试用例全部通过。Qwen3-VL-32B 在三类场景（动物、人物、物品）下均表现出稳定的视觉定位能力。

---

## 六、文件清单

```
tests/
├── test_bird.jpg          # 测试图片：两只鸟
├── test_cat.jpg           # 测试图片：戴绿帽的猫
├── test_person_pc.jpg     # 测试图片：人+电脑
└── engine_dev/
    ├── ARCHITECTURE.md            # ← 本文档
    ├── step1_box_detection.py     # Step 1 单图 Box 定位
    ├── step1_batch.py             # Step 1 批量 Box 定位
    ├── step2_sam_segment.py       # Step 2 完整管线（Box + SAM2 + 合成）
    ├── debug_box.jpg              # 单图测试结果
    ├── debug_box_bird_left.jpg
    ├── debug_box_bird_right.jpg
    ├── debug_box_bird_both.jpg
    ├── debug_box_cat_hat.jpg
    ├── debug_box_cat_body.jpg
    ├── debug_box_person.jpg
    ├── debug_box_pc.jpg
    └── step2_*.jpg / step2_*.png  # Step 2 输出
```

---

## 七、Step 2 实现：SAM 2 Box Prompt 分割

### 7.1 核心流程

```text
Qwen3-VL Box ──> Box 外扩 12% ──> 全图 + Box → SAM 2 ──> Mask → 合成透明 PNG
        (0-1000)     → 像素坐标            Replicate API        RGBA
```

`step2_sam_segment.py` 实现了完整端到端管线，通过 `Step2Runner` 类封装：

```python
runner = Step2Runner(box_api_key, sam2_token)
runner.run(Path("test_bird.jpg"), "左边那只鸟")
```

### 7.2 SAM 2 API 接入

- **平台**：Replicate（`meta/sam-2`）
- **模式**：全图 + Box Prompt
- **Box 格式**：`[x1, y1, x2, y2]` 像素坐标，外扩 12% Margin
- **API Key**：`REPLICATE_API_TOKEN` 环境变量
- **SDK**：优先使用 `replicate` Python 包，回退到 REST API

### 7.3 可视化输出

每轮测试生成 2 个文件：
- **对比图** (`step2_{image}_{prompt}_comparison.jpg`)：2×2 网格
  - 左上：原图 + Box 标注
  - 右上：SAM 2 输出的 Mask（灰底显示）
  - 左下：透明 PNG 结果（棋盘格背景）
  - 右下：技术信息
- **透明 PNG** (`step2_{image}_{prompt}.png`)：可直接用的抠图结果

### 7.4 成本估算

| 步骤 | 提供方 | 单价 | 100 张总价 |
|------|--------|------|-----------|
| Box 定位 | 硅基流动 Qwen3-VL-32B | ~¥0.003 | ¥0.30 |
| SAM 2 分割 | Replicate meta/sam-2 | ~$0.012 (≈¥0.09) | ¥9.00 |
| **合计** | | **~¥0.093/张** | **¥9.30**
