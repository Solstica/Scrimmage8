#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import zipfile
from collections import deque
from pathlib import Path

DEFAULT_CONFIG = Path("config/submission.json")
IMAGE_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".webp")
AUX_SUFFIXES = (
    ".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out",
    ".synctex.gz", ".toc", ".xdv", ".nav", ".snm", ".vrb",
)
# Files under paper/ that are part of the compilable paper shell even when they
# are not reached through \input/\includegraphics. Local font files belong here:
# fontspec commonly refers to them through Path=/BoldFont= or \IfFileExists,
# which is not a normal TeX file command and therefore is not discovered by the
# dependency regexes below.
SUPPORT_EXTS = {
    ".tex", ".sty", ".cls", ".bst", ".bib", ".cfg", ".def", ".clo",
    ".otf", ".ttf", ".ttc",
}
DIRECT_FILE_COMMANDS = ("lstinputlisting", "VerbatimInput", "includepdf")
TEXT_COMMAND_RE = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}")
BIB_RE = re.compile(r"\\bibliography\s*\{([^{}]+)\}")
ADDBIB_RE = re.compile(r"\\addbibresource(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}")
DIRECT_FILE_RE = re.compile(
    r"\\(?:" + "|".join(re.escape(x) for x in DIRECT_FILE_COMMANDS) + r")"
    r"(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}"
)
INPUTMINTED_RE = re.compile(
    r"\\inputminted(?:\s*\[[^\]]*\])?\s*\{[^{}]*\}\s*\{([^{}]+)\}"
)
COMMENT_RE = re.compile(r"(?<!\\)%.*$")


class BuildError(RuntimeError):
    pass


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(root: Path, path: Path) -> dict:
    config_path = path if path.is_absolute() else root / path
    if not config_path.exists():
        raise BuildError(f"submission config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def rel(root: Path, path: Path) -> Path:
    return path.resolve().relative_to(root.resolve())


def is_within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def strip_tex_comments(text: str) -> str:
    return "\n".join(COMMENT_RE.sub("", line) for line in text.splitlines())


def should_exclude(root: Path, path: Path, patterns: list[str]) -> bool:
    try:
        rp = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return True
    name = path.name
    if any(name.endswith(s) for s in AUX_SUFFIXES):
        return True
    return any(fnmatch.fnmatch(rp, pat) or fnmatch.fnmatch(name, pat) for pat in patterns)


def resolve_project_macro(root: Path, raw: str) -> Path | None:
    token = raw.strip()
    if token.startswith((r"\ProjectRoot/", r"\ProjectRoot\\", r"\ProjectRoot")):
        rest = token[len(r"\ProjectRoot"):].lstrip("/\\")
        return (root / rest).resolve()
    return None


def candidate_bases(root: Path, compile_dir: Path, current: Path) -> list[Path]:
    return [compile_dir, current.parent, root]


def resolve_file(root: Path, compile_dir: Path, current: Path, raw: str, kind: str) -> Path | None:
    raw = raw.strip().strip('"').strip("'")
    if not raw or any(mark in raw for mark in ("#", r"\jobname")):
        return None

    macro = resolve_project_macro(root, raw)
    raw_path = Path(raw) if macro is None else macro
    if macro is not None:
        candidates = [macro]
    elif raw_path.is_absolute():
        candidates = [raw_path]
    else:
        candidates = [base / raw_path for base in candidate_bases(root, compile_dir, current)]

    ext_candidates: list[Path] = []
    for candidate in candidates:
        if kind == "tex":
            ext_candidates.append(candidate)
            if candidate.suffix == "":
                ext_candidates.append(candidate.with_suffix(".tex"))
        elif kind == "image":
            if candidate.suffix:
                ext_candidates.append(candidate)
            else:
                ext_candidates.extend(candidate.with_suffix(ext) for ext in IMAGE_EXTS)
        elif kind == "bib":
            ext_candidates.append(candidate)
            if candidate.suffix == "":
                ext_candidates.append(candidate.with_suffix(".bib"))
        else:
            ext_candidates.append(candidate)

    for candidate in ext_candidates:
        candidate = candidate.resolve()
        if candidate.exists() and candidate.is_file() and is_within(root, candidate):
            return candidate
    return None


def dependencies_from_tex(root: Path, compile_dir: Path, tex_path: Path) -> tuple[list[tuple[Path, bool]], list[str]]:
    text = strip_tex_comments(tex_path.read_text(encoding="utf-8", errors="ignore"))
    found: list[tuple[Path, bool]] = []
    unresolved: list[str] = []

    for raw in TEXT_COMMAND_RE.findall(text):
        path = resolve_file(root, compile_dir, tex_path, raw, "tex")
        if path:
            found.append((path, True))
        else:
            unresolved.append(f"{rel(root, tex_path)}: input/include -> {raw}")

    for raw in GRAPHICS_RE.findall(text):
        path = resolve_file(root, compile_dir, tex_path, raw, "image")
        if path:
            found.append((path, False))
        else:
            unresolved.append(f"{rel(root, tex_path)}: includegraphics -> {raw}")

    for raw in DIRECT_FILE_RE.findall(text):
        path = resolve_file(root, compile_dir, tex_path, raw, "direct")
        if path:
            found.append((path, path.suffix.lower() == ".tex"))
        else:
            unresolved.append(f"{rel(root, tex_path)}: direct file -> {raw}")

    for raw in INPUTMINTED_RE.findall(text):
        path = resolve_file(root, compile_dir, tex_path, raw, "direct")
        if path:
            found.append((path, False))
        else:
            unresolved.append(f"{rel(root, tex_path)}: inputminted -> {raw}")

    for group in BIB_RE.findall(text):
        for raw in [x.strip() for x in group.split(",") if x.strip()]:
            path = resolve_file(root, compile_dir, tex_path, raw, "bib")
            if path:
                found.append((path, False))
            else:
                unresolved.append(f"{rel(root, tex_path)}: bibliography -> {raw}")

    for raw in ADDBIB_RE.findall(text):
        path = resolve_file(root, compile_dir, tex_path, raw, "bib")
        if path:
            found.append((path, False))
        else:
            unresolved.append(f"{rel(root, tex_path)}: addbibresource -> {raw}")

    return found, unresolved


def paper_support_files(root: Path, entry: Path, exclude: list[str]) -> set[Path]:
    files: set[Path] = set()
    for path in entry.parent.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORT_EXTS and not should_exclude(root, path, exclude):
            files.add(path.resolve())
    return files


def discover_tex_dependencies(root: Path, entry: Path, exclude: list[str]) -> tuple[set[Path], set[Path], list[str]]:
    compile_dir = entry.parent.resolve()
    included: set[Path] = paper_support_files(root, entry, exclude)
    included.add(entry.resolve())
    queue = deque(path for path in included if path.suffix.lower() == ".tex")
    scanned: set[Path] = set()
    unresolved: list[str] = []

    while queue:
        current = queue.popleft()
        if current in scanned:
            continue
        scanned.add(current)
        deps, missing = dependencies_from_tex(root, compile_dir, current)
        unresolved.extend(missing)
        for path, scan_as_tex in deps:
            if should_exclude(root, path, exclude):
                continue
            included.add(path)
            if scan_as_tex and path.suffix.lower() == ".tex" and path not in scanned:
                queue.append(path)

    module_roots: set[Path] = set()
    for path in included:
        parts = rel(root, path).parts
        if len(parts) >= 2 and parts[0] == "modules":
            module_roots.add(root / parts[0] / parts[1])
    return included, module_roots, unresolved


def copy_file(root: Path, staging: Path, source: Path) -> None:
    target = staging / rel(root, source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_tree_filtered(root: Path, staging: Path, source_dir: Path, exclude: list[str]) -> int:
    count = 0
    if not source_dir.exists():
        return count
    for path in source_dir.rglob("*"):
        if not path.is_file() or should_exclude(root, path, exclude):
            continue
        copy_file(root, staging, path)
        count += 1
    return count


def copy_glob(root: Path, staging: Path, pattern: str, exclude: list[str]) -> int:
    count = 0
    for path in root.glob(pattern):
        if path.is_file() and not should_exclude(root, path, exclude):
            copy_file(root, staging, path)
            count += 1
        elif path.is_dir():
            count += copy_tree_filtered(root, staging, path, exclude)
    return count


def disable_toc(staging: Path, entry_rel: Path) -> None:
    settings = staging / entry_rel.parent / "settings.tex"
    if settings.exists():
        text = settings.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"\\showtoctrue\b", r"\\showtocfalse", text)
        settings.write_text(text, encoding="utf-8")

    entry = staging / entry_rel
    if entry.exists():
        text = entry.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(
            r"(?m)^(\s*)\\tableofcontents(\s*(?:%.*)?)$",
            r"\1% [submission] \\tableofcontents\2",
            text,
        )
        entry.write_text(text, encoding="utf-8")


def run_compile(staging: Path, entry_rel: Path, latexmk: str) -> Path:
    paper_dir = (staging / entry_rel.parent).resolve()
    entry_name = entry_rel.name
    exe = shutil.which(latexmk) or latexmk
    cmd = [exe, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", entry_name]
    print("[submission] compile:", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, cwd=paper_dir, check=False)
    except FileNotFoundError as exc:
        raise BuildError(f"latexmk not found ({latexmk}). Install TeX Live/latexmk or run with --no-compile.") from exc
    if proc.returncode != 0:
        raise BuildError("staging compilation failed; inspect the first LaTeX error above")
    pdf = paper_dir / (Path(entry_name).stem + ".pdf")
    if not pdf.exists():
        raise BuildError(f"compile succeeded but PDF missing: {pdf}")
    return pdf


def remove_aux(staging: Path) -> None:
    for path in list(staging.rglob("*")):
        if path.is_file() and any(path.name.endswith(suffix) for suffix in AUX_SUFFIXES):
            path.unlink(missing_ok=True)


def write_submission_readme(staging: Path, entry_rel: Path, module_roots: set[Path], root: Path) -> None:
    modules = sorted(rel(root, path).as_posix() for path in module_roots)
    lines = [
        "CUMCM submission package",
        "",
        "Paper source keeps the repository's original main.tex + \\input{} structure.",
        "The table of contents is disabled only in this staging copy.",
        "",
        "Compile:",
        f"  cd {entry_rel.parent.as_posix()}",
        f"  latexmk -xelatex -interaction=nonstopmode -halt-on-error {entry_rel.name}",
        "",
        "Included problem/module roots:",
    ]
    lines.extend(f"  - {module}" for module in modules)
    lines.extend([
        "",
        "Module code/ contains the formal code selected by the repository convention.",
        "Raw/external data, results/, docs/, work/, Git metadata and repository audit scripts are excluded by default.",
        "Add indispensable small data or shared runtime files through config/submission.json -> extra_include.",
        "",
    ])
    (staging / "README.txt").write_text("\n".join(lines), encoding="utf-8")


def human_mb(size: int) -> float:
    return size / (1024 * 1024)


def report_files(staging: Path, cfg: dict) -> None:
    files = [path for path in staging.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    print(f"[submission] staging files={len(files)} uncompressed={human_mb(total):.2f} MiB")
    print("[submission] largest files:")
    for path in sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:15]:
        print(f"  {human_mb(path.stat().st_size):7.2f} MiB  {path.relative_to(staging).as_posix()}")

    raster_warn = int(float(cfg.get("warn_raster_mb", 1.0)) * 1024 * 1024)
    vector_warn = int(float(cfg.get("warn_vector_mb", 0.5)) * 1024 * 1024)
    for path in files:
        ext = path.suffix.lower()
        size = path.stat().st_size
        if ext in {".png", ".jpg", ".jpeg", ".webp"} and size > raster_warn:
            print(f"[submission][WARN] raster > {cfg.get('warn_raster_mb', 1.0)} MiB: {path.relative_to(staging)}")
        if ext in {".pdf", ".svg", ".eps"} and path.name != "final.pdf" and size > vector_warn:
            print(f"[submission][WARN] vector/figure > {cfg.get('warn_vector_mb', 0.5)} MiB: {path.relative_to(staging)}")


def make_zip(staging: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a CUMCM submission staging directory from actual TeX dependencies while preserving repository-relative paths."
    )
    parser.add_argument("--project", type=Path, default=None, help="repository root; default = script parent")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--no-compile", action="store_true", help="skip latexmk and final.pdf generation")
    parser.add_argument("--dry-run", action="store_true", help="discover dependencies and report only")
    parser.add_argument("--max-mb", type=float, default=None, help="override ZIP hard size limit")
    args = parser.parse_args()

    root = (args.project or repo_root_from_script()).expanduser().resolve()
    cfg = load_config(root, args.config)
    entry_rel = Path(cfg.get("entry_tex", "paper/main.tex"))
    entry = (root / entry_rel).resolve()
    if not entry.exists():
        raise BuildError(f"entry TeX not found: {entry}")

    exclude = list(cfg.get("exclude", []))
    deps, module_roots, unresolved = discover_tex_dependencies(root, entry, exclude)
    if unresolved:
        print("[submission][ERROR] unresolved TeX dependencies:")
        for item in unresolved:
            print("  -", item)
        raise BuildError("dependency scan failed. Fix paths or add unsupported resources with extra_include.")

    print(f"[submission] discovered {len(deps)} referenced/support files")
    print("[submission] referenced module roots:")
    for path in sorted(module_roots):
        print("  -", rel(root, path).as_posix())
    if args.dry_run:
        return 0

    staging = (root / cfg.get("staging_dir", "submission")).resolve()
    if staging == root or not is_within(root, staging):
        raise BuildError("staging_dir must be a child of the repository root")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    for path in sorted(deps):
        copy_file(root, staging, path)

    if cfg.get("include_module_code", True):
        for module_root in module_roots:
            copy_tree_filtered(root, staging, module_root / "code", exclude)

    if cfg.get("include_root_requirements", True):
        for name in ("requirements.txt", "environment.yml", "pyproject.toml"):
            path = root / name
            if path.exists() and path.is_file():
                copy_file(root, staging, path)

    for pattern in cfg.get("extra_include", []):
        copy_glob(root, staging, pattern, exclude)

    disable_toc(staging, entry_rel)
    write_submission_readme(staging, entry_rel, module_roots, root)

    compile_enabled = bool(cfg.get("compile", True)) and not args.no_compile
    if compile_enabled:
        pdf = run_compile(staging, entry_rel, str(cfg.get("latexmk", "latexmk")))
        if cfg.get("include_final_pdf", True):
            final_pdf = staging / str(cfg.get("final_pdf_name", "final.pdf"))
            shutil.copy2(pdf, final_pdf)
        pdf.unlink(missing_ok=True)

    remove_aux(staging)
    report_files(staging, cfg)

    zip_path = (root / cfg.get("zip_name", "submission.zip")).resolve()
    make_zip(staging, zip_path)
    zip_mb = human_mb(zip_path.stat().st_size)
    target = float(cfg.get("target_zip_mb", 18.0))
    hard = float(args.max_mb if args.max_mb is not None else cfg.get("hard_zip_mb", 20.0))
    print(f"[submission] zip={zip_path.relative_to(root)} size={zip_mb:.2f} MiB")
    if zip_mb > hard:
        print(f"[submission][FAIL] ZIP exceeds hard limit {hard:.2f} MiB. Reduce large figures or extra files.")
        return 2
    if zip_mb > target:
        print(f"[submission][WARN] ZIP exceeds target {target:.2f} MiB but remains below hard limit.")
    else:
        print(f"[submission][PASS] ZIP is within target {target:.2f} MiB.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"[submission][FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
