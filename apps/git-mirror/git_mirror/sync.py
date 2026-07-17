"""核心同步逻辑 — clone bare / fetch / push --mirror。"""

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    """执行 git 命令，失败时打印完整错误并退出。"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 命令失败: {' '.join(cmd)}")
        if e.stdout:
            print(f"  stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"  stderr: {e.stderr.strip()}")
        sys.exit(1)


def _ensure_remote(repo_dir: Path, label: str, url: str):
    """确保 bare 仓库中存在指定 remote。"""
    remotes = _run(["git", "-C", str(repo_dir), "remote"])
    existing = [r.strip() for r in remotes.split("\n") if r.strip()]

    if label not in existing:
        _run(["git", "-C", str(repo_dir), "remote", "add", label, url])
        print(f"  + 添加 remote: {label} → {url}")


def init_repo(name: str, work_dir: Path) -> Path:
    """初始化 bare 仓库目录（如果不存在则创建）。"""
    repo_dir = work_dir / name
    repo_dir.mkdir(parents=True, exist_ok=True)
    if not (repo_dir / "HEAD").exists():
        _run(["git", "init", "--bare", str(repo_dir)])
        print(f"  + 初始化 bare 仓库: {repo_dir}")
    return repo_dir


def sync_once(name: str, repo_dir: Path, source_label: str, target_label: str, remotes: dict[str, str]):
    """执行一次单向同步：从 source 拉取，推送到 target。"""
    source_url = remotes.get(source_label)
    target_url = remotes.get(target_label)

    if not source_url:
        print(f"[ERROR] remote '{source_label}' 未配置")
        sys.exit(1)
    if not target_url:
        print(f"[ERROR] remote '{target_label}' 未配置")
        sys.exit(1)

    # 确保两个 remote 都存在
    _ensure_remote(repo_dir, source_label, source_url)
    _ensure_remote(repo_dir, target_label, target_url)

    # 从 source 拉取所有分支和标签
    print(f"  ⬇ fetch {source_label} ({source_url}) ...")
    _run(["git", "-C", str(repo_dir), "fetch", source_label,
          "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "--prune", "--force"])
    print(f"  ✅ 拉取完成")

    # 推送到 target
    print(f"  ⬆ push --mirror → {target_label} ({target_url}) ...")
    output = _run(["git", "-C", str(repo_dir), "push", "--mirror", target_label])
    if output:
        for line in output.split("\n"):
            print(f"     {line.strip()}")
    print(f"  ✅ 推送完成")
