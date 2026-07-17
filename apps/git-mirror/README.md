# Git Mirror

通用 Git 仓库双向镜像同步工具。在任意两个 Git remote（如 Gitee ↔ GitHub）之间同步代码。

## 安装

```bash
cd apps/git-mirror
pip install -e .
```

## 快速开始

```bash
# 1. 添加一个仓库，配置两个 remote
git-mirror add toolbox \
    -r gitee=https://gitee.com/user/toolbox.git \
    -r github=https://github.com/user/toolbox.git

# 2. 同步：码云 → GitHub
git-mirror sync toolbox --from gitee --to github

# 3. 反向同步：GitHub → 码云
git-mirror sync toolbox --from github --to gitee

# 4. 一键同步所有配置的仓库
git-mirror sync --all
```

## 命令

| 命令 | 说明 |
|------|------|
| `git-mirror add <name> -r label=url` | 添加仓库，可多次 `-r` 指定多个 remote |
| `git-mirror sync <name> --from a --to b` | 单向同步：a → b |
| `git-mirror sync --all` | 按配置规则同步所有仓库 |
| `git-mirror list` | 列出所有配置 |
| `git-mirror remove <name>` | 移除仓库配置 |

## 配置

配置文件位于 `~/.git-mirror/config.json`，可手动编辑：

```json
{
  "repos": {
    "toolbox": {
      "remotes": {
        "gitee": "https://gitee.com/user/toolbox.git",
        "github": "https://github.com/user/toolbox.git"
      },
      "sync_rules": [
        {"from": "gitee", "to": "github"},
        {"from": "github", "to": "gitee"}
      ]
    }
  },
  "work_dir": "~/.git-mirror/repos"
}
```

## 原理

使用 `git clone --bare` + `git fetch` + `git push --mirror` 实现，不依赖任何平台 API，纯 Git 命令。
