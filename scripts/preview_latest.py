#!/usr/bin/env python3
"""Windows/macOS/Linux 一键运行远端 feature/shared 上的最新版全文 overlay。

本脚本可从同一 Git 仓库的任意 worktree 启动。它区分：
- CALLER_ROOT：用户执行 `git paper-merge` 的 worktree；
- COMMON_ROOT：所有 worktree 共享的主仓库根目录。

controller / preview 固定生成在 COMMON_ROOT 旁边。全文总装只允许在独立临时
worktree 中发生，运行前后会校验 CALLER_ROOT 的分支和 HEAD 未被改变。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CTRL_MARKER = ".cumcm-preview-controller"
_GIT_WORKTREE_ENV_KEYS = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
}


def clean_git_env() -> dict[str, str]:
    """移除 git alias 可能传入的 worktree 定向变量，确保 cwd 决定 Git 上下文。"""
    env = os.environ.copy()
    for key in _GIT_WORKTREE_ENV_KEYS:
        env.pop(key, None)
    return env


def git_out(args, cwd: Path | None = None, check: bool = True) -> str:
    p = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
        encoding="utf-8",
        errors="replace",
        env=clean_git_env(),
    )
    return p.stdout.strip()


def resolve_repo_roots() -> tuple[Path, Path, Path]:
    """返回 (execution_root, common_git_dir, common_repo_root)。"""
    current = Path(git_out(["git", "rev-parse", "--show-toplevel"])).resolve()
    raw_common = Path(git_out(["git", "rev-parse", "--git-common-dir"], cwd=current))
    common_git = raw_common if raw_common.is_absolute() else (current / raw_common)
    common_git = common_git.resolve()
    common_root = common_git.parent.resolve()
    if not (common_root / ".git").exists():
        raise SystemExit(
            "无法由 git common-dir 解析主仓库根目录。\n"
            f"execution root: {current}\n"
            f"common git dir: {common_git}\n"
            f"candidate root: {common_root}"
        )
    return current, common_git, common_root


EXECUTION_ROOT, COMMON_GIT_DIR, COMMON_ROOT = resolve_repo_roots()


def run(args, cwd: Path = COMMON_ROOT, check: bool = True):
    return subprocess.run(args, cwd=cwd, text=True, check=check, env=clean_git_env())


def registered(path: Path) -> bool:
    p = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=COMMON_ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
        env=clean_git_env(),
    )
    needle = str(path.resolve()).replace("\\", "/").lower()
    return any(
        line.startswith("worktree ")
        and line[9:].replace("\\", "/").lower() == needle
        for line in p.stdout.splitlines()
    )


def common_git_of(root: Path) -> Path:
    raw = Path(git_out(["git", "rev-parse", "--git-common-dir"], cwd=root))
    return (raw if raw.is_absolute() else root / raw).resolve()


def worktree_state(root: Path) -> tuple[str, str]:
    branch = git_out(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=root,
        check=False,
    )
    head = git_out(["git", "rev-parse", "HEAD"], cwd=root)
    return branch or "(detached)", head


def legacy_controller_is_safe(path: Path) -> bool:
    """识别旧版 paper-merge 留下的、尚未带 marker 的临时 controller。

    只允许回收同时满足以下条件的 worktree：
    1. 属于当前仓库；
    2. 工作区完全干净；
    3. HEAD 是当前 origin/feature/shared 的祖先。

    这样可以兼容旧版 controller，又不会把用户长期 worktree 当临时目录删除。
    """
    if not path.exists() or not registered(path):
        return False
    try:
        if common_git_of(path) != COMMON_GIT_DIR:
            return False
        if git_out(["git", "status", "--porcelain"], cwd=path):
            return False
        head = git_out(["git", "rev-parse", "HEAD"], cwd=path)
        return (
            run(
                ["git", "merge-base", "--is-ancestor", head, "origin/feature/shared"],
                cwd=COMMON_ROOT,
                check=False,
            ).returncode
            == 0
        )
    except Exception:
        return False


def remove_tree_with_retries(path: Path, attempts: int = 6) -> None:
    """非交互删除临时 controller；Windows 文件句柄短暂占用时做有限重试。"""
    last_error: OSError | None = None
    for i in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            if i + 1 < attempts:
                time.sleep(0.20 * (i + 1))
    raise RuntimeError(f"无法删除临时 preview controller：{path}\nlast error: {last_error}")


def prune_worktree_metadata() -> None:
    """立即清理已删除临时 worktree 的 Git 元数据，不等待默认过期时间。"""
    run(["git", "worktree", "prune", "--expire", "now"], check=False)


def clean_controller(path: Path) -> None:
    """回收 preview controller；避免 Git for Windows 在删除失败时进入交互式重试提示。"""
    exists = path.exists()
    is_registered = registered(path)
    marker = path / CTRL_MARKER

    if exists and not marker.exists():
        if is_registered and legacy_controller_is_safe(path):
            print(f"[INFO] 回收旧版无标记 preview controller：{path}")
            remove_tree_with_retries(path)
            prune_worktree_metadata()
            return
        raise SystemExit(
            f"拒绝清理无控制标记的普通目录或 worktree：{path}\n"
            "该目录未通过旧版 controller 安全识别；请人工确认后处理。"
        )

    # 标记明确的 controller 不再调用 `git worktree remove` 直接递归删除。
    # Git for Windows 在目录被杀毒软件/索引器短暂占用时会进入
    # "Should I try again? (y/n)" 交互，导致 git paper-merge 看似挂起。
    # 先由 Python 非交互重试删除目录，再立即 prune 回收 worktree 元数据。
    if exists:
        if not marker.exists():
            raise SystemExit(f"controller 标记丢失，拒绝继续删除：{path}")
        remove_tree_with_retries(path)

    if is_registered or not path.exists():
        prune_worktree_metadata()


def open_pdf(pdf: Path) -> None:
    """在 controller 已回收后，从稳定目录启动系统 PDF 查看器。"""
    try:
        if os.name == "nt":
            os.startfile(str(pdf))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pdf)], cwd=COMMON_ROOT, env=clean_git_env())
        else:
            subprocess.Popen(["xdg-open", str(pdf)], cwd=COMMON_ROOT, env=clean_git_env())
    except Exception as exc:
        print("[WARN] 无法自动打开 PDF:", exc)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--preview-dir",
        default=str(COMMON_ROOT.parent / (COMMON_ROOT.name + "-paper-preview")),
    )
    ap.add_argument(
        "--controller-dir",
        default=str(COMMON_ROOT.parent / (COMMON_ROOT.name + "-preview-controller")),
    )
    ap.add_argument(
        "--caller-root",
        help="实际调用 git paper-merge 的 worktree；由仓库级启动器传入",
    )
    ap.add_argument(
        "--fast",
        action="store_true",
        help="只 overlay 论文相关文件；默认调用完整 preview_merge.py",
    )
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--open", action="store_true", help="生成 PDF 后自动打开")
    a = ap.parse_args()

    caller = Path(a.caller_root).resolve() if a.caller_root else EXECUTION_ROOT
    if common_git_of(caller) != COMMON_GIT_DIR:
        raise SystemExit(f"caller worktree 不属于当前仓库：{caller}")
    caller_before = worktree_state(caller)

    preview = Path(a.preview_dir).resolve()
    ctrl = Path(a.controller_dir).resolve()
    forbidden = {caller, EXECUTION_ROOT, COMMON_ROOT}
    if preview in forbidden or ctrl in forbidden or preview == ctrl:
        raise SystemExit(
            "preview/controller 路径不得等于调用者 worktree、执行根目录或主仓库根目录，且二者不得相同。"
        )

    print("[INFO] caller worktree: ", caller)
    print("[INFO] caller branch:   ", caller_before[0])
    print("[INFO] common repo root:", COMMON_ROOT)

    run(["git", "fetch", "origin", "--prune"])
    clean_controller(ctrl)

    run(["git", "worktree", "add", "--detach", str(ctrl), "origin/feature/shared"])
    (ctrl / CTRL_MARKER).write_text("temporary preview controller\n", encoding="utf-8")

    pdf_to_open: Path | None = None
    try:
        script = "preview_fast.py" if a.fast else "preview_merge.py"
        cmd = [
            sys.executable,
            str(ctrl / "scripts" / script),
            "--preview-dir",
            str(preview),
            "--base-branch",
            "feature/paper-shell",
            "--strict",
            "--strict-preflight",
            # 子进程 cwd 位于临时 controller。禁止它在此处启动 PDF 查看器，
            # 否则 Windows 查看器可能继承 controller 作为当前目录并锁住目录。
            "--no-open",
        ]
        if a.no_build:
            cmd.append("--no-build")

        mode = "fast" if a.fast else "full"
        print(f"[INFO] latest preview mode: {mode}")
        print("[INFO] controller: origin/feature/shared")
        print("[INFO] compose base: origin/feature/paper-shell")
        print("[INFO] preview dir:", preview)

        # 以清理后的 Git 环境启动 controller，防止调用者 worktree 的 GIT_* 变量泄漏。
        run(cmd, cwd=ctrl)

        pdf = preview / "paper" / "main.pdf"
        if pdf.exists():
            print("PDF:", pdf)
            if a.open:
                pdf_to_open = pdf
        else:
            print(f"[INFO] 拼装完成，未生成 PDF：{preview}")
    finally:
        # 先回收 controller，再打开 PDF。这样 PDF 查看器不会继承待删除目录为 cwd。
        clean_controller(ctrl)
        caller_after = worktree_state(caller)
        if caller_after != caller_before:
            raise RuntimeError(
                "preview 检测到调用者 worktree 的分支或 HEAD 被改变。\n"
                f"before: branch={caller_before[0]}, HEAD={caller_before[1]}\n"
                f"after:  branch={caller_after[0]}, HEAD={caller_after[1]}\n"
                "全文融合必须完全发生在独立临时 worktree 中。"
            )

    if pdf_to_open is not None:
        open_pdf(pdf_to_open)


if __name__ == "__main__":
    main()
