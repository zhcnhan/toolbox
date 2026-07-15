# 文件转换测试清单 v2

将测试文件放入 `转换前/` 文件夹，然后运行测试脚本。

## 运行方式

```bash
cd apps/format_converter/backend
python ../test_resources/run_test.py
```

转换结果输出到 `转换后/` 文件夹。

记录日志：
```bash
python ../test_resources/run_and_log.py
# 日志输出到 test_result.log / test_stderr.log
```

---

## 需要的测试文件清单

### 1. 数据格式 (5 种 → 任意互转，共 20 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `data.json` | json | 任意 JSON 文件 |
| `data.yaml` | yaml | YAML 文件 |
| `data.csv` | csv | 表格数据 |
| `data.xml` | xml | XML 文件 |
| `data.toml` | toml | TOML 配置文件 |

### 2. 图片格式 (8 种输入 → 7 种输出，共 ~49 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `image.jpg` | jpg | JPEG 图片 |
| `image.png` | png | PNG 图片 |
| `image.webp` | webp | WebP 图片 |
| `image.bmp` | bmp | 位图 |
| `image.gif` | gif | GIF 图片 |
| `image.ico` | ico | 图标文件 |
| `image.tiff` | tiff | TIFF 图片 |
| `image.svg` | svg | SVG 矢量图（仅输入） |

### 3. 音频格式 (9 种输入 → 8 种输出，共 ~64 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `audio.mp3` | mp3 | MP3 音频 |
| `audio.wav` | wav | WAV 音频 |
| `audio.flac` | flac | FLAC 无损音频 |
| `audio.ogg` | ogg | OGG Vorbis |
| `audio.aac` | aac | AAC 音频 |
| `audio.wma` | wma | WMA 音频（仅输入，ffmpeg 不支持 WMA 编码） |
| `audio.m4a` | m4a | M4A 音频 |
| `audio.opus` | opus | Opus 音频 |
| `audio.aiff` | aiff | AIFF 音频 |

### 4. 视频格式 (7 种输入 → 7 种输出，共 ~42 条路径)

| 文件 | 格式 | 说明 |
|------|------|------|
| `video.mp4` | mp4 | MP4 视频 |
| `video.avi` | avi | AVI 视频 |
| `video.mkv` | mkv | MKV 视频 |
| `video.mov` | mov | MOV 视频 |
| `video.webm` | webm | WebM 视频 |
| `video.flv` | flv | FLV 视频 |
| `video.wmv` | wmv | WMV 视频 |

### 5. 文档格式 (8 种输入 → 8 种输出，共 ~56 条路径)

| 文件 | 格式 | 可转换到（已实现） |
|------|------|---------|
| `doc.pdf` | pdf | docx, txt, md, html, rtf, epub, doc |
| `doc.docx` | docx | pdf, txt, html, md, rtf, epub, doc |
| `doc.doc` | doc | docx, pdf, txt, html, md, rtf, epub, doc |
| `doc.txt` | txt | pdf, docx, md, html, rtf, epub, doc |
| `doc.md` | md | pdf, html, txt, docx, rtf, epub, doc |
| `doc.html` | html | pdf, txt, docx, md, rtf, epub, doc |
| `doc.epub` | epub | txt, pdf, docx, md, html, rtf |
| `doc.rtf` | rtf | txt, pdf, docx, md, html, epub, doc |

> **注意**: 带 `doc` 目标的路径需要 LibreOffice；PDF 创建需要 weasyprint；
> EPub 创建需要 ebooklib。无 LibreOffice 时 `→doc` 类路径会失败（预期行为）。

---

## 统计

| 类别 | 输入格式 | 输出格式 | 转换路径 |
|------|---------|---------|---------|
| data | 5 | 5 | 20 |
| audio | 9 | 8 | 64 |
| video | 7 | 7 | 42 |
| image | 8 | 7 | 49 |
| document | 8 | 8 | 56 |
| **合计** | **37** | **35** | **~231** |

---

## 注意事项

- 文件名可以随意，脚本通过扩展名自动识别格式
- 视频和音频转换需要系统安装 `ffmpeg`
- `doc → *` 和 `* → doc` 类路径需要 `LibreOffice`
- `md → pdf` 和 `html → pdf` 需要 `weasyprint`
- `* → epub` 需要 `ebooklib`
- `svg` 输入需要 `cairosvg`
- 文件大小建议控制在 10MB 以内以加快测试速度
