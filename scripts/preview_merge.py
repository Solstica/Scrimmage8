#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config/project.json").read_text(encoding="utf-8"))
MARKER = ".cumcm-preview-worktree"
TEMP_BRANCH_PREFIX = "preview/tmp-"


def run(args, cwd=ROOT, check=True, capture=False):
    kwargs = {"cwd": cwd, "text": True, "check": check, "capture_output": capture}
    if capture:
        kwargs.update(encoding="utf-8", errors="replace")
    return subprocess.run(args, **kwargs)


def _norm(path: Path | str) -> str:
    return str(Path(path).resolve()).replace("\\", "/").lower()


def registered(path: Path) -> bool:
    p = run(["git", "worktree", "list", "--porcelain"], capture=True).stdout
    needle = _norm(path)
    return any(
        line.startswith("worktree ") and line[9:].replace("\\", "/").lower() == needle
        for line in p.splitlines()
    )


def marker_temp_branch(path: Path) -> str | None:
    marker = path / MARKER
    if not marker.exists():
        return None
    for line in marker.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("temp_branch="):
            branch = line.split("=", 1)[1].strip()
            if branch.startswith(TEMP_BRANCH_PREFIX):
                return branch
    return None


def local_branch_exists(branch: str) -> bool:
    return run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
    ).returncode == 0


def delete_temp_branch(branch: str | None) -> None:
    if not branch or not branch.startswith(TEMP_BRANCH_PREFIX):
        return
    if local_branch_exists(branch):
        p = run(["git", "branch", "-D", branch], check=False, capture=True)
        if p.returncode:
            print(f"[WARN] 临时融合分支删除失败：{branch}")
        else:
            print(f"[INFO] 已删除临时融合分支：{branch}")


def detach_preview_branch(path: Path, branch: str) -> None:
    if not path.exists() or not registered(path):
        delete_temp_branch(branch)
        return
    current = run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=path,
        check=False,
        capture=True,
    ).stdout.strip()
    if current == branch:
        p = run(["git", "checkout", "--detach", "HEAD"], cwd=path, check=False, capture=True)
        if p.returncode:
            print(f"[WARN] preview worktree 无法从临时分支脱离：{branch}")
            return
    delete_temp_branch(branch)


def clean_preview(path: Path) -> None:
    """只清理带 preview 标记的目录，并回收可能残留的临时融合分支。"""
    if Path.cwd().resolve() == path.resolve():
        raise SystemExit("不能从待删除的 preview 目录内部执行 --clean；先 cd 到正常 worktree。")
    if path.resolve() == ROOT.resolve():
        raise SystemExit("preview 路径不能等于当前仓库根目录。")

    exists = path.exists()
    is_registered = registered(path)
    stale_branch = marker_temp_branch(path) if exists else None
    if exists and not (path / MARKER).exists():
        raise SystemExit(
            f"拒绝清理没有 {MARKER} 标记的目录：{path}\n"
            "请确认路径；preview 脚本不会删除普通工作目录。"
        )

    if is_registered:
        run(["git", "worktree", "remove", "--force", str(path)], check=False)
    if path.exists():
        if not (path / MARKER).exists():
            raise SystemExit(f"preview worktree 移除后标记异常，拒绝继续删除：{path}")
        shutil.rmtree(path, ignore_errors=False)
    delete_temp_branch(stale_branch)
    run(["git", "worktree", "prune"], check=False)


def ref_exists(ref: str) -> bool:
    return run(["git", "show-ref", "--verify", "--quiet", ref], check=False).returncode == 0


def integration_cfg() -> dict:
    return CFG.get("integration", {})


def owned_roots(module: dict) -> list[str]:
    roots: list[str] = []
    for key in ("path", "task"):
        value = module.get(key)
        if value:
            roots.append(value.rstrip("/"))
    for value in module.get("extra_paths", []):
        if value:
            roots.append(value.rstrip("/"))
    return list(dict.fromkeys(roots))


def is_owned(path: str, module: dict) -> bool:
    path = path.replace("\\", "/")
    return any(path == root or path.startswith(root + "/") for root in owned_roots(module))


def branch_changes(audit_base_ref: str, branch_ref: str):
    p = run(["git", "diff", "--name-status", "-z", f"{audit_base_ref}...{branch_ref}"], capture=True)
    parts = p.stdout.split("\0")
    out = []
    i = 0
    while i < len(parts):
        status = parts[i]
        if not status:
            break
        i += 1
        code = status[0]
        if code in {"R", "C"}:
            old, new = parts[i], parts[i + 1]
            i += 2
            out.append((code, old, new))
        else:
            path = parts[i]
            i += 1
            out.append((code, path, None))
    return out


def audit_ownership(module: dict, audit_base_ref: str):
    branch_ref = f"origin/{module['branch']}"
    changes = branch_changes(audit_base_ref, branch_ref)
    violations: list[str] = []
    for _code, p1, p2 in changes:
        for path in (p1, p2):
            if path and not is_owned(path, module):
                violations.append(path)
    if violations:
        bad = "\n  - ".join(sorted(set(violations)))
        raise RuntimeError(
            f"{module['branch']} 修改了责任域之外的路径：\n  - {bad}\n"
            "请先把误提交迁回正确分支；preview 不自动吞并跨模块改动。"
        )
    return changes


def overlay_branch(module: dict, audit_base_ref: str, preview: Path) -> None:
    branch_ref = f"origin/{module['branch']}"
    changes = audit_ownership(module, audit_base_ref)
    head = run(["git", "rev-parse", branch_ref], capture=True).stdout.strip()
    print(f"[OVERLAY] {module['key']}: {module['branch']} @ {head[:12]} ({len(changes)} changes)")
    for code, p1, p2 in changes:
        if code == "D":
            run(["git", "rm", "-f", "--ignore-unmatch", "--", p1], cwd=preview, check=False)
        elif code == "R":
            run(["git", "rm", "-f", "--ignore-unmatch", "--", p1], cwd=preview, check=False)
            run(["git", "checkout", branch_ref, "--", p2], cwd=preview)
        elif code == "C":
            run(["git", "checkout", branch_ref, "--", p2], cwd=preview)
        else:
            run(["git", "checkout", branch_ref, "--", p1], cwd=preview)


def module_plan(extra_skip: set[str]) -> list[dict]:
    integ = integration_cfg()
    skip = set(integ.get("skip_module_keys", [])) | extra_skip
    modules = [m for m in CFG["modules"] if m.get("active", True)]
    known = {m["key"] for m in modules}
    unknown = extra_skip - known
    if unknown:
        raise SystemExit("--skip 包含未知模块 key: " + ", ".join(sorted(unknown)))
    plan = [m for m in modules if m["key"] not in skip]
    keys = [m["key"] for m in plan]
    if len(keys) != len(set(keys)):
        raise SystemExit("config/project.json 中存在重复模块 key。")
    return sorted(plan, key=lambda x: x["merge_order"])


def cite_audit(preview: Path):
    bib = preview / "modules/70_references/paper/references.tex"
    if not bib.exists():
        print("[WARN] 未找到 references.tex，跳过 cite 审计。")
        return set(), set()
    cite_keys: set[str] = set()
    cite_re = re.compile(r"\\cite\{([^}]+)\}")
    for root in (preview / "modules", preview / "paper"):
        if not root.exists():
            continue
        for tex in root.rglob("*.tex"):
            text = tex.read_text(encoding="utf-8", errors="replace")
            for group in cite_re.findall(text):
                cite_keys.update(key.strip() for key in group.split(",") if key.strip())
    bib_text = bib.read_text(encoding="utf-8", errors="replace")
    bib_keys = set(re.findall(r"\\bibitem\{([^}]+)\}", bib_text))
    missing = cite_keys - bib_keys
    unused = bib_keys - cite_keys
    if missing:
        print("[FAIL] bibliography 缺少正文 cite key:")
        for key in sorted(missing):
            print(" -", key)
    else:
        print(f"[PASS] cite-key 审计：正文 {len(cite_keys)} 个 key 均存在。")
    if unused:
        print("[WARN] bibliography 中未被正文使用的条目:")
        for key in sorted(unused):
            print(" -", key)
    return missing, unused


def compose_commit(preview: Path) -> None:
    run(["git", "add", "-A"], cwd=preview)
    if not run(["git", "diff", "--cached", "--quiet"], cwd=preview, check=False).returncode:
        print("[INFO] overlay 与 compose base 无文件差异，无需创建临时提交。")
        return
    if run(["git", "diff", "--cached", "--check"], cwd=preview, check=False).returncode:
        raise RuntimeError("git diff --cached --check 发现空白错误。")
    run([
        "git", "-c", "user.name=CUMCM Preview", "-c", "user.email=preview@local.invalid",
        "commit", "-m", "preview: compose owned module snapshots"
    ], cwd=preview)


def build(preview: Path, no_build: bool) -> None:
    if no_build:
        print("[INFO] --no-build：仅完成 overlay 与静态审计。")
        return
    paper = preview / "paper"
    if shutil.which("latexmk"):
        run(["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=paper)
    elif shutil.which("xelatex"):
        run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=paper)
        run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=paper)
    else:
        print("[WARN] 未找到 latexmk/xelatex，仅完成临时拼装。")


def prepare_preview_path(preview: Path) -> None:
    """回收旧 preview；无标记目录一律拒绝删除。"""
    if preview.resolve() == ROOT.resolve():
        raise SystemExit("preview 路径不能等于当前仓库根目录。")
    exists = preview.exists()
    is_registered = registered(preview)
    if not exists and not is_registered:
        return

    marker = preview / MARKER
    if exists and marker.exists():
        print(f"[INFO] 回收上次 preview：{preview}")
        clean_preview(preview)
        return

    if not exists and is_registered:
        print(f"[INFO] 清理已失效的 preview worktree 注册：{preview}")
        run(["git", "worktree", "remove", "--force", str(preview)], check=False)
        run(["git", "worktree", "prune"], check=False)
        return

    raise SystemExit(
        f"目标 preview 路径已存在但没有 {MARKER} 标记：{preview}\n"
        "为避免误删普通工作目录，本脚本拒绝自动清理；请人工确认后换路径或删除。"
    )


def make_temp_branch() -> str:
    return f"{TEMP_BRANCH_PREFIX}{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--strict", action="store_true", help="缺任一计划分支即失败")
    ap.add_argument("--strict-preflight", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--preview-dir")
    ap.add_argument("--base-branch", help="覆盖 config.integration.base_branch")
    ap.add_argument("--skip", action="append", default=[], help="额外跳过模块 key，可重复")
    a = ap.parse_args()

    preview = Path(a.preview_dir).resolve() if a.preview_dir else (ROOT.parent / (ROOT.name + "-preview")).resolve()
    if a.clean:
        clean_preview(preview)
        print("preview 已清理")
        return
    if (ROOT / MARKER).exists():
        raise SystemExit("当前位于 preview worktree，请回到正常 worktree。")

    run(["git", "fetch", "origin", "--prune"])
    prepare_preview_path(preview)

    integ = integration_cfg()
    compose_base = a.base_branch or integ.get("base_branch") or CFG.get("default_base", "main")
    audit_base = CFG.get("default_base", "main")
    compose_ref = f"origin/{compose_base}"
    audit_ref = f"origin/{audit_base}"
    for label, ref in (("总装底座", compose_ref), ("责任域审计基线", audit_ref)):
        if not ref_exists(f"refs/remotes/{ref}"):
            raise SystemExit(f"远端缺少{label} {ref}")

    plan = module_plan(set(a.skip))
    print("=== preview overlay plan ===")
    print("compose base:", compose_ref)
    print("audit base:  ", audit_ref)
    for m in plan:
        print(f"  {m['merge_order']:>3}  {m['key']:<12} {m['branch']}")

    temp_branch = make_temp_branch()
    print("[INFO] temporary integration branch:", temp_branch)
    try:
        run(["git", "worktree", "add", "-b", temp_branch, str(preview), compose_ref])
    except Exception:
        delete_temp_branch(temp_branch)
        raise

    (preview / MARKER).write_text(
        "temporary full-paper preview\n" + f"temp_branch={temp_branch}\n",
        encoding="utf-8",
    )
    try:
        for module in plan:
            ref = f"refs/remotes/origin/{module['branch']}"
            if not ref_exists(ref):
                msg = f"远端缺少 {module['branch']}"
                if a.strict:
                    raise RuntimeError(msg)
                print("[WARN]", msg, "，本次跳过")
                continue
            overlay_branch(module, audit_ref, preview)

        compose_commit(preview)
        missing, _unused = cite_audit(preview)
        if missing:
            raise RuntimeError("正文引用与 references.tex 不一致。")

        pre = preview / "scripts/final_preflight.py"
        if pre.exists():
            p = run([sys.executable, str(pre)], cwd=preview, check=False)
            if p.returncode and a.strict_preflight:
                raise RuntimeError("final_preflight 未通过。")
        build(preview, a.no_build)
        if pre.exists() and not a.no_build:
            p = run([sys.executable, str(pre), "--post-build"], cwd=preview, check=False)
            if p.returncode and a.strict_preflight:
                raise RuntimeError("final_preflight --post-build 未通过。")

        pdf = preview / "paper" / "main.pdf"
        if pdf.exists():
            print("PDF:", pdf)
            if not a.no_open:
                try:
                    if os.name == "nt":
                        os.startfile(pdf)  # type: ignore[attr-defined]
                    elif sys.platform == "darwin":
                        run(["open", str(pdf)], check=False)
                    else:
                        run(["xdg-open", str(pdf)], check=False)
                except Exception as exc:
                    print("[WARN] 无法自动打开 PDF:", exc)
        print("[PASS] preview overlay completed:", preview)
    except Exception:
        print(f"\n临时目录保留用于检查：{preview}")
        raise
    finally:
        # 保留 preview worktree/PDF 供查看，但立即让它脱离临时融合分支并删除该分支。
        # 因此任何 preview 提交都不会落到 q1/q2/.../evaluation 等责任分支上。
        detach_preview_branch(preview, temp_branch)


if __name__ == "__main__":
    main()
