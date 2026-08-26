#!/usr/bin/env python3
from __future__ import annotations

"""Fast paper-preview mode.

Only paper-relevant files are overlaid into the temporary detached worktree.
Heavy result archives, editable plotting projects and logs are skipped, while
source code is kept because some competitions require complete code in the PDF appendix.
The responsibility branches themselves are never modified.
"""

from pathlib import Path

import preview_merge as pm

_TEXT_SUFFIXES = {".tex", ".sty", ".cls", ".md", ".py", ".sh", ".json", ".txt", ".csv"}


def preview_excluded(path: str | None) -> bool:
    if not path:
        return False
    p = path.replace("\\", "/")
    parts = p.split("/")

    if any("COMPLETE_ARCHIVE_" in part or "FULL_ARCHIVE_" in part for part in parts):
        return True
    if "/results/" in p or "/records/" in p:
        return True
    if "/figures/editable/" in p or p.lower().endswith((".opju", ".xlsx", ".xlsm")):
        return True
    if p.lower().endswith((".log", ".log.err", ".tmp")):
        return True
    return False


def fast_overlay_branch(module: dict, audit_base_ref: str, preview: Path) -> None:
    branch_ref = f"origin/{module['branch']}"
    changes = pm.audit_ownership(module, audit_base_ref)
    kept = []
    for item in changes:
        _code, p1, p2 = item
        if preview_excluded(p1) or preview_excluded(p2):
            continue
        kept.append(item)

    head = pm.run(["git", "rev-parse", branch_ref], capture=True).stdout.strip()
    print(
        f"[FAST OVERLAY] {module['key']}: {module['branch']} @ {head[:12]} "
        f"({len(kept)}/{len(changes)} paper-relevant changes)"
    )

    for code, p1, p2 in kept:
        if code == "D":
            pm.run(["git", "rm", "-f", "--ignore-unmatch", "--", p1], cwd=preview, check=False)
        elif code == "R":
            pm.run(["git", "rm", "-f", "--ignore-unmatch", "--", p1], cwd=preview, check=False)
            pm.run(["git", "checkout", branch_ref, "--", p2], cwd=preview)
        elif code == "C":
            pm.run(["git", "checkout", branch_ref, "--", p2], cwd=preview)
        else:
            pm.run(["git", "checkout", branch_ref, "--", p1], cwd=preview)


def _strip_trailing_ws_bytes(data: bytes) -> bytes:
    chunks = data.splitlines(keepends=True)
    if not chunks:
        return data.rstrip(b" \t")
    out: list[bytes] = []
    for line in chunks:
        if line.endswith(b"\r\n"):
            body, ending = line[:-2], b"\r\n"
        elif line.endswith(b"\n"):
            body, ending = line[:-1], b"\n"
        elif line.endswith(b"\r"):
            body, ending = line[:-1], b"\r"
        else:
            body, ending = line, b""
        out.append(body.rstrip(b" \t") + ending)
    return b"".join(out)


def fast_compose_commit(preview: Path) -> None:
    pm.run(["git", "add", "-A"], cwd=preview)
    changed = pm.run(
        ["git", "diff", "--cached", "--name-only", "-z", "HEAD"],
        cwd=preview,
        capture=True,
    ).stdout.split("\0")

    cleaned = 0
    for rel in changed:
        if not rel:
            continue
        path = preview / rel
        if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        old = path.read_bytes()
        new = _strip_trailing_ws_bytes(old)
        if new != old:
            path.write_bytes(new)
            cleaned += 1

    if cleaned:
        print(f"[FAST CLEAN] 临时清理 {cleaned} 个文本文件的行尾空白")
        pm.run(["git", "add", "-A"], cwd=preview)

    if pm.run(["git", "diff", "--cached", "--quiet"], cwd=preview, check=False).returncode:
        pm.run([
            "git", "-c", "user.name=CUMCM Preview", "-c", "user.email=preview@local.invalid",
            "commit", "-m", "preview: compose owned module snapshots"
        ], cwd=preview)


def main() -> None:
    pm.overlay_branch = fast_overlay_branch
    pm.compose_commit = fast_compose_commit
    pm.main()


if __name__ == "__main__":
    main()
