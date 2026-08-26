#!/usr/bin/env python3
from __future__ import annotations

"""Report stale/diverged temporary branches without deleting anything.

Typical use after a squash merge:
    python scripts/branch_hygiene.py

The script classifies origin/chore/* branches against origin/main.  A branch
that is both ahead and behind main is not automatically safe to merge: this is
exactly what a squash-source branch looks like after its consolidated commit
has landed on main.  Inspect it, then delete the stale remote branch manually.
"""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, check: bool = True) -> str:
    p = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if check and p.returncode:
        raise SystemExit(p.stderr.strip() or "git command failed")
    return p.stdout.strip()


def counts(base: str, branch: str) -> tuple[int, int]:
    out = run("rev-list", "--left-right", "--count", f"{base}...{branch}")
    left, right = out.split()
    return int(left), int(right)  # main-only, branch-only


def short_sha(ref: str) -> str:
    return run("rev-parse", "--short=12", ref)


def classify(behind: int, ahead: int) -> str:
    if ahead == 0 and behind == 0:
        return "与 main 相同，可删除临时分支"
    if ahead == 0:
        return "仅落后 main；通常已无独立内容，可核对后删除"
    if behind == 0:
        return "仅领先 main；仍有未进入 main 的提交"
    return "已分叉；可能是 squash 后遗留分支，禁止直接再次 merge"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="main", help="稳定主分支，默认 main")
    ap.add_argument("--prefix", default="chore/", help="检查的临时分支前缀")
    ap.add_argument("--no-fetch", action="store_true", help="跳过 git fetch")
    a = ap.parse_args()

    if not a.no_fetch:
        run("fetch", "origin", "--prune")

    base = f"origin/{a.main}"
    refs = run(
        "for-each-ref",
        "--format=%(refname:short)",
        f"refs/remotes/origin/{a.prefix}*",
    ).splitlines()
    refs = [r for r in refs if r and r != "origin/HEAD"]

    if not refs:
        print(f"未发现 origin/{a.prefix}* 临时分支。")
        return

    print(f"基线: {base} @ {short_sha(base)}")
    print("branch | behind(main-only) | ahead(branch-only) | state")
    print("-" * 92)
    for ref in sorted(refs):
        behind, ahead = counts(base, ref)
        print(f"{ref} | {behind:>3} | {ahead:>3} | {classify(behind, ahead)}")

    print("\n说明：ahead+behind 同时非零只表示历史已分叉；若此前采用 squash merge，")
    print("这种状态通常是正常遗留。先 compare，再删除旧 chore 分支，不要重复 merge。")


if __name__ == "__main__":
    main()
