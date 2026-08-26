#!/usr/bin/env python3
"""安装仓库级 `git paper-merge` 命令。

安装一次后，可在同一仓库的任意 worktree 中直接运行：

    git paper-merge

默认使用 fast overlay；完整 overlay 使用：

    git paper-merge --full

其他参数（如 --open、--no-build）会继续传给 preview_latest.py。
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ALIAS_NAME = "paper-merge"
TOOLS_DIRNAME = "cumcm-preview-tools"
BOOTSTRAP_NAME = "paper_merge_anywhere.py"


def out(args, cwd: Path | None = None) -> str:
    p = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.stdout.strip()


def roots() -> tuple[Path, Path, Path]:
    current = Path(out(["git", "rev-parse", "--show-toplevel"])).resolve()
    raw = Path(out(["git", "rev-parse", "--git-common-dir"], cwd=current))
    common_git = raw if raw.is_absolute() else (current / raw)
    common_git = common_git.resolve()
    common_root = common_git.parent.resolve()
    if not (common_root / ".git").exists():
        raise SystemExit(f"无法解析共享主仓库根目录：{common_root}")
    return current, common_git, common_root


def shell_path(path: Path) -> str:
    # Git for Windows 的 alias 由 sh 执行，正斜杠路径兼容性更好。
    return str(path.resolve()).replace("\\", "/")


def install() -> None:
    current, common_git, common_root = roots()
    source = Path(__file__).resolve().with_name(BOOTSTRAP_NAME)
    if not source.exists():
        raise SystemExit(f"缺少安装源文件：{source}")

    tool_dir = common_git / TOOLS_DIRNAME
    tool_dir.mkdir(parents=True, exist_ok=True)
    target = tool_dir / BOOTSTRAP_NAME
    shutil.copy2(source, target)

    python_exe = shell_path(Path(sys.executable))
    bootstrap = shell_path(target)
    alias = (
        "!f() { "
        + shlex.quote(python_exe)
        + " "
        + shlex.quote(bootstrap)
        + ' "$@"; }; f'
    )
    subprocess.run(
        ["git", "config", "--local", f"alias.{ALIAS_NAME}", alias],
        cwd=common_root,
        check=True,
    )

    print("[PASS] 已安装仓库级命令：git paper-merge")
    print("       默认快速总装：git paper-merge")
    print("       完整总装：    git paper-merge --full")
    print("       编译后打开：  git paper-merge --open")
    print("       仅静态总装：  git paper-merge --no-build")
    print("[INFO] 当前 worktree:", current)
    print("[INFO] 主仓库根目录:", common_root)
    print("[INFO] 启动器安装到:", target)


def uninstall() -> None:
    _current, common_git, common_root = roots()
    subprocess.run(
        ["git", "config", "--local", "--unset-all", f"alias.{ALIAS_NAME}"],
        cwd=common_root,
        check=False,
    )
    tool_dir = common_git / TOOLS_DIRNAME
    if tool_dir.exists():
        shutil.rmtree(tool_dir)
    print("[PASS] 已卸载 git paper-merge。")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()
    if args.uninstall:
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
