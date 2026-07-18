# 🍎 Mac 安装教程

> 全程约 10 分钟，不需要懂代码。有问题找开发者。

---

## 一、装依赖

打开「终端」App（在「启动台」→「其他」文件夹里），复制粘贴下面这一行，回车：

```bash
brew install python@3.12 node
```

**如果提示 `command not found: brew`**，先执行这个（等几分钟）：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
装完再运行上面的 `brew install ...`

---

## 二、下载代码

```bash
cd ~/Desktop && git clone https://github.com/zhcnhan/toolbox.git
```

> 如果提示 `command not found: git`，去 https://git-scm.com/download/mac 下载安装，装完重启终端再试。

---

## 三、启动

```bash
cd ~/Desktop/toolbox/apps/batch_bg_remover
chmod +x batch-bg-mac.sh
./batch-bg-mac.sh
```

第一次会装依赖，看到 `pip` 和 `npm` 跑进度条是正常的，等它跑完。

**最后显示：**
```
✅ 启动完成！
前端: http://localhost:5174
后端: http://localhost:8001
按 Ctrl+C 停止所有服务
```

---

## 四、使用

打开浏览器，访问 `http://localhost:5174`

- **抠图**：拖入图片 → 选引擎 → 点「开始」
- **提示词修正**：点图片下的「✏️ 修正」→ 输入文字（如「猫」）→ 确定
- **CLIPSeg 灵敏度**：引擎选「CLIPSeg 本地」，设置里可以调滑块
- **云端引擎**：需要去对应网站申请 API Key，填进设置里

---

## 五、下次再用

打开终端，执行：

```bash
cd ~/Desktop/toolbox/apps/batch_bg_remover
./batch-bg-mac.sh
```

---

## 可能的问题

| 现象 | 怎么办 |
|------|--------|
| `pip: command not found` | 装 Python 时没加 PATH，重跑 `brew install python@3.12` |
| `npm: command not found` | 装 Node 时有问题，重跑 `brew install node` |
| 浏览器打开是白屏 | 等前端启动（看终端有没有 `➜ Local: http://localhost:5174`） |
| 抠图失败：No module named 'torch' | 这个电脑不支持 CLIPSeg，切回 rembg 引擎就行 |
| 端口被占用 | 关掉其他占 8001/5174 端口的程序 |

---

## 关掉程序

终端里按 `Ctrl + C`，或者直接关掉终端窗口。
