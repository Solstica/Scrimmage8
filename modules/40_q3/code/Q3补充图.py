"""读取 Q3 已有候选结果，生成不重复的补充诊断图和一图一表。"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.font_manager import FontProperties
import numpy as np


root = Path(__file__).resolve().parents[1]
src = root / "results/EXPERIMENT/低速扫描重审/粗扫描方案.csv"
fig_dir = root / "figures/诊断"
data_dir = root / "figures/editable"
ink, muted, grid = "#000000", "#647680", "#DDE5E8"
blue, orange = "#236A92", "#C46A35"

plt.rcParams.update({
    "font.family": "SimSun",
    "font.size": 22,
    "axes.unicode_minus": False,
    "axes.labelcolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "axes.edgecolor": grid,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

times_bold = FontProperties(fname="C:/Windows/Fonts/timesbd.ttf", size=22)
simsun = FontProperties(fname="C:/Windows/Fonts/simsun.ttc", size=22)
palette = ["#3C9BC9", "#65BDBA", "#B0D6A9", "#FEE199",
           "#FCDC94", "#FAA26F", "#F97F5F", "#FC757B"]
heat_cmap = LinearSegmentedColormap.from_list("八色发散", palette, N=256)


def read_rows():
    with src.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    try:
        f = path.open("w", encoding="utf-8-sig", newline="")
    except PermissionError:
        path = path.with_name(path.stem + "（Python重绘）" + path.suffix)
        f = path.open("w", encoding="utf-8-sig", newline="")
    with f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save(fig, name):
    fig_dir.mkdir(parents=True, exist_ok=True)
    path = fig_dir / f"{name}.png"
    try:
        fig.savefig(path, dpi=300, facecolor="white", transparent=False,
                    bbox_inches="tight", pad_inches=.02)
    except PermissionError:
        path = fig_dir / f"{name}（Python重绘）.png"
        fig.savefig(path, dpi=300, facecolor="white", transparent=False,
                    bbox_inches="tight", pad_inches=.02)
    plt.close(fig)
    print(f"已生成：{path.name}")


def build_data(rows):
    rates = sorted({float(r["扫描速率（K/min）"]) for r in rows})
    thresholds = ["15℃", "10℃"]
    lookup = {(float(r["扫描速率（K/min）"]), int(r["新增层数"])): r for r in rows}

    marginal = []
    margin = []
    for rate in rates:
        for threshold in thresholds:
            for n in range(1, 4):
                before = lookup[(rate, n - 1)]
                after = lookup[(rate, n)]
                old_t = float(before[f"{threshold}有效时间（s）"])
                new_t = float(after[f"{threshold}有效时间（s）"])
                marginal.append({
                    "扫描速率（K/min）": f"{rate:g}",
                    "阈值口径": threshold,
                    "层数变化": f"{n - 1}→{n}",
                    "原新增层数": str(n - 1),
                    "新增后层数": str(n),
                    "原有效时间（s）": f"{old_t:.9f}",
                    "新增后有效时间（s）": f"{new_t:.9f}",
                    "边际有效时间（s）": f"{new_t - old_t:.9f}",
                })
            for n in range(4):
                r = lookup[(rate, n)]
                heat = float(r[f"{threshold}时间（s）"])
                weight = float(r["负重时间（s）"])
                margin.append({
                    "扫描速率（K/min）": f"{rate:g}",
                    "阈值口径": threshold,
                    "新增层数": str(n),
                    "阈值时间 t_θ（s）": f"{heat:.9f}",
                    "负重时间 t_W（s）": f"{weight:.9f}",
                    "约束裕量 t_θ−t_W（s）": f"{heat - weight:.9f}",
                    "主导限制": "热安全" if heat <= weight else "负重",
                })
    return rates, marginal, margin


def draw_marginal(rates, rows):
    trans = ["0→1", "1→2", "2→3"]
    vals = {(float(r["扫描速率（K/min）"]), r["阈值口径"], r["层数变化"]):
            float(r["边际有效时间（s）"]) for r in rows}
    lim = max(abs(v) for v in vals.values())
    fig, axes = plt.subplots(1, 2, figsize=(40 / 2.54, 15 / 2.54), sharey=True)
    fig.subplots_adjust(left=.095, right=.84, bottom=.18, top=.91, wspace=.20)
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    for ax, threshold in zip(axes, ["15℃", "10℃"]):
        matrix = np.array([[vals[(rate, threshold, t)] for t in trans] for rate in rates])
        im = ax.imshow(matrix, cmap=heat_cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_xticks(range(3), trans)
        ax.set_yticks(range(len(rates)), [f"{r:g}" for r in rates])
        ax.set_xlabel("层数变化", fontproperties=simsun)
        ax.set_ylabel("扫描速率（K/min）", fontproperties=simsun)
        ax.grid(which="minor", color="white", lw=2)
        ax.set_xticks(np.arange(-.5, 3, 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(rates), 1), minor=True)
        ax.tick_params(which="major", direction="in", length=8, width=2, pad=8)
        ax.tick_params(which="minor", length=0)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(2)
            spine.set_color("black")
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(times_bold)
        ax.text(.02, 1.02, threshold, transform=ax.transAxes,
                fontproperties=times_bold, color="black", va="bottom")
        for i, rate in enumerate(rates):
            for j, t in enumerate(trans):
                val = matrix[i, j]
                ax.text(j, i, f"{val:+.1f}", ha="center", va="center",
                        color="white" if abs(val) > .45 * lim else "black",
                        fontproperties=times_bold)
    bar_ax = fig.add_axes([.86, .25, .016, .42])
    cb = fig.colorbar(im, cax=bar_ax, ticks=[-lim, -lim / 2, 0, lim / 2, lim])
    cb.set_label("边际有效时间（s）", labelpad=10, fontproperties=simsun)
    cb.outline.set_linewidth(2)
    cb.outline.set_color("black")
    cb.ax.tick_params(direction="in", length=8, width=2, pad=8)
    for label in cb.ax.get_yticklabels():
        label.set_fontproperties(times_bold)
    save(fig, "边际有效时间变化（Python重绘）")


def draw_margin(rates, rows):
    ns = [0, 1, 2, 3]
    vals = {(float(r["扫描速率（K/min）"]), r["阈值口径"], int(r["新增层数"])):
            float(r["约束裕量 t_θ−t_W（s）"]) for r in rows}
    lim = max(abs(v) for v in vals.values())
    fig, axes = plt.subplots(1, 2, figsize=(40 / 2.54, 15 / 2.54), sharey=True)
    fig.subplots_adjust(left=.095, right=.84, bottom=.18, top=.91, wspace=.20)
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    for ax, threshold in zip(axes, ["15℃", "10℃"]):
        matrix = np.array([[vals[(rate, threshold, n)] for n in ns] for rate in rates])
        im = ax.imshow(matrix, cmap=heat_cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_xticks(range(4), ns)
        ax.set_yticks(range(len(rates)), [f"{r:g}" for r in rates])
        ax.set_xlabel("新增层数 n", fontproperties=simsun)
        ax.set_ylabel("扫描速率（K/min）", fontproperties=simsun)
        ax.set_xticks(np.arange(-.5, 4, 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(rates), 1), minor=True)
        ax.grid(which="minor", color="white", lw=2)
        ax.tick_params(which="major", direction="in", length=8, width=2, pad=8)
        ax.tick_params(which="minor", length=0)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(2)
            spine.set_color("black")
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(times_bold)
        ax.text(.02, 1.02, threshold, transform=ax.transAxes,
                fontproperties=times_bold, color="black", va="bottom")
        for i, rate in enumerate(rates):
            for j, n in enumerate(ns):
                val = matrix[i, j]
                ax.text(j, i, f"{val:+.1f}", ha="center", va="center",
                        color="white" if abs(val) > .45 * lim else "black",
                        fontproperties=times_bold)
    bar_ax = fig.add_axes([.86, .25, .016, .42])
    cb = fig.colorbar(im, cax=bar_ax, ticks=[-lim, -lim / 2, 0, lim / 2, lim])
    cb.set_label("约束裕量（s）", labelpad=10, fontproperties=simsun)
    cb.outline.set_linewidth(2)
    cb.outline.set_color("black")
    cb.ax.tick_params(direction="in", length=8, width=2, pad=8)
    for label in cb.ax.get_yticklabels():
        label.set_fontproperties(times_bold)
    save(fig, "约束裕量地图（Python重绘）")


def main():
    rows = read_rows()
    assert len(rows) == 32
    rates, marginal, margin = build_data(rows)
    data_dir.mkdir(parents=True, exist_ok=True)
    write_csv(data_dir / "边际有效时间变化.csv", list(marginal[0]), marginal)
    write_csv(data_dir / "约束裕量地图.csv", list(margin[0]), margin)
    draw_marginal(rates, marginal)
    draw_margin(rates, margin)
    print("已生成：2 张 Q3 补充诊断图、2 份中文一图一表。")


if __name__ == "__main__":
    main()
