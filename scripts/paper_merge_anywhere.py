#!/usr/bin/env python3
"""仓库级全文总装启动器。

此文件通常由 install_paper_merge.py 安装到共享 git common-dir 中，并通过
`git paper-merge` 从任意 worktree 调用。每次运行都会先拉取 origin/feature/shared
上的最新版 preview_latest.py，再执行全文临时 overlay。

启动器只读取调用者 worktree，不允许全文总装推进或切换调用者所在分支。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def out(args, cwd: Path | None = None, check: bool = True) -> str:
    p = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )
    return p.stdout


def repo_roots() -> tuple[Path, Path, Path]:
    current = Path(out(["git", "rev-parse", "--show-toplevel"]).strip()).resolve()
    raw = Path(out(["git", "rev-parse", "--git-common-dir"], cwd=current).strip())
    common_git = raw if raw.is_absolute() else (current / raw)
    common_git = common_git.resolve()
    common_root = common_git.parent.resolve()
    if not (common_root / ".git").exists():
        raise SystemExit(f"无法解析共享主仓库根目录：{common_root}")
    return current, common_git, common_root


def worktree_state(root: Path) -> tuple[str, str]:
    branch = out(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=root,
        check=False,
    ).strip()
    head = out(["git", "rev-parse", "HEAD"], cwd=root).strip()
    return branch or "(detached)", head


def main() -> None:
    current, common_git, common_root = repo_roots()
    caller_before = worktree_state(current)
    args = list(sys.argv[1:])
    full = False
    if "--full" in args:
        args.remove("--full")
        full = True

    print("[INFO] 更新远端责任分支引用")
    subprocess.run(["git", "fetch", "origin", "--prune"], cwd=common_root, check=True)

    latest = out(
        ["git", "show", "origin/feature/shared:scripts/preview_latest.py"],
        cwd=common_root,
    )
    tool_dir = common_git / "cumcm-preview-tools"
    tool_dir.mkdir(parents=True, exist_ok=True)
    runtime = tool_dir / "preview_latest_runtime.py"
    runtime.write_text(latest, encoding="utf-8")

    cmd = [sys.executable, str(runtime), "--caller-root", str(current)]
    if not full:
        cmd.append("--fast")
    cmd.extend(args)

    mode = "full" if full else "fast"
    print(f"[INFO] paper merge mode: {mode}")
    print(f"[INFO] caller worktree: {current}")
    try:
        subprocess.run(cmd, cwd=common_root, check=True)
    finally:
        caller_after = worktree_state(current)
        if caller_after != caller_before:
            raise RuntimeError(
                "paper-merge 检测到调用者 worktree 的 HEAD 发生变化，已中止。\n"
                f"before: branch={caller_before[0]}, HEAD={caller_before[1]}\n"
                f"after:  branch={caller_after[0]}, HEAD={caller_after[1]}\n"
                "全文总装只能在独立临时 worktree/分支中产生提交。"
            )


if __name__ == "__main__":
    main()
