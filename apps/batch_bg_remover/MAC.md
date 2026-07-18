# 🍎 Mac 安装教程

> 全程 5 分钟，不需要懂代码。

## 第一步：装 Homebrew 和 Node.js（只需一次）

打开「终端」App，一行一行复制执行：

```bash
# 装 Homebrew（已换国内源，不用翻墙）
/bin/bash -c "$(curl -fsSL https://gitee.com/ineo6/homebrew-install/raw/master/install.sh)"

# 装 Node.js（提供 npm 命令）
brew install node
```

等跑完才能继续下一步。

## 第二步：下载代码

```bash
cd ~/Desktop && git clone https://gitee.com/gengzisama/toolbox.git
```

## 第三步：生成桌面启动器

```bash
bash ~/Desktop/toolbox/apps/batch_bg_remover/make-mac-app.sh
```

等跑完，桌面出现「批量抠图.command」。

## 使用

- **打开**：双击桌面「批量抠图.command」
- **关闭**：关掉弹出的终端窗口（不会弄坏任何东西）
- **首次启动**会自动装依赖，等 2-3 分钟，之后秒开

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `command not found: git` | 没装 Git | Homebrew 装完就有了，重新开个终端再试 |
| `command not found: npm` | 没装 Node.js | 执行 `brew install node` |
| 下载慢或失败 | 网络问题 | 如果你有 VPN 可以开一下，没有就多试几次 |
| 打开后浏览器白屏 | 还没启动完 | 等终端出现 `http://localhost:5174` 就行了 |
| CLIPSeg 抠图失败：No module named 'torch' | 默认没装 torch | 终端跑 `cd ~/Desktop/toolbox/apps/batch_bg_remover && source backend/venv/bin/activate && pip install torch -i https://pypi.tuna.tsinghua.edu.cn/simple` |
