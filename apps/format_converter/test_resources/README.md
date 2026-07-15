# 文件转换测试清单

> **状态**: 37/37 测试文件就绪 · 171/171 转换路径全部通过 ✅（2026-07-15）

将以下文件放入 `转换前/` 文件夹，然后运行转换脚本。

## 运行方式

```bash
cd apps/format_converter/backend
python ../test_resources/run_test.py
```

转换结果输出到 `转换后/` 文件夹。

---

## 需要的测试文件清单

### 1. 数据格式 (5 种 → 任意互转，共 20 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `data.json` | json | 任意 JSON 文件 | ✅ |
| `data.yaml` | yaml | YAML 或 YML 均可 | ✅ |
| `data.csv` | csv | 表格数据 | ✅ |
| `data.xml` | xml | XML 文件 | ✅ |
| `data.toml` | toml | TOML 配置文件 | ✅ |

### 2. 图片格式 (8 种输入 → 7 种输出，共 ~49 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `image.jpg` | jpg | JPEG 或 JPEG 均可 | ✅ |
| `image.png` | png | PNG 图片 | ✅ |
| `image.webp` | webp | WebP 图片 | ✅ |
| `image.bmp` | bmp | 位图 | ✅ |
| `image.gif` | gif | GIF 动图或静图均可 | ✅ |
| `image.ico` | ico | 图标文件 | ✅ |
| `image.tiff` | tiff | TIFF 或 TIF 均可 | ✅ |
| `image.svg` | svg | SVG 矢量图（仅输入） | ✅ |

### 3. 音频格式 (9 种输入 → 7 种输出，共 ~56 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `audio.mp3` | mp3 | MP3 音频 | ✅ |
| `audio.wav` | wav | WAV 音频 | ✅ |
| `audio.flac` | flac | FLAC 无损音频 | ✅ |
| `audio.ogg` | ogg | OGG Vorbis | ✅ |
| `audio.aac` | aac | AAC 音频 | ✅ |
| `audio.wma` | wma | WMA 音频（仅输入） | ✅ |
| `audio.m4a` | m4a | M4A 音频 | ✅ |
| `audio.opus` | opus | Opus 音频 | ✅ |
| `audio.aiff` | aiff | AIFF 音频（仅输入） | ✅ |

### 4. 视频格式 (7 种输入 → 5 种输出，共 ~30 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `video.mp4` | mp4 | MP4 视频 | ✅ |
| `video.avi` | avi | AVI 视频 | ✅ |
| `video.mkv` | mkv | MKV 视频 | ✅ |
| `video.mov` | mov | MOV 视频 | ✅ |
| `video.webm` | webm | WebM 视频 | ✅ |
| `video.flv` | flv | FLV 视频（仅输入） | ✅ |
| `video.wmv` | wmv | WMV 视频（仅输入） | ✅ |

### 5. 文档格式 (8 种输入 → 特定路径，共 15 条路径)

| 文件 | 格式 | 可转换到 |
|------|------|---------|
| `doc.pdf` | pdf | docx, txt | ✅ |
| `doc.docx` | docx | pdf, txt, html | ✅ |
| `doc.doc` | doc | docx | ✅ |
| `doc.txt` | txt | pdf, docx, md, html | ✅ |
| `doc.md` | md | pdf, html | ✅ |
| `doc.html` | html | pdf, txt | ✅ |
| `doc.rtf` | rtf | txt | ✅ |
| `doc.epub` | epub | txt（仅输入） | ✅ |

---

## 统计

- **输入格式**: 37 种
- **输出格式**: 30 种
- **转换路径**: 171 条
- **所需测试文件**: 37 个（每种格式 1 个）
- **测试结果**: 171/171 全部通过 ✅

## 运行方式

### Docker 环境

```bash
docker compose run --rm format-converter python test_resources/run_test.py
```

### 本地环境

```bash
cd apps/format_converter/backend
python ../test_resources/run_test.py
```

### Windows 环境

```powershell
cd apps\format_converter\backend
$env:PYTHONIOENCODING='utf-8'
$env:PATH = 'C:\Program Files\GTK3-Runtime Win64\bin;C:\Program Files\LibreOffice\program;' + $env:PATH
python ..\test_resources\run_test.py
```

## 注意事项

- 文件名可以随意，脚本通过扩展名自动识别格式
- Docker 镜像已内置所有依赖（ffmpeg、LibreOffice、GTK3），无需额外安装
- 本地运行需确保 ffmpeg、LibreOffice、GTK3 在 PATH 中
- 文件大小建议控制在 10MB 以内以加快测试速度
- 每个转换最多 60 秒超时，视频编码使用 ultrafast 预设
