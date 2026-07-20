# 🍎 Mac 安装教程

> 全程 5 分钟，不需要懂代码。

## 第一步：装 Node.js（只需一次）

打开「终端」App，先检查电脑上有没有 Node.js：

```bash
node -v
```

如果显示 `v18.x.x` 之类的版本号，说明已经有了，直接跳到第二步。

如果没有，去 **https://nodejs.org** 下载 macOS 安装包（选 LTS 长期支持版），双击安装，一路点「继续」就行。

> 不用装 Homebrew，不用管任何命令行，下载 → 双击 → 下一步 → 完成。

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
- **浏览器访问**：打开后自动弹出 `http://localhost:8001`

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `command not found: git` | 没装 Git | 去 https://git-scm.com/download/mac 下载安装 |
| `command not found: npm` | 没装 Node.js | 去 https://nodejs.org 下载 macOS 安装包 |
| Python 弹窗要输密码 | 自动安装 Python 需要权限 | 输入 Mac 开机密码就行，只这一次 |
| 双击「批量抠图.command」提示无法验证开发者 | macOS 安全策略拦截 | 去「系统设置 → 隐私与安全性 → 安全性」，点「仍要打开」；或按住 `⌃Control` 键再双击文件 |
| 下载慢或失败 | 网络问题 | 如果有 VPN 就开一下，没有就多试几次 |
| 打开后浏览器白屏 | 还没启动完 | 等终端出现 `http://localhost:8001` 就行了 |
