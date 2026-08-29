#!/usr/bin/env python3
from __future__ import annotations

"""Compatibility wrapper for preview ownership auditing.

The historical implementation is kept in preview_merge_core.py. This wrapper
filters merge-base-only paths that are already identical to the current audit
base, so stale history does not trigger false responsibility violations.
Actual final-state differences remain visible to the original HARD audit.
"""

import preview_merge_core as _core

# Re-export the original module API so existing callers keep working.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_original_branch_changes = _core.branch_changes


def _path_differs_from_base(audit_base_ref: str, branch_ref: str, path: str) -> bool:
    p = _core.run(
        ["git", "diff", "--quiet", audit_base_ref, branch_ref, "--", path],
        check=False,
    )
    if p.returncode not in {0, 1}:
        raise RuntimeError(
            f"无法比较责任域路径最终状态：{path} "
            f"({audit_base_ref} vs {branch_ref}, rc={p.returncode})"
        )
    return p.returncode == 1


def branch_changes(audit_base_ref: str, branch_ref: str):
    """Return branch-introduced changes that still differ from audit base.

    The original three-dot diff is retained to identify branch-introduced paths.
    A second final-state comparison removes paths that were historically touched
    on the branch but are now byte-for-byte/tree-state identical to the current
    audit base. This prevents stale merged/reverted history from being replayed
    or reported as an ownership violation.
    """
    raw = _original_branch_changes(audit_base_ref, branch_ref)
    effective = []
    ignored = []
    for item in raw:
        _code, p1, p2 = item
        paths = [p for p in (p1, p2) if p]
        if any(_path_differs_from_base(audit_base_ref, branch_ref, p) for p in paths):
            effective.append(item)
        else:
            ignored.extend(paths)

    if ignored:
        print(
            f"[INFO] {branch_ref}: 忽略 {len(set(ignored))} 个已与 {audit_base_ref} "
            "最终状态一致的历史差异"
        )
    return effective


# Patch the core global used by audit_ownership()/overlay_branch().
_core.branch_changes = branch_changes
globals()["branch_changes"] = branch_changes


if __name__ == "__main__":
    _core.main()
