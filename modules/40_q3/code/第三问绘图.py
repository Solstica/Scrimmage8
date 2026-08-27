"""读取已验证的 Q3 诊断结果，生成 PNG 和一图一表；不运行求解器。"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np


root = Path(__file__).resolve().parents[1]
src = root / "results/EXPERIMENT/低速扫描重审"
fig_dir = root / "figures/诊断"
data_dir = root / "data/processed/诊断绘图"
blue, orange = "#236A92", "#C46A35"
ink, muted, grid = "#233641", "#647680", "#DDE5E8"
colors = {"15℃": blue, "10℃": orange}
rate_col = "扫描速率（K/min）"
plt.rcParams.update({
    "font.family": "Microsoft YaHei", "font.size": 11,
    "axes.unicode_minus": False, "text.color": ink,
    "axes.labelcolor": ink, "xtick.color": muted, "ytick.color": muted,
    "axes.edgecolor": grid, "axes.titleweight": "bold",
    "figure.facecolor": "#FAFCFD", "axes.facecolor": "white",
    "savefig.facecolor": "#FAFCFD", "mathtext.fontset": "dejavusans",
})


def read(name):
    with (src / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_data(name, rows):
    with (data_dir / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save(fig, name):
    fig.savefig(fig_dir / f"{name}.png", dpi=300)
    plt.close(fig)
    print(f"已生成：{name}.png")


def header(fig, num, title, subtitle):
    fig.text(.07, .97, f"Q3  /  {num}     双阈值诊断", color=muted, fontsize=10,
             va="top", weight="bold")
    fig.text(.07, .93, title, fontsize=23, weight="bold", va="top")
    fig.text(.07, .876, subtitle, fontsize=10.5, color=muted, va="top")


def draw_trade(rows, best):
    rates = [1.25, 1.5, 1.75, 2.0]
    cols = [rate_col, "新增层数", "15℃时间（s）", "10℃时间（s）", "负重时间（s）"]
    data = [{col: r[col] for col in cols} for r in rows if float(r[rate_col]) in rates]
    save_data("热安全与负重权衡", data)
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.5))
    fig.subplots_adjust(left=.08, right=.965, bottom=.17, top=.735, hspace=.68, wspace=.22)
    header(fig, "01", "增厚延长热安全时间，也缩短负重时间",
           "贴身侧温度分别降至 15℃ / 10℃；四个整数层数完整枚举，保留两种截止口径。")
    handles = [Line2D([], [], color=blue, marker="o", lw=2, label="15℃ 热安全时间"),
               Line2D([], [], color=orange, marker="s", lw=2, label="10℃ 热安全时间"),
               Line2D([], [], color=ink, ls="--", lw=1.7, label="负重时间（包含人体自重）")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.07, .835),
               ncol=3, frameon=False, columnspacing=2.6, fontsize=10.5)
    for ax, rate, letter in zip(axes.flat, rates, "ABCD"):
        group = sorted((r for r in data if float(r[rate_col]) == rate),
                       key=lambda r: int(r["新增层数"]))
        n = np.array([int(r["新增层数"]) for r in group])
        weight = np.array([float(r["负重时间（s）"]) for r in group])
        ax.plot(n, weight, color=ink, ls="--", lw=1.7, zorder=2)
        cross = []
        for threshold, marker in [("15℃", "o"), ("10℃", "s")]:
            time = np.array([float(r[f"{threshold}时间（s）"]) for r in group])
            ax.plot(n, time, color=colors[threshold], marker=marker, markersize=6,
                    lw=2.2, markeredgecolor="white", markeredgewidth=.8, zorder=3)
            # 只定位相邻整数候选间的符号变化，不插值为可行层数。
            edges = np.flatnonzero((time[:-1] - weight[:-1]) * (time[1:] - weight[1:]) < 0)
            if len(edges):
                label = f"热/重主导交替：n={edges[0]} → {edges[0] + 1}"
            else:
                label = "所有层数均受" + ("负重限制" if np.all(time > weight) else "热安全限制")
            cross.append((threshold, label))
        ax.set_title(f"{letter}   " + r"$\beta_{\mathrm{DSC}}$" + f" = {rate:g} K/min",
                     loc="left", fontsize=13, pad=27)
        ax.text(0, 1.035, f"最优新增层数：15℃ → {best[(rate, '15℃')]} 层    |    "
                f"10℃ → {best[(rate, '10℃')]} 层", transform=ax.transAxes,
                fontsize=10, color=muted)
        ax.set(xlim=(-.15, 3.15), ylim=(490, 1110), xticks=[0, 1, 2, 3],
               yticks=[500, 650, 800, 950, 1100], xlabel="新增层数 n", ylabel="时间（s）")
        ax.grid(axis="y", color=grid, lw=.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(length=0, pad=7)
        for j, (threshold, label) in enumerate(cross):
            ax.text(0, -.26 - .095 * j, f"{threshold}：{label}", transform=ax.transAxes,
                    color=colors[threshold], fontsize=9.5)
        if rate == 2:
            gap = weight[-1] - float(group[-1]["10℃时间（s）"])
            ax.annotate(f"10℃ 距负重上限仅 {gap:.3f} s", xy=(3, weight[-1]),
                        xytext=(.55, 1010), fontsize=10, color=orange,
                        arrowprops={"arrowstyle": "-", "color": orange, "lw": 1},
                        bbox={"facecolor": "#FFF6ED", "edgecolor": "none", "pad": 6})
    fig.text(.07, .05, "读图：有效时间取热安全与负重时间的较小值。连线仅辅助阅读，非整数层数不属于可行方案。",
             fontsize=10, color=muted)
    fig.text(.07, .025, "诊断结果 · 阈值待确认 · 低速工况不能直接解释为已确认的材料设计", fontsize=9, color=muted)
    save(fig, "热安全与负重权衡")


def draw_heatmap(rows, best):
    rates = sorted({float(r[rate_col]) for r in rows})
    cols = [rate_col, "新增层数", "15℃有效时间（s）", "10℃有效时间（s）",
            "15℃限制因素", "10℃限制因素"]
    data = [{col: r[col] for col in cols} for r in rows]
    save_data("有效时间全景", data)
    cmap = LinearSegmentedColormap.from_list("time", ["#F5F0DF", "#B7D7D4", "#4E999F", "#164D64"])
    norm = Normalize(0, 800)
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 10))
    fig.subplots_adjust(left=.10, right=.87, bottom=.15, top=.76, wspace=.32)
    header(fig, "02", "哪一层最优，取决于谁先成为限制",
           "全部 8 个扫描速率 × 4 个层数；双描边标出各速率下的最优方案，统一色阶便于跨阈值比较。")
    lookup = {(float(r[rate_col]), int(r["新增层数"])): r for r in data}
    for ax, threshold, letter in zip(axes, ["15℃", "10℃"], "AB"):
        values = np.array([[float(lookup[(v, n)][f"{threshold}有效时间（s）"])
                            for n in range(4)] for v in rates])
        im = ax.imshow(values, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_title(f"{letter}   贴身侧 {threshold} 截止", color=colors[threshold],
                     fontsize=14, loc="left", pad=16)
        ax.set(xticks=np.arange(4), xticklabels=[0, 1, 2, 3], yticks=np.arange(8),
               yticklabels=[f"{v:g}" + (" *" if v == .5 else "") for v in rates],
               xlabel="新增层数 n")
        ax.set_ylabel(r"扫描速率 $\beta_{\mathrm{DSC}}$（K/min）")
        ax.set_xticks(np.arange(-.5, 4, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 8, 1), minor=True)
        ax.grid(which="minor", color="white", lw=2)
        ax.tick_params(which="both", length=0, pad=8)
        ax.spines[:].set_visible(False)
        for i, v in enumerate(rates):
            for n in range(4):
                val = values[i, n]
                color = "white" if val >= 530 else ink
                active = lookup[(v, n)][f"{threshold}限制因素"]
                ax.text(n, i - .10, f"{val:.1f}", ha="center", va="center",
                        fontsize=12, weight="bold", color=color)
                ax.text(n, i + .21, active, ha="center", va="center", fontsize=9, color=color)
            n = best[(v, threshold)]
            for edge, lw in [(ink, 3.8), ("white", 1.6)]:
                ax.add_patch(Rectangle((n - .425, i - .425), .85, .85,
                                       fill=False, edgecolor=edge, lw=lw))
    bar_ax = fig.add_axes([.905, .23, .017, .44])
    bar = fig.colorbar(im, cax=bar_ax, ticks=[0, 200, 400, 600, 800])
    bar.ax.tick_params(length=0, labelsize=9)
    bar.outline.set_visible(False)
    bar.set_label("有效时间（s）", labelpad=12)
    fig.text(.10, .085, "单元格：有效时间（s） / 限制因素。最优框由未舍入数值判定；四舍五入仅用于显示。",
             fontsize=10, color=muted)
    fig.text(.10, .056, "扫描速率行按类别排列，行距不代表数值间距。* 0.5 K/min 为极端高不确定性诊断。",
             fontsize=9.5, color=muted)
    fig.text(.10, .027, "诊断结果 · 低速高潜热工况的数学最优，不等于材料可行性已确认", fontsize=9.5, color=muted)
    save(fig, "有效时间全景")


def draw_switch(rows):
    cols = ["阈值口径", "区间下界（K/min）", "区间上界（K/min）", "下界最优层数", "上界最优层数"]
    save_data("双阈值切换区间", [{col: r[col] for col in cols} for r in rows])
    fig, ax = plt.subplots(figsize=(12.8, 7.6))
    fig.subplots_adjust(left=.13, right=.95, bottom=.22, top=.79)
    header(fig, "03", "阈值降低，层数切换向更高扫描速率移动",
           "六个窄区间来自自适应二分；横线表示数值定位范围，不是统计置信区间。")
    for y in range(3):
        if y % 2 == 0:
            ax.axhspan(y - .45, y + .45, color="#F0F5F7", zorder=0)
    for r in rows:
        threshold = r["阈值口径"]
        low, high = float(r["区间下界（K/min）"]), float(r["区间上界（K/min）"])
        y = int(r["下界最优层数"]) + (-.17 if threshold == "15℃" else .17)
        ax.plot([low, high], [y, y], color=colors[threshold], lw=7, solid_capstyle="butt")
        ax.plot([low, high], [y, y], color=colors[threshold], marker="|", markersize=13, ls="none")
        ax.text(high + .014, y, f"{threshold}   [{low:.4f}, {high:.4f}]",
                va="center", fontsize=10.5, color=colors[threshold])
    ax.set(xlim=(1.18, 1.91), ylim=(2.48, -.48), yticks=[0, 1, 2],
           yticklabels=["0 → 1 层", "1 → 2 层", "2 → 3 层"],
           xticks=np.arange(1.2, 1.81, .1),
           xlabel=r"扫描速率 $\beta_{\mathrm{DSC}}$（K/min）")
    ax.set_ylabel("最优新增层数的切换", labelpad=18)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=grid, lw=.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, pad=10)
    fig.text(.13, .115, "所有原始区间宽度均为 0.0078125 K/min；标签显示 4 位小数，完整精度见配套数据表。",
             color=muted, fontsize=10)
    fig.text(.13, .075, "半时间步长复核保持六处切换方向不变；这不等于已确定连续域内全部分界或材料可行性。",
             color=muted, fontsize=10)
    fig.text(.13, .035, "诊断结果 · 同时保留 15℃ 与 10℃，最终截止阈值仍待建模端确认", color=muted, fontsize=9.5)
    save(fig, "双阈值切换区间")


def main():
    rows = read("粗扫描方案.csv")
    opt = read("粗扫描最优方案.csv")
    switches = read("切换区间.csv")
    best = {(float(r[rate_col]), r["阈值口径"]): int(r["最优新增层数"]) for r in opt}
    # 防止错读字段或把热安全时间当作有效时间。
    assert len(rows) == 32 and len(best) == 16 and len(switches) == 6
    for r in rows:
        for threshold in ["15℃", "10℃"]:
            time = float(r[f"{threshold}时间（s）"])
            weight = float(r["负重时间（s）"])
            effective = float(r[f"{threshold}有效时间（s）"])
            assert np.all(np.isfinite([time, weight, effective]))
            assert abs(effective - min(time, weight)) < 1e-8
    for (v, threshold), n in best.items():
        group = [r for r in rows if float(r[rate_col]) == v]
        assert {int(r["新增层数"]) for r in group} == {0, 1, 2, 3}
        actual = max(group, key=lambda r: float(r[f"{threshold}有效时间（s）"]))
        assert int(actual["新增层数"]) == n
    for r in switches:
        width = float(r["区间上界（K/min）"]) - float(r["区间下界（K/min）"])
        assert abs(width - .0078125) < 1e-10
    fig_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    draw_trade(rows, best)
    draw_heatmap(rows, best)
    draw_switch(switches)
    print("通过：32 个方案的双阈值有效时间、16 个最优层数和 6 个切换区间校验。")


if __name__ == "__main__":
    main()
