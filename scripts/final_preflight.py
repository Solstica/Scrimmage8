#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")

# 这些词不是数学禁词，但在多次终稿中往往来自内部讨论而非正式表述。
INTERNAL_PROSE = (
    "物理口径",
    "统计口径",
    "证据边界",
    "统一链路",
    "机制链",
    "层级结构",
    "柔性释放",
    "柔性替代",
    "基础的量化参考",
    "严格 Cost 区间",
    "严格闭合",
)

# 常见的工程/调试英文残留。公认缩写、附件字段和英文全称不在此列。
ENGLISH_RESIDUES = (
    "Cost-only",
    "final-pool",
    "Legal placements",
    "Root objective",
    "（active）",
    "(active)",
    "Exact 校准",
)

PAPER_VARIANT_RE = re.compile(
    r"(?:^|[_-])(?:final\d*|v\d+|old\d*|backup\d*|copy\d*|副本)(?:[_-]|\.)",
    re.IGNORECASE,
)


def tex_files() -> list[Path]:
    return list((ROOT / "modules").glob("*/paper/*.tex")) + list((ROOT / "paper").glob("*.tex"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def prose_length(text: str) -> int:
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\(?:textbf|emph|mathrm|operatorname)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"[$\\{}_^~]", "", text)
    return len(re.sub(r"\s+", "", text))


def resolve_project_path(raw: str, kind: str) -> Path | None:
    raw = raw.strip()
    if not raw.startswith(r"\ProjectRoot/"):
        return None
    rel = raw[len(r"\ProjectRoot/") :]
    p = ROOT / rel
    if p.exists():
        return p
    if kind == "graphics" and not p.suffix:
        for ext in (".png", ".jpg", ".jpeg", ".pdf", ".eps"):
            if p.with_suffix(ext).exists():
                return p.with_suffix(ext)
    if kind == "input" and not p.suffix and p.with_suffix(".tex").exists():
        return p.with_suffix(".tex")
    return p


def strip_literal_environments(text: str) -> str:
    """Remove literal code examples so commands shown as text are not treated as active TeX."""
    for env in ("lstlisting", "verbatim", "Verbatim"):
        text = re.sub(
            rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}",
            "",
            text,
            flags=re.S,
        )
    return text


def project_assets(text: str):
    text = strip_literal_environments(text)
    patterns = (
        ("graphics", re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", re.S)),
        ("listing", re.compile(r"\\lstinputlisting(?:\[[^\]]*\])?\{([^}]+)\}", re.S)),
        ("input", re.compile(r"\\input\{([^}]+)\}")),
    )
    for kind, pat in patterns:
        for raw in pat.findall(text):
            if raw.strip().startswith(r"\ProjectRoot/"):
                yield kind, raw.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-build", action="store_true")
    a = ap.parse_args()

    errors: list[str] = []
    warns: list[str] = []
    labels: defaultdict[str, list[Path]] = defaultdict(list)
    all_tex: dict[Path, str] = {}

    module_tex = list((ROOT / "modules").glob("*/paper/*.tex"))
    forbidden_global_style = (
        r"\geometry{",
        r"\setmainfont",
        r"\setCJKmainfont",
        r"\renewcommand\section",
        r"\renewcommand{\baselinestretch}",
    )

    for p in tex_files():
        t = read(p)
        all_tex[p] = t
        rel = p.relative_to(ROOT)

        for marker in CONFLICT_MARKERS:
            if marker in t:
                errors.append(f"{rel}: 残留 Git 冲突标记 {marker}")

        if r"\beginingroup" in t:
            errors.append(f"{rel}: 发现不存在的 TeX 命令 \\beginingroup，应为 \\begingroup")
        if re.search(r"(?m)^\s*\\\\begin\{", t):
            errors.append(f"{rel}: 发现行首双反斜杠 \\\\begin{{...}}，可能导致 There's no line here to end")

        for token in ("??", "[?]", "TODO", "FIXME"):
            if token in t:
                warns.append(f"{rel}: 发现 {token}")

        for phrase in INTERNAL_PROSE:
            if phrase in t:
                warns.append(f"{rel}: 出现内部/过程化表达“{phrase}”，终稿建议改为直接数学事实")

        for phrase in ENGLISH_RESIDUES:
            if phrase in t:
                warns.append(f"{rel}: 出现工程式英文残留“{phrase}”，检查是否应改为中文正式表述")

        benwen_count = t.count("本文")
        if benwen_count >= 3 and "modules/00_abstract" not in str(rel).replace("\\", "/"):
            warns.append(f"{rel}: “本文”出现 {benwen_count} 次，检查是否存在反复自我说明式写法")

        for x in re.findall(r"\\label\{([^}]+)\}", t):
            labels[x].append(p)

        # 纯文字段落接近约 5 行时，优先检查是否应分点、分段、公式化或交给图表表达。
        if "modules/80_appendix" not in str(p).replace("\\", "/"):
            for idx, para in enumerate(re.split(r"\n\s*\n", t), 1):
                if any(
                    x in para
                    for x in (
                        "\\begin{equation",
                        "\\begin{align",
                        "\\begin{figure",
                        "\\begin{table",
                        "\\begin{algorithm",
                        "\\begin{lstlisting",
                    )
                ):
                    continue
                if para.lstrip().startswith(("\\section", "\\subsection", "\\subsubsection", "%")):
                    continue
                n = prose_length(para)
                if n >= 200:
                    warns.append(f"{rel}: 第 {idx} 个文字段约 {n} 字，建议分点/分段或用公式组织")

        # 对明确写成 \ProjectRoot/... 的活动资源做静态存在性检查，提前拦截路径拼错。
        for kind, raw in project_assets(t):
            target = resolve_project_path(raw, kind)
            if target is not None and not target.exists():
                errors.append(f"{rel}: {kind} 资源不存在: {raw}")

    for p in module_tex:
        t = all_tex[p]
        for token in forbidden_global_style:
            if token in t:
                errors.append(f"{p.relative_to(ROOT)}: 章节正文不得重定义公共样式 {token}")

    # paper/ 目录内不允许出现第二套 final/v2/old/backup 正文真源。
    for paper_dir in (ROOT / "modules").glob("*/paper"):
        for p in paper_dir.glob("*.tex"):
            if PAPER_VARIANT_RE.search(p.name):
                errors.append(
                    f"{p.relative_to(ROOT)}: 可疑平行正文源；请保留 canonical 文件并把旧稿移入 work/archive"
                )

    for k, ps in labels.items():
        if len(ps) > 1:
            errors.append(f"重复 label {k}: " + ", ".join(str(p.relative_to(ROOT)) for p in ps))

    # 图表放入正文后必须至少有一次文字引用，避免“孤立图表”。
    joined = "\n".join(all_tex.values())
    for label, ps in labels.items():
        if not (label.startswith("fig:") or label.startswith("tab:")):
            continue
        refs = len(re.findall(rf"\\(?:ref|autoref)\{{{re.escape(label)}\}}", joined))
        if refs == 0:
            warns.append(f"{ps[0].relative_to(ROOT)}: {label} 未被正文引用或解释")

    for reg in ROOT.glob("modules/*/results/registry.csv"):
        with reg.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("result_id"):
                    continue
                if row.get("used_in_paper", "").strip().lower() in {"yes", "true", "1", "y"}:
                    if row.get("status") != "FROZEN" or row.get("review_state") != "CHECKED":
                        errors.append(
                            f"{reg.relative_to(ROOT)}: {row['result_id']} 已用于正文但不是 FROZEN+CHECKED"
                        )

    maintex = read(ROOT / "paper/main.tex")
    required_main = (
        r"\input{settings.tex}",
        r"\ifshowtoc",
        r"\tableofcontents",
        r"\pagenumbering{arabic}",
        r"\setcounter{page}{1}",
    )
    for token in required_main:
        if token not in maintex:
            errors.append(f"paper/main.tex 缺少公共结构: {token}")

    if maintex.count(r"\clearpage") < 4:
        errors.append("paper/main.tex 分页不足：参考文献、附录、AI使用报告应各自另起一页")

    settings = ROOT / "paper/settings.tex"
    if not settings.exists() or "\\newif\\ifshowtoc" not in read(settings):
        errors.append("paper/settings.tex 缺少目录开关")

    abstract = ROOT / "modules/00_abstract/paper/abstract.tex"
    if abstract.exists() and re.search(r"\\section\*?\{", read(abstract)):
        errors.append("摘要模块不应自行创建 section；摘要标题由公共模板负责")

    appendix = ROOT / "modules/80_appendix/paper/appendix.tex"
    if appendix.exists() and re.search(r"\\subsection\{", read(appendix)):
        errors.append("附录不应使用有编号 subsection，避免目录出现错误章节号")

    if not (ROOT / "modules/20_q1/paper/q1_algorithm.tex").exists():
        errors.append("问题一伪代码示例 q1_algorithm.tex 缺失")

    if a.post_build:
        log = ROOT / "paper/main.log"
        if log.exists():
            log_text = read(log)
            if "Overfull \\hbox" in log_text:
                warns.append("LaTeX 日志存在 Overfull \\hbox")
            if "undefined references" in log_text.lower() or (
                "citation" in log_text.lower() and "undefined" in log_text.lower()
            ):
                errors.append("LaTeX 日志存在未解析引用或文献引用")

    for w in dict.fromkeys(warns):
        print("[WARN]", w)
    for e in dict.fromkeys(errors):
        print("[FAIL]", e)
    if not errors:
        print("[PASS] final preflight")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
