"""CLI 入口 — add / sync / list / remove。"""

import argparse
import sys
import io

from git_mirror import __version__
from git_mirror.config import load_config, save_config, get_work_dir
from git_mirror.sync import init_repo, sync_once

# Windows GBK 兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def cmd_add(args):
    """添加一个仓库到配置。"""
    config = load_config()

    if args.name in config["repos"]:
        print(f"[WARN] 仓库 '{args.name}' 已存在，将更新 remote 配置。")
        repo = config["repos"][args.name]
    else:
        repo = {"remotes": {}, "sync_rules": []}
        config["repos"][args.name] = repo

    for r in args.remote:
        if "=" not in r:
            print(f"[ERROR] remote 格式错误: '{r}'，应为 label=url")
            sys.exit(1)
        label, url = r.split("=", 1)
        repo["remotes"][label] = url

    # 自动生成双向同步规则（如果设了多个 remote）
    if len(repo["remotes"]) >= 2 and not repo["sync_rules"]:
        labels = list(repo["remotes"].keys())
        for i, src in enumerate(labels):
            for dst in labels:
                if src != dst:
                    rule = {"from": src, "to": dst}
                    if rule not in repo["sync_rules"]:
                        repo["sync_rules"].append(rule)

    save_config(config)
    print(f"✅ 仓库 '{args.name}' 已配置:")
    for label, url in repo["remotes"].items():
        print(f"     {label}: {url}")
    if repo["sync_rules"]:
        print(f"  同步规则:")
        for rule in repo["sync_rules"]:
            print(f"    {rule['from']} → {rule['to']}")


def cmd_sync(args):
    """执行同步。"""
    config = load_config()
    work_dir = get_work_dir(config)

    if args.all:
        if not config["repos"]:
            print("没有配置任何仓库。")
            sys.exit(0)
        for name, repo in config["repos"].items():
            if not repo["sync_rules"]:
                print(f"[SKIP] {name}: 未配置同步规则")
                continue
            _sync_repo(name, repo, work_dir)
    else:
        if args.name not in config["repos"]:
            print(f"[ERROR] 仓库 '{args.name}' 未配置，请先 add")
            sys.exit(1)
        repo = config["repos"][args.name]

        if args.source and args.target:
            # 单次临时同步
            _sync_repo(args.name, repo, work_dir, from_label=args.source, to_label=args.target)
        else:
            # 按配置的规则同步
            if not repo["sync_rules"]:
                print(f"[ERROR] 未指定 --from/--to，且仓库 '{args.name}' 无同步规则")
                sys.exit(1)
            _sync_repo(args.name, repo, work_dir)


def _sync_repo(name: str, repo: dict, work_dir, from_label=None, to_label=None):
    """执行一个仓库的同步。"""
    repo_dir = init_repo(name, work_dir)

    if from_label and to_label:
        print(f"\n🔄 [{name}] {from_label} → {to_label}")
        sync_once(name, repo_dir, from_label, to_label, repo["remotes"])
    else:
        for rule in repo["sync_rules"]:
            print(f"\n🔄 [{name}] {rule['from']} → {rule['to']}")
            sync_once(name, repo_dir, rule["from"], rule["to"], repo["remotes"])


def cmd_list(args=None):
    """列出所有配置的仓库。"""
    config = load_config()

    if not config["repos"]:
        print("没有配置任何仓库。\n使用: git-mirror add <name> -r label=url ...")
        return

    for name, repo in config["repos"].items():
        print(f"\n📦 {name}")
        print(f"   Remotes:")
        for label, url in repo["remotes"].items():
            print(f"     {label}: {url}")
        if repo["sync_rules"]:
            print(f"   同步规则:")
            for rule in repo["sync_rules"]:
                print(f"     {rule['from']} → {rule['to']}")


def cmd_remove(args):
    """删除一个仓库配置。"""
    config = load_config()

    if args.name not in config["repos"]:
        print(f"[ERROR] 仓库 '{args.name}' 不存在")
        sys.exit(1)

    del config["repos"][args.name]
    save_config(config)
    print(f"✅ 已移除仓库 '{args.name}'（bare 仓库目录不受影响）")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="git-mirror",
        description="通用 Git 仓库双向镜像同步工具",
    )
    parser.add_argument("-v", "--version", action="version", version=f"git-mirror {__version__}")

    sub = parser.add_subparsers(dest="command")

    # ---- add ----
    p_add = sub.add_parser("add", help="添加仓库")
    p_add.add_argument("name", help="仓库名称")
    p_add.add_argument("-r", "--remote", action="append", default=[],
                       help="remote 配置，格式: label=url（可多次指定）")
    p_add.set_defaults(func=cmd_add)

    # ---- sync ----
    p_sync = sub.add_parser("sync", help="同步仓库")
    p_sync.add_argument("name", nargs="?", help="仓库名称（--all 时可选）")
    p_sync.add_argument("--all", action="store_true", help="同步所有仓库")
    p_sync.add_argument("--from", dest="source", help="源 remote 标签")
    p_sync.add_argument("--to", dest="target", help="目标 remote 标签")
    p_sync.set_defaults(func=cmd_sync)

    # ---- list ----
    p_list = sub.add_parser("list", help="列出所有仓库")
    p_list.set_defaults(func=cmd_list)

    # ---- remove ----
    p_remove = sub.add_parser("remove", help="移除仓库配置")
    p_remove.add_argument("name", help="仓库名称")
    p_remove.set_defaults(func=cmd_remove)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
