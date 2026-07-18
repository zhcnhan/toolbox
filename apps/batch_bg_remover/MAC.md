# 🍎 Mac 安装教程

> 全程 5 分钟，不需要懂代码。

## 一步到位

打开「终端」App，一行一行复制执行：

```bash
# 1. 下载代码（用码云镜像，不用翻墙）
cd ~/Desktop && git clone https://gitee.com/gengzisama/toolbox.git

# 2. 生成桌面应用
bash ~/Desktop/toolbox/apps/batch_bg_remover/make-mac-app.sh
```

等跑完，桌面出现「批量抠图.command」。

## 使用

- **打开**：双击「批量抠图.command」
- **关闭**：关掉弹出的终端窗口
- **首次**会自动装依赖，等 2-3 分钟，之后秒开

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `command not found: brew` | 没装 Homebrew | 先跑下面的命令装 brew（已换国内源） |
| `command not found: git` | 没装 Git | 去 https://git-scm.com/download/mac 下载安装 |
| `command not found: npm` | 没装 Node.js | 装 Homebrew 后执行 `brew install node` |
| 下载慢或失败 | GitHub 被墙 | 已经用码云地址了，如果还慢，开一下 VPN |
| 打开后浏览器白屏 | 还没启动完 | 等终端出现 `http://localhost:5174` 就行了 |
| CLIPSeg 抠图失败：No module named 'torch' | 默认没装 torch | 终端跑 `cd ~/Desktop/toolbox/apps/batch_bg_remover && source backend/venv/bin/activate && pip install torch -i https://pypi.tuna.tsinghua.edu.cn/simple` |

**装 Homebrew + Node.js（国内源）：**

```bash
# 装 Homebrew
/bin/bash -c "$(curl -fsSL https://gitee.com/ineo6/homebrew-install/raw/master/install.sh)"

# 装 Node.js（提供 npm 命令）
brew install node
```

装完后继续执行第一步 `git clone`。
