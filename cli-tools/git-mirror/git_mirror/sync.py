"""核心同步逻辑 — clone bare / fetch / push --all + --tags，含自动凭据管理。"""

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, quote

from git_mirror.config import DEFAULT_CONFIG_DIR

CREDENTIAL_FILE = DEFAULT_CONFIG_DIR / "credentials.json"


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    """执行 git 命令，失败时打印完整错误并退出。"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 命令失败: {' '.join(cmd)}")
        if e.stdout:
            print(f"  stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"  stderr: {e.stderr.strip()}")
        sys.exit(1)


def _try_run(cmd: list[str], cwd: Path | None = None) -> dict:
    """执行命令，不退出，返回结果字典。"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True,
        )
        return {"ok": True, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "stdout": e.stdout.strip() if e.stdout else "",
                "stderr": e.stderr.strip() if e.stderr else "", "code": e.returncode}


def _ensure_remote(repo_dir: Path, label: str, url: str):
    """确保 bare 仓库中存在指定 remote。"""
    remotes = _run(["git", "-C", str(repo_dir), "remote"])
    existing = [r.strip() for r in remotes.split("\n") if r.strip()]
    if label not in existing:
        _run(["git", "-C", str(repo_dir), "remote", "add", label, url])
        print(f"  + 添加 remote: {label} -> {url}")
    else:
        # 确保 URL 是最新的
        current = _run(["git", "-C", str(repo_dir), "remote", "get-url", label])
        if current != url:
            _run(["git", "-C", str(repo_dir), "remote", "set-url", label, url])


def init_repo(name: str, work_dir: Path) -> Path:
    """初始化 bare 仓库目录（如果不存在则创建）。"""
    repo_dir = work_dir / name
    repo_dir.mkdir(parents=True, exist_ok=True)
    if not (repo_dir / "HEAD").exists():
        _run(["git", "init", "--bare", str(repo_dir)])
        print(f"  + 初始化 bare 仓库: {repo_dir}")
    return repo_dir


# ---------------------------------------------------------------------------
# 凭据管理
# ---------------------------------------------------------------------------

def _load_credentials() -> dict:
    """加载保存的凭据。"""
    if not CREDENTIAL_FILE.exists():
        return {}
    with open(CREDENTIAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_credentials(creds: dict):
    """保存凭据到文件，限制权限。"""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # 尝试限制权限（仅 owner 可读写）
    try:
        os.chmod(CREDENTIAL_FILE, 0o600)
    except OSError:
        pass


def _host_key(url: str) -> str:
    """从 URL 中提取 hostkey 用于凭据索引。"""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    # 去掉端口
    return host


def _get_stored_credential(url: str) -> tuple[str, str] | None:
    """获取已保存的凭据（username, token）。"""
    creds = _load_credentials()
    key = _host_key(url)
    entry = creds.get(key)
    if entry:
        return entry.get("username", ""), entry.get("token", "")
    return None


def _prompt_and_save_credential(url: str, label: str) -> tuple[str, str]:
    """询问用户凭据并保存。"""
    key = _host_key(url)
    print(f"\n  [AUTH] {label} ({key}) 需要身份验证")
    print(f"  URL: {url}")
    username = input("  用户名 / Git 平台 (如 github, gitee): ").strip()
    token = input("  Personal Access Token（输入时不显示）: ").strip()

    if not token:
        print("  [SKIP] 未提供 token，跳过本次推送")
        return "", ""

    creds = _load_credentials()
    creds[key] = {"username": username, "token": token}
    _save_credentials(creds)
    print(f"  + 凭据已保存到 {CREDENTIAL_FILE}")
    return username, token


def _embed_credentials(url: str, username: str, token: str) -> str:
    """在 HTTPS URL 中嵌入凭据。"""
    parsed = urlparse(url)
    if username:
        netloc = f"{quote(username, safe='')}:{quote(token, safe='')}@{parsed.hostname}"
    else:
        netloc = f"oauth2:{quote(token, safe='')}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def _is_auth_error(stderr: str, stdout: str = "") -> bool:
    """判断 git 输出是否为身份验证错误。"""
    text = (stderr + " " + stdout).lower()
    keywords = [
        "authentication failed", "401", "403",
        "could not read username", "could not read password",
        "invalid username or password",
        "remote: invalid username or password",
        "fatal: could not read password",
        "permission denied", "access denied",
        "remote: unauthorized", "remote: not authorized",
        "fatal: authentication failed",
        "no permission",
    ]
    return any(k in text for k in keywords)


# ---------------------------------------------------------------------------
# 推送（自动处理凭据）
# ---------------------------------------------------------------------------

def _push_all(repo_dir: Path, target_label: str, target_url: str):
    """执行 git push --all --tags（推送所有分支和标签），凭据缺失时自动询问用户。"""
    # 先尝试直接用已保存的凭据
    cred = _get_stored_credential(target_url)
    if cred and cred[1]:
        username, token = cred
        auth_url = _embed_credentials(target_url, username, token)
        _run(["git", "-C", str(repo_dir), "remote", "set-url", target_label, auth_url])
        result = _try_run(["git", "-C", str(repo_dir), "push", "--all", target_label])
        if result["ok"]:
            _try_run(["git", "-C", str(repo_dir), "push", "--tags", target_label])
        _run(["git", "-C", str(repo_dir), "remote", "set-url", target_label, target_url])
        if result["ok"]:
            _print_push_output(result)
            return
        elif not _is_auth_error(result["stderr"], result["stdout"]):
            # 不是 auth 错误，直接报错退出
            _print_push_output(result)
            sys.exit(1)
        # auth 错误，清除过期凭据，重新询问
        creds = _load_credentials()
        key = _host_key(target_url)
        creds.pop(key, None)
        _save_credentials(creds)
        print(f"  [AUTH] 已保存的凭据已过期，请重新输入")

    # 无凭据或已过期 → 直接尝试 push（可能 SSH key 已配好）
    result = _try_run(["git", "-C", str(repo_dir), "push", "--all", target_label])
    if result["ok"]:
        _try_run(["git", "-C", str(repo_dir), "push", "--tags", target_label])
        return
    # 如果 --all 失败且没有 tags，也返回
    if _is_auth_error(result["stderr"], result["stdout"]):
        pass  # 继续到下面处理 auth
    else:
        _print_push_output(result)
        return

    # 检查是不是 SSH URL（不用管凭据）
    if target_url.startswith("git@"):
        _print_push_output(result)
        sys.exit(1)

    # HTTPS auth 错误 → 问用户
    if _is_auth_error(result["stderr"], result["stdout"]):
        username, token = _prompt_and_save_credential(target_url, target_label)
        if not token:
            sys.exit(1)

        auth_url = _embed_credentials(target_url, username, token)
        _run(["git", "-C", str(repo_dir), "remote", "set-url", target_label, auth_url])
        try:
            output = _try_run(["git", "-C", str(repo_dir), "push", "--all", target_label])
            if output["ok"]:
                _print_push_output(output)
                _try_run(["git", "-C", str(repo_dir), "push", "--tags", target_label])
            else:
                # 凭据可能错误
                print(f"\n[ERROR] 推送失败，凭据可能不正确")
                _print_push_output(output)
                # 删除错误凭据
                creds = _load_credentials()
                key = _host_key(target_url)
                creds.pop(key, None)
                _save_credentials(creds)
                sys.exit(1)
        finally:
            _run(["git", "-C", str(repo_dir), "remote", "set-url", target_label, target_url])
    else:
        # 非 auth 错误
        _print_push_output(result)
        sys.exit(1)


def _print_push_output(result: dict):
    """打印推送输出。"""
    if result.get("stdout"):
        for line in result["stdout"].split("\n"):
            line = line.strip()
            if line:
                print(f"     {line}")
    if result.get("stderr") and "Everything up-to-date" not in result["stderr"]:
        for line in result["stderr"].split("\n"):
            line = line.strip()
            # 过滤掉凭据中的 token 信息
            if line and "http" not in line.lower():
                print(f"     {line}")


# ---------------------------------------------------------------------------
# 同步入口
# ---------------------------------------------------------------------------

def sync_once(name: str, repo_dir: Path, source_label: str, target_label: str,
              remotes: dict[str, str]):
    """执行一次单向同步：从 source 拉取，推送到 target。"""
    source_url = remotes.get(source_label)
    target_url = remotes.get(target_label)

    if not source_url:
        print(f"[ERROR] remote '{source_label}' 未配置")
        sys.exit(1)
    if not target_url:
        print(f"[ERROR] remote '{target_label}' 未配置")
        sys.exit(1)

    _ensure_remote(repo_dir, source_label, source_url)
    _ensure_remote(repo_dir, target_label, target_url)

    # fetch
    print(f"  [v] fetch {source_label} ({source_url}) ...")
    fetch_result = _try_run(["git", "-C", str(repo_dir), "fetch", source_label,
                             "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*",
                             "--prune", "--force"])
    if not fetch_result["ok"]:
        if _is_auth_error(fetch_result["stderr"], fetch_result["stdout"]):
            print(f"  [AUTH] fetch {source_label} 需要凭据（私有仓库）")
            print(f"  暂时仅支持公开仓库的 pull，私有仓库 pull 请先在服务器配好 SSH key")
        _print_push_output(fetch_result)
        sys.exit(1)
    print(f"  [OK] 拉取完成")

    # push
    print(f"  [^] push --all + --tags -> {target_label} ({target_url}) ...")
    _push_all(repo_dir, target_label, target_url)
    print(f"  [OK] 推送完成")
