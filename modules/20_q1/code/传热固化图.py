"""从一份独立数据表复现基准工况的传热—固化共时间轴图。"""

import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


out = Path(__file__).resolve().parents[1] / "results" / "EXPERIMENT" / "第一问图形设计_20260827"
with (out / "传热固化数据.csv").open(encoding="utf-8-sig", newline="") as f:
    header = next(csv.reader(f))
data = np.genfromtxt(out / "传热固化数据.csv", delimiter=",", skip_header=1, encoding="utf-8-sig")


def col(name):
    values = data[:, header.index(name)]
    return values[np.isfinite(values)]


t = col("时间（s）")
Tin = col("贴身侧温度（℃）")
Tavg = col("功能层平均温度（℃）")
Tout = col("外表面温度（℃）")
xi = col("固化进度")
tp = col("温度场时刻（s）")
names = [name for name in header if name.startswith("位置")]
x = np.array([float(name.removeprefix("位置").split("mm")[0]) for name in names])
field = np.array([col(name) for name in names])
levels, tm = col("节点进度"), col("节点时间（s）")
thresholds, tt = col("评价阈值（℃）"), col("达阈值时间（s）")

plt.rcParams.update({
    "font.family": ["Times New Roman", "SimSun"],
    "font.size": 8.5,
    "axes.labelsize": 9,
    "axes.linewidth": 0.75,
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#333333",
    "text.color": "#333333",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "axes.unicode_minus": False,
    "mathtext.fontset": "stix",
})
blue, purple = "#006BEE", "#CB5CD7"
ink, gray, grid = "#333333", "#777777", "#E5E7EB"
panel_font = FontProperties(family="Times New Roman", size=10, weight="bold")

fig = plt.figure(figsize=(180 / 25.4, 162 / 25.4), facecolor="white")
gs = fig.add_gridspec(3, 1, height_ratios=[1.25, 1.1, 0.72], hspace=0.18,
                      left=0.12, right=0.90, bottom=0.095, top=0.90)
ax0 = fig.add_subplot(gs[0])
ax1 = fig.add_subplot(gs[1], sharex=ax0)
ax2 = fig.add_subplot(gs[2], sharex=ax0)

for label, ax in zip(("(a)", "(b)", "(c)"), (ax0, ax1, ax2)):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(direction="out", width=0.75, length=3, pad=3)
    ax.text(-0.105, 1.015, label, transform=ax.transAxes, fontproperties=panel_font)
    ax.set_xlim(0, 320)
    ax.set_axisbelow(True)
for ax in (ax0, ax1):
    ax.tick_params(labelbottom=False)

# 温度色块为原采样值，等温线仅在相邻采样间线性定位。
te = np.r_[tp[0], (tp[:-1] + tp[1:]) / 2, tp[-1]]
xe = np.r_[x[0], (x[:-1] + x[1:]) / 2, x[-1]]
heat = ax0.pcolormesh(te, xe, field, shading="flat", cmap="cividis", vmin=5, vmax=38)
cs = ax0.contour(tp, x, field, levels=[15, 20, 25], colors="white", linewidths=0.8)
ax0.clabel(cs, fmt={15: "15 ℃", 20: "20 ℃", 25: "25 ℃"}, fontsize=8,
           manual=[(242, 1.3), (175, 0.3), (58, 0.3)], inline_spacing=3)
for pos in (0.7, 1.1):
    ax0.axhline(pos, color="white", ls=(0, (2, 3)), lw=0.85, alpha=0.9)
for y, name in ((0.35, "织物层"), (0.9, "功能层"), (1.25, "隔热层")):
    ax0.text(1.012, y, name, transform=ax0.get_yaxis_transform(), va="center", fontsize=8)
ax0.set_ylim(0, 1.4)
ax0.set_yticks([0, 0.7, 1.1, 1.4])
ax0.set_ylabel("距贴身侧位置 (mm)", labelpad=10)
cax = fig.add_axes([0.63, 0.943, 0.27, 0.013])
cb = fig.colorbar(heat, cax=cax, orientation="horizontal", ticks=[5, 15, 25, 38])
cb.outline.set_visible(False)
cb.ax.tick_params(length=2, width=0.6, labelsize=8, pad=2)
fig.text(0.61, 0.947, "温度 (℃)", ha="right", va="center", fontsize=8)
fig.text(0.12, 0.949, "基准工况 · v = 5 K/min", ha="left", va="center", fontsize=8)

# 曲线与固化进度共用时间轴，浅色区仅表示 10%—90% 进度区间。
for ax in (ax1, ax2):
    ax.axvspan(tm[0], tm[2], color=purple, alpha=0.07, lw=0)
    ax.grid(axis="y", color=grid, linewidth=0.35)
for temp, color, ls, label in (
    (Tin, blue, "-", "贴身侧"),
    (Tavg, purple, (0, (5, 2)), "功能层均温"),
    (Tout, gray, (0, (1.5, 2)), "外表面"),
):
    ax1.plot(t, temp, color=color, ls=ls, lw=1.4 if label == "贴身侧" else 1.1, label=label)
ax1.set_ylim(5, 39)
ax1.set_yticks([10, 15, 20, 30, 37])
ax1.set_ylabel("温度 (℃)", labelpad=13)
ax1.legend(loc="upper center", bbox_to_anchor=(0.55, 1), ncol=3, frameon=False, columnspacing=1.3,
           handlelength=2.5, handletextpad=0.5, fontsize=8)
for temp, time, marker in zip(thresholds, tt, ("o", "s")):
    ax1.axhline(temp, color=gray, lw=0.7, ls=(0, (3, 4)), alpha=0.75)
    ax1.scatter(time, temp, s=24, marker=marker, color=blue, ec="white", lw=0.7, zorder=6)
ax1.annotate(f"15 ℃ · {tt[0]:.1f} s", xy=(tt[0], 15), xytext=(241, 25),
             ha="center", fontsize=8, arrowprops={"arrowstyle": "-", "color": blue, "lw": 0.8})
ax1.annotate(f"10 ℃ · {tt[1]:.1f} s", xy=(tt[1], 10), xytext=(241, 7.8),
             ha="center", fontsize=8, arrowprops={"arrowstyle": "-", "color": blue, "lw": 0.8})

ax2.fill_between(t, 0, xi, color=purple, alpha=0.10, lw=0)
ax2.plot(t, xi, color=purple, lw=1.4)
ax2.scatter(tm[:3], levels[:3], s=21, color=purple, ec="white", lw=0.7, zorder=5)
for q, time in zip(levels[:3], tm[:3]):
    ax2.annotate(f"{q:.0%}", xy=(time, q), xytext=(-8, 9), textcoords="offset points",
                 ha="right", va="center", fontsize=8)
ax2.scatter(tm[-1], 1, marker="D", s=23, color=ink, ec="white", lw=0.6, zorder=6)
ax2.annotate(f"固化完成\n{tm[-1]:.1f} s", xy=(tm[-1], 1), xytext=(298, 0.43),
             ha="center", va="center", fontsize=8,
             arrowprops={"arrowstyle": "-", "color": ink, "lw": 0.8})
ax2.text((tm[0] + tm[2]) / 2, 1.16, "10%—90% 固化区间", ha="center", va="center", fontsize=8, color="#795583")
ax2.set_ylim(0, 1.28)
ax2.set_yticks([0, 0.5, 1])
ax2.set_ylabel("固化进度", labelpad=14)
ax2.set_xlabel("时间 (s)", labelpad=8)
ax2.set_xticks(np.arange(0, 301, 50))
for ax in (ax0, ax1, ax2):
    ax.axvline(tm[-1], color=ink, lw=0.75, ls=(0, (4, 3)), alpha=0.7)

fig.savefig(out / "传热与固化.png", dpi=300, facecolor="white")
plt.close(fig)
print(out / "传热与固化.png")
