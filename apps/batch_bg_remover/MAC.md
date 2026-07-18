# 🍎 Mac 安装教程

> 全程 5 分钟，不需要懂代码。

## 一步到位

打开「终端」App，复制粘贴这两行：

```bash
cd ~/Desktop && git clone https://github.com/zhcnhan/toolbox.git
bash ~/Desktop/toolbox/apps/batch_bg_remover/make-mac-app.sh
```

等跑完，桌面出现 `BatchBackgroundRemover.app`。

## 使用

- **打开**：双击桌面图标
- **关闭**：程序坞右键 → 退出
- **首次**会自动装依赖，等 2-3 分钟，之后秒开

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `command not found: brew` | 没装 Homebrew | 先跑 `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| `command not found: git` | 没装 Git | 去 https://git-scm.com/download/mac 下载安装 |
| 打开后浏览器白屏 | 还没启动完 | 等终端出现 `http://localhost:5174` 就行了 |
| 抠图失败：No module named 'torch' | 没启用 CLIPSeg | 引擎切回 rembg 就行 |
