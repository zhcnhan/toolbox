# 第三方开源软件声明

本项目使用了以下开源软件，在此对其作者和贡献者表示诚挚感谢。

---

## PySide6

- **许可证**: LGPL v3
- **项目地址**: https://wiki.qt.io/Qt_for_Python
- **版权**: © The Qt Company Ltd.
- **用途**: GUI 框架

> PySide6 是 Qt for Python 的官方绑定，在 LGPL v3 许可下发布。
> 本软件以动态链接方式使用 PySide6，符合 LGPL 的合规要求。

---

## PyYAML

- **许可证**: MIT
- **项目地址**: https://github.com/yaml/pyyaml
- **版权**: © 2017-2021 Ingy döt Net; © 2006-2016 Kirill Simonov
- **用途**: YAML 文件解析与生成

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software...

---

## xmltodict

- **许可证**: MIT
- **项目地址**: https://github.com/martinblech/xmltodict
- **版权**: © 2012 Martin Blech
- **用途**: XML ↔ dict 互转

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction...

---

## tomli / tomli-w

- **许可证**: MIT
- **项目地址**: https://github.com/hukkin/tomli
- **版权**: © Taneli Hukkinen
- **用途**: TOML 文件解析与生成

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software...

---

## Pillow (PIL Fork)

- **许可证**: Historical Permission Notice and Disclaimer (HPND)
- **项目地址**: https://github.com/python-pillow/Pillow
- **版权**: © 2010-2024 Jeffrey A. Clark and contributors
- **用途**: 图片加载、处理和格式转换

> The Python Imaging Library (PIL) is
>
>     Copyright © 1997-2011 by Secret Labs AB
>     Copyright © 1995-2011 by Fredrik Lundh
>
> Pillow is the friendly PIL fork. It is
>
>     Copyright © 2010-2024 by Jeffrey A. Clark and contributors
>
> By obtaining, using, and/or copying this software and/or its associated
> documentation, you agree that you have read, understood, and will comply
> with the following terms and conditions...

---

## pydub

- **许可证**: MIT
- **项目地址**: https://github.com/jiaaro/pydub
- **版权**: © 2011 Robert James and contributors
- **用途**: 音频文件加载和格式转换

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction...

---

## ffmpeg-python

- **许可证**: Apache-2.0
- **项目地址**: https://github.com/kkroening/ffmpeg-python
- **版权**: © Karl Kroening
- **用途**: ffmpeg Python 绑定，用于视频转换

> Licensed under the Apache License, Version 2.0 (the "License");
> you may not use this file except in compliance with the License.
> You may obtain a copy of the License at
>
>     http://www.apache.org/licenses/LICENSE-2.0
>
> Unless required by applicable law or agreed to in writing, software
> distributed under the License is distributed on an "AS IS" BASIS,
> WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

---

## FFmpeg

- **许可证**: LGPL v2.1+ / GPL v2+
- **项目地址**: https://ffmpeg.org/
- **版权**: © 2000-2024 FFmpeg developers
- **用途**: 音视频编解码核心引擎

> FFmpeg 是本项目中音频和视频格式转换的核心依赖。
> FFmpeg 是一个独立的可执行程序，不在本项目的代码库中分发。
> 用户需自行从 https://ffmpeg.org/download.html 下载安装，
> 并将其添加到系统 PATH 环境变量中。
>
> FFmpeg 在 LGPL/GPL 许可下发布：
>   - LGPL 版本: 使用 --enable-version3 等非 GPL 选项编译
>   - GPL 版本:  包含 --enable-gpl 和 --enable-nonfree 选项
>
> 本项目仅通过命令行调用 FFmpeg，不链接其库文件，
> 因此在法律上不构成衍生作品。

---

## Python 标准库

- **许可证**: Python Software Foundation License (PSFL)
- **项目地址**: https://www.python.org/
- **用途**: json, csv, xml, argparse 等标准库模块

---

**声明**: 本项目中各第三方依赖的完整许可证文本可从其各自的源代码仓库中获取。
本文件对其许可证内容的引用仅为摘要说明，不构成法律建议。
使用本项目前，请仔细阅读各第三方组件对应的完整许可条款。
