# cli-tools — 命令行工具

纯命令行工具集合。每个工具是独立的 Python 包或脚本，通过命令行参数交互，适合自动化流程、批量处理和 CI/CD 集成。

## 工具列表

| 工具 | 说明 |
|------|------|
| [git-mirror](./git-mirror/) | Git 仓库双向镜像同步 — 在任意两个 remote 之间同步代码 |

## 约定

- 每个子目录是一个独立工具，自带 `pyproject.toml`、`requirements.txt` 和 `README.md`
- `pip install -e .` 即可安装为全局命令
- 不依赖仓库中的其他模块
