import csv
import sys
from io import StringIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, NullLocator


# 尺寸按论文双栏；宋体中文、Times 英文与数字。
MM = 1 / 25.4
DPI = 300
NAMES = ["ISO 11079简化", "旧PMV关系", "Kuwabara经验"]
COLORS = dict(zip(NAMES, ["#006BEE", "#777777", "#CB5CD7"]))
SHORT = dict(zip(NAMES, ["ISO 简化", "旧 PMV", "Kuwabara"]))
INK = "#333333"
plt.rcParams.update({
    "font.family": ["Times New Roman", "SimSun"],
    "font.size": 8.5,
    "axes.labelsize": 9,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.linewidth": 0.75,
    "xtick.major.width": 0.75,
    "ytick.major.width": 0.75,
    "mathtext.fontset": "stix",
    "svg.fonttype": "none",
    "svg.hashsalt": "q2-figure",
    "axes.unicode_minus": False,
    "savefig.facecolor": "white",
})


def read(path):
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def style(ax):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=7)
    ax.tick_params(axis="x", direction="out", length=3)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#EEF0F2", linewidth=0.35)


def panel(ax, text):
    ax.text(0, 1.045, text, transform=ax.transAxes, fontsize=10, va="bottom")


def threshold_legend(fig, y):
    handles = [
        Line2D([], [], marker="o", color=INK, linestyle="none", markersize=4.5, label="15 ℃ 阈值（t₁₅）"),
        Line2D([], [], marker="s", color=INK, markerfacecolor="white", linestyle="none", markersize=4.5, label="10 ℃ 阈值（t₁₀）"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.55, y), ncol=2, frameon=False)


def save(fig, out, name):
    out.mkdir(parents=True, exist_ok=True)
    preview = out / "预览"
    preview.mkdir(exist_ok=True)
    # 不用 tight 裁切改变声明的物理尺寸。
    svg = StringIO()
    fig.savefig(svg, format="svg", metadata={"Date": None})
    (out / f"{name}.svg").write_text("\n".join(line.rstrip() for line in svg.getvalue().splitlines()) + "\n", encoding="utf-8", newline="\n")
    fig.savefig(preview / f"{name}.png", dpi=DPI)
    plt.close(fig)
    print(f"已生成 {name}：SVG 与 {DPI} dpi PNG")


def draw_time(data, out):
    fig, (ax, gap) = plt.subplots(1, 2, figsize=(180 * MM, 142 * MM), sharey=True,
                                 gridspec_kw={"width_ratios": [2.1, 1]})
    fig.subplots_adjust(left=0.175, right=0.955, bottom=0.14, top=0.855, wspace=0.20)
    ys = [9, 8, 7, 5.5, 4.5, 3.5, 2, 1, 0]
    for r, y in zip(data, ys):
        color = COLORS[r["外对流模型"]]
        t15, t10, dt = (float(r[k]) for k in ("t15（s）", "t10（s）", "阈值间隔（s）"))
        ax.plot([t15, t10], [y, y], color=color, linewidth=1.4)
        ax.plot(t15, y, "o", color=color, markersize=4.5)
        ax.plot(t10, y, "s", color=color, markerfacecolor="white", markersize=4.5)
        ax.annotate(f"{t15:.1f}", (t15, y), xytext=(-6, 0), textcoords="offset points", ha="right", va="center", color=color)
        ax.annotate(f"{t10:.1f}", (t10, y), xytext=(6, 0), textcoords="offset points", va="center", color=color)
        gap.hlines(y, 0, dt, color=color, linewidth=1.1, alpha=0.5)
        gap.plot(dt, y, "D", color=color, markersize=4)
        gap.annotate(f"{dt:.2f}", (dt, y), xytext=(6, 0), textcoords="offset points", va="center", color=color)
    for scan, y in zip([2, 5, 10], [9.8, 6.2, 2.7]):
        ax.text(0, y, f"DSC = {scan} K/min", fontsize=8.5, color=INK)
    for a in (ax, gap):
        style(a)
        a.set_ylim(-0.65, 10.2)
        for y in (6.55, 3.05):
            a.axhline(y, color="#E5E7EB", linewidth=0.5)
    ax.set_yticks(ys, [SHORT[r["外对流模型"]] for r in data])
    gap.tick_params(labelleft=False)
    ax.set_xlim(0, 240)
    ax.xaxis.set_major_locator(MultipleLocator(50))
    gap.set_xlim(0, 17)
    gap.xaxis.set_major_locator(MultipleLocator(5))
    ax.set_xlabel("首次到达阈值的时间 / s", labelpad=8)
    gap.set_xlabel(r"$t_{10}-t_{15}$ / s", labelpad=8)
    panel(ax, "(a)  阈值时间")
    panel(gap, "(b)  阈值间隔")
    threshold_legend(fig, 0.983)
    fig.text(0.175, 0.032, "线段连接两个温度阈值，不表示置信区间；间隔不等于允许继续暴露时间。", fontsize=8)
    save(fig, out, "阈值时间")


def draw_sens(data, out):
    fig, axes = plt.subplots(1, 2, figsize=(180 * MM, 94 * MM), sharey=True)
    fig.subplots_adjust(left=0.12, right=0.965, bottom=0.25, top=0.80, wspace=0.24)
    handles = [Line2D([], [], color=COLORS[n], marker=m, linewidth=1.1, markersize=4.5, label=SHORT[n])
               for n, m in [(NAMES[1], "o"), (NAMES[2], "D")]]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.54, 0.985), ncol=2, frameon=False)
    for k, ax, tag in zip((15, 10), axes, ("a", "b")):
        style(ax)
        for r in data:
            name, scan = r["外对流模型"], float(r["扫描速率（K/min）"])
            y = {2: 2, 5: 1, 10: 0}[scan] + (0.17 if name == NAMES[1] else -0.17)
            x = float(r[f"t{k}变化（%）"])
            color = COLORS[name]
            ax.hlines(y, 0, x, color=color, linewidth=1.1)
            ax.plot(x, y, "o" if name == NAMES[1] else "D", color=color, markersize=4.5)
            ax.annotate(f"{x:+.2f}%", (x, y), xytext=(6 if x > 0 else -6, 0), textcoords="offset points",
                        ha="left" if x > 0 else "right", va="center", color=color)
        ax.axvline(0, color=INK, linewidth=0.8)
        ax.set_xlim(-19, 19)
        ax.set_ylim(-0.6, 2.6)
        ax.set_xticks([-15, -10, -5, 0, 5, 10, 15])
        ax.set_xlabel("相对 ISO 11079 简化的变化 / %", labelpad=8)
        panel(ax, rf"({tag})  $t_{{{k}}}$")
    axes[0].set_yticks([2, 1, 0], ["2", "5", "10"])
    axes[0].set_ylabel("DSC 扫描速率 / (K/min)", labelpad=8)
    fig.text(0.12, 0.08, "负值：阈值提前     |     零线：ISO 11079 简化基准     |     正值：阈值推迟", fontsize=8)
    save(fig, out, "边界敏感性")


def draw_check(data, out):
    fig, (ax, fine) = plt.subplots(2, 1, figsize=(180 * MM, 178 * MM),
                                  gridspec_kw={"height_ratios": [2.3, 1]})
    fig.subplots_adjust(left=0.26, right=0.955, bottom=0.115, top=0.875, hspace=0.68)
    threshold_legend(fig, 0.98)
    base = [r for r in data if r["设置"] == "基准"]
    keys = [(name, scan) for name in NAMES for scan in (2.0, 5.0, 10.0)]
    for r in base:
        name, scan = r["外对流模型"], float(r["扫描速率（K/min）"])
        y = 8 - keys.index((name, scan))
        is15 = r["阈值"] == "t15"
        color = COLORS[name]
        x = float(r["相对差异（%）"])
        ax.plot(x, y + (0.13 if is15 else -0.13), "o" if is15 else "s", color=color,
                markerfacecolor=color if is15 else "white", markersize=4.5)
    style(ax)
    ax.set_yticks(range(8, -1, -1), [f"{SHORT[n]}  ·  {s:g}" for n, s in keys])
    ax.set_xlim(0, 1.55)
    ax.set_ylim(-0.6, 8.6)
    ax.xaxis.set_major_locator(MultipleLocator(0.25))
    for y in (2.5, 5.5):
        ax.axhline(y, color="#E5E7EB", linewidth=0.5)
    ax.set_ylabel("关系 · DSC 扫描速率 / (K/min)", labelpad=8)
    ax.set_xlabel("(有限体积 − 模态) / 模态 × 100%", labelpad=8)
    panel(ax, "(a)  独立离散对照")
    maximum = max(float(r["绘图幅值（%）"]) for r in base)
    ax.text(0.995, 1.06, f"最大偏差 {maximum:.4f}%", transform=ax.transAxes, ha="right", fontsize=8.5)

    rows = [r for r in data if r["设置"] != "基准"]
    for j, r in enumerate(rows):
        x = float(r["绘图幅值（%）"])
        is15 = r["阈值"] == "t15"
        color = COLORS[NAMES[0]]
        fine.plot(x, 3 - j, "o" if is15 else "s", color=color,
                  markerfacecolor=color if is15 else "white", markersize=4.5)
        fine.annotate(f"{float(r['相对差异（%）']):+.6f}%", (x, 3 - j), xytext=(7, 0),
                      textcoords="offset points", va="center", fontsize=8.5)
    style(fine)
    fine.set_xscale("log")
    fine.set_xlim(1e-5, 1.5e-2)
    fine.xaxis.set_minor_locator(NullLocator())
    fine.set_ylim(-0.55, 3.55)
    fine.set_yticks([3, 2, 1, 0], [r["设置"] + " · " + r["阈值"] for r in rows])
    fine.set_xlabel("相对基准有限体积的变化幅值 / %（对数轴）", labelpad=8)
    panel(fine, "(b)  有限体积加密检查")
    fine.text(0.995, 1.08, "ISO 简化 · 5 K/min", transform=fine.transAxes, ha="right", fontsize=8.5)
    fig.text(0.26, 0.027, "上图为方法差异；下图为离散参数变化。数值一致性不能证明外边界的物理适用性。", fontsize=8)
    save(fig, out, "数值验证")


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    draw_time(read(src / "阈值时间.csv"), out)
    draw_sens(read(src / "边界敏感性.csv"), out)
    draw_check(read(src / "数值验证.csv"), out)


if __name__ == "__main__":
    main()
