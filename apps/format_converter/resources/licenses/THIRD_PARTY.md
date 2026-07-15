# 第三方开源软件声明

本项目使用了以下开源软件，在此对其作者和贡献者表示诚挚感谢。

---

## FastAPI

- **许可证**: MIT
- **项目地址**: https://github.com/tiangolo/fastapi
- **版权**: © 2018 Sebastián Ramírez
- **用途**: 后端 Web 框架

---

## Uvicorn

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/encode/uvicorn
- **版权**: © Encode OSS Ltd.
- **用途**: ASGI 服务器

---

## PyYAML

- **许可证**: MIT
- **项目地址**: https://github.com/yaml/pyyaml
- **版权**: © 2017-2021 Ingy döt Net; © 2006-2016 Kirill Simonov
- **用途**: YAML 文件解析与生成

---

## xmltodict

- **许可证**: MIT
- **项目地址**: https://github.com/martinblech/xmltodict
- **版权**: © 2012 Martin Blech
- **用途**: XML ↔ dict 互转

---

## tomli / tomli-w

- **许可证**: MIT
- **项目地址**: https://github.com/hukkin/tomli
- **版权**: © Taneli Hukkinen
- **用途**: TOML 文件解析与生成

---

## Pillow (PIL Fork)

- **许可证**: Historical Permission Notice and Disclaimer (HPND)
- **项目地址**: https://github.com/python-pillow/Pillow
- **版权**: © 2010-2024 Jeffrey A. Clark and contributors
- **用途**: 图片加载、处理和格式转换

---

## pydub

- **许可证**: MIT
- **项目地址**: https://github.com/jiaaro/pydub
- **版权**: © 2011 Robert James and contributors
- **用途**: 音频文件加载和格式转换

---

## ffmpeg-python

- **许可证**: Apache-2.0
- **项目地址**: https://github.com/kkroening/ffmpeg-python
- **版权**: © Karl Kroening
- **用途**: ffmpeg Python 绑定（视频转换辅助）

> 本项目的视频转换已改为直接调用 ffmpeg 子进程，ffmpeg-python 仅作为备用依赖保留。

---

## FFmpeg

- **许可证**: LGPL v2.1+ / GPL v2+ (取决于编译选项)
- **项目地址**: https://ffmpeg.org/
- **版权**: © 2000-2024 FFmpeg developers
- **用途**: 音视频编解码核心引擎

> FFmpeg 是本项目中音频和视频格式转换的核心依赖。
> FFmpeg 是一个独立的可执行程序，不在本项目的代码库中分发。
> 本项目仅通过命令行调用 FFmpeg，不链接其库文件，因此在法律上不构成衍生作品。
> Docker 镜像中通过 `apt-get install ffmpeg` 安装。

---

## pdf2docx

- **许可证**: MIT
- **项目地址**: https://github.com/ArtifexSoftware/pdf2docx
- **版权**: © Artifex Software
- **用途**: PDF → DOCX 转换

---

## python-docx

- **许可证**: MIT
- **项目地址**: https://github.com/python-openxml/python-docx
- **版权**: © Steve Canny
- **用途**: DOCX 文档读写

---

## PyPDF2

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/py-pdf/pypdf
- **版权**: © Mathieu Fenniak
- **用途**: PDF 文本提取

---

## ReportLab

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/MrBitBucket/reportlab-mirror
- **版权**: © ReportLab Inc.
- **用途**: PDF 生成（TXT/DOCX → PDF 回退方案、SVG 渲染辅助）

---

## WeasyPrint

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/Kozea/WeasyPrint
- **版权**: © Simon Sapin
- **用途**: HTML/Markdown → PDF 转换

---

## Markdown

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/Python-Markdown/markdown
- **版权**: © 2019-2024 Waylan Limberg; © 2007-2018 Manfred Stienstra, Yuri Takhteyev
- **用途**: Markdown → HTML 转换

---

## ebooklib

- **许可证**: AGPL-3.0
- **项目地址**: https://github.com/aerkalov/ebooklib
- **版权**: © Aleksandar Erkalov
- **用途**: EPUB 电子书读取

> ebooklib 在 AGPL-3.0 许可下发布。使用此库时请注意 AGPL 的传染性条款：
> 如果你通过网络提供服务，需要向用户提供你修改后的源代码。
> 本项目仅作为调用方使用 ebooklib，未修改其源代码。

---

## BeautifulSoup4 (bs4)

- **许可证**: MIT
- **项目地址**: https://www.crummy.com/software/BeautifulSoup/
- **版权**: © Leonard Richardson
- **用途**: HTML 解析（HTML → TXT、EPUB → TXT）

---

## striprtf

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/joshy/striprtf
- **版权**: © Joshy PHP
- **用途**: RTF → TXT 转换

---

## CairoSVG

- **许可证**: LGPL-3.0
- **项目地址**: https://github.com/Kozea/CairoSVG
- **版权**: © Kozea
- **用途**: SVG → 位图格式转换

> CairoSVG 在 LGPL-3.0 许可下发布。本项目以动态调用方式使用 CairoSVG，符合 LGPL 合规要求。

---

## svglib

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/deeplook/svglib
- **版权**: © Dinu Gherman
- **用途**: SVG 渲染回退方案

---

## rlPyCairo

- **许可证**: BSD-3-Clause
- **项目地址**: https://github.com/MrBitBucket/rlPyCairo
- **版权**: © ReportLab Inc.
- **用途**: ReportLab Cairo 后端（svglib 渲染辅助）

---

## @react-three/rapier

- **许可证**: MIT
- **项目地址**: https://github.com/pmndrs/react-three-rapier
- **版权**: © Paul Henschel
- **用途**: 3D 物理引擎，驱动右下角互动小猫的碰撞、弹跳和拖拽物理效果

---

## Rapier (Rust physics engine)

- **许可证**: Apache-2.0
- **项目地址**: https://rapier.rs/
- **版权**: © Dimforge
- **用途**: @react-three/rapier 的底层 WASM 物理引擎

> Rapier 在 Apache-2.0 许可下发布。本项目通过 WASM 模块使用 Rapier，不修改其源代码。

---

## LibreOffice

- **许可证**: MPL-2.0
- **项目地址**: https://www.libreoffice.org/
- **版权**: © The Document Foundation
- **用途**: DOC → DOCX 转换、DOCX → PDF 高质量转换

> LibreOffice 在 MPL-2.0 许可下发布。
> 本项目通过 headless 模式调用 LibreOffice 进行文档转换，不修改其源代码。
> Docker 镜像中通过 `apt-get install libreoffice` 安装。

---

## GTK3 Runtime / Cairo / Pango

- **许可证**: LGPL-2.1+
- **项目地址**: https://www.gtk.org/
- **版权**: © GTK Development Team
- **用途**: SVG 渲染底层依赖（CairoSVG / WeasyPrint）

> GTK3、Cairo、Pango 等库在 LGPL-2.1+ 许可下发布。
> 本项目仅通过动态链接使用这些库，符合 LGPL 合规要求。

---

## Noto CJK Fonts

- **许可证**: OFL-1.1 (SIL Open Font License)
- **项目地址**: https://github.com/notofonts/noto-cjk
- **版权**: © Google Inc.
- **用途**: 中日韩文字渲染（Docker 镜像中的字体支持）

---

## Python 标准库

- **许可证**: Python Software Foundation License (PSFL)
- **项目地址**: https://www.python.org/
- **用途**: json, csv, xml, struct, io, os, subprocess 等标准库模块

---

**声明**: 本项目中各第三方依赖的完整许可证文本可从其各自的源代码仓库中获取。
本文件对其许可证内容的引用仅为摘要说明，不构成法律建议。
使用本项目前，请仔细阅读各第三方组件对应的完整许可条款。

---

## 许可证兼容性说明

本项目自身使用 **MIT** 许可证发布。上述第三方依赖的许可证类型汇总如下：

| 许可证类型 | 组件 |
|-----------|------|
| MIT | FastAPI, PyYAML, xmltodict, tomli/tomli-w, pydub, pdf2docx, python-docx, BeautifulSoup4, @react-three/rapier |
| BSD-3-Clause | Uvicorn, PyPDF2, ReportLab, WeasyPrint, Markdown, svglib, rlPyCairo, striprtf |
| HPND | Pillow |
| Apache-2.0 | ffmpeg-python, Rapier |
| LGPL-2.1+ / LGPL-3.0 | GTK3/Cairo/Pango, CairoSVG |
| MPL-2.0 | LibreOffice |
| AGPL-3.0 | ebooklib (请注意 AGPL 条款) |
| OFL-1.1 | Noto CJK Fonts |
| LGPL/GPL | FFmpeg (独立程序，命令行调用) |
| PSFL | Python 标准库 |

> **AGPL 注意事项**: `ebooklib` 使用 AGPL-3.0 许可。如果您通过网络提供本服务且修改了
> ebooklib 的源代码，您需要向用户提供修改后的源代码。本项目未修改 ebooklib 源代码，
> 仅作为调用方使用。如需避免 AGPL 影响，可移除 EPUB → TXT 转换功能及相关依赖。
