"""生成双阈值最优新增层数状态带状图预览及矢量输出。"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch, Rectangle
import matplotlib.patheffects as patheffects
import numpy as np


root = Path(__file__).resolve().parents[1]
src = root / "results/EXPERIMENT/低速扫描重审/切换区间.csv"
out_png = root / "figures/图3：双阈值最优层数状态带状图（Python预览）.png"
out_svg = root / "figures/图3：双阈值最优层数状态带状图（Python矢量）.svg"

times = FontProperties(fname="C:/Windows/Fonts/times.ttf", size=22)
times_bold = FontProperties(fname="C:/Windows/Fonts/timesbd.ttf", size=22)
simsun = FontProperties(fname="C:/Windows/Fonts/simsun.ttc", size=22)
# 使用宋体字形；温度刻度通过轻微描边实现粗体效果，避免切换到微软雅黑。
simsun_bold = FontProperties(fname="C:/Windows/Fonts/simsun.ttc", size=22)

COLORS = {0: "#E7F0F5", 1: "#A9C9D8", 2: "#6199B0", 3: "#236A92"}
TEXT_COLORS = {0: "#111111", 1: "#111111", 2: "#FFFFFF", 3: "#FFFFFF"}


def read_rows():
    with src.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def draw(rows):
    x_min, x_data_max, x_axis_max = 1.18, 1.75, 1.80
    thresholds = ["15℃", "10℃"]
    bands = {}
    for threshold in thresholds:
        transitions = sorted(
            [r for r in rows if r["阈值口径"] == threshold],
            key=lambda r: float(r["区间下界（K/min）"]),
        )
        edges = [x_min]
        for r in transitions:
            edges.append((float(r["区间下界（K/min）"]) + float(r["区间上界（K/min）"])) / 2)
        edges.append(x_data_max)
        bands[threshold] = {"edges": edges, "transitions": transitions}

    fig, ax = plt.subplots(figsize=(20 / 2.54, 15 / 2.54))
    fig.subplots_adjust(left=0.18, right=0.97, bottom=0.20, top=0.90)
    y_positions = {"15℃": 1.25, "10℃": 0.35}
    bar_h = 0.62

    for threshold in thresholds:
        y = y_positions[threshold]
        transitions = bands[threshold]["transitions"]
        edges = bands[threshold]["edges"]
        for n in range(4):
            left, right = edges[n], edges[n + 1]
            ax.barh(y, right - left, left=left, height=bar_h,
                    color=COLORS[n], edgecolor="white", linewidth=1.4, zorder=2)
            # 最窄的末段（10℃、n=3）不足以容纳完整标签，交由顶部图例编码，避免文字越界。
            if right - left >= 0.06:
                ax.text((left + right) / 2, y, f"n={n}", ha="center", va="center",
                        fontproperties=times_bold, color=TEXT_COLORS[n], zorder=4)
        for r in transitions:
            low = float(r["区间下界（K/min）"])
            high = float(r["区间上界（K/min）"])
            ax.add_patch(Rectangle(
                (low, y - bar_h / 2), high - low, bar_h,
                facecolor="#D17B3A", edgecolor="none", alpha=0.23, zorder=3,
            ))
            ax.vlines([low, high], y - bar_h / 2 - 0.05, y + bar_h / 2 + 0.05,
                      color="#B65B24", linewidth=1.5, zorder=3)

    # 右侧保留少量留白，避免最窄的 n=3 状态段文字被裁切。
    ax.set_xlim(x_min, x_axis_max)
    ax.set_ylim(-0.25, 1.85)
    ax.set_xticks(np.arange(1.2, 1.81, 0.1))
    ax.set_yticks([1.25, 0.35])
    ax.set_yticklabels(thresholds, fontproperties=simsun)
    ax.set_xlabel("扫描速率（K/min）", fontproperties=simsun)
    for label in ax.get_xticklabels():
        label.set_fontproperties(times_bold)
        label.set_color("black")
    for label in ax.get_yticklabels():
        label.set_fontproperties(simsun_bold)
        label.set_color("black")
        # SimSun 字库中的摄氏度字形可用，但没有独立粗体文件；用细描边保持宋体轮廓并实现加粗。
        label.set_path_effects([patheffects.withStroke(linewidth=0.65, foreground="black")])
    ax.tick_params(direction="in", length=8, width=2, labelsize=22)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(2)
        spine.set_color("black")

    legend = ax.legend(
        handles=[Patch(facecolor=COLORS[n], edgecolor="none", label=f"n={n}") for n in range(4)],
        ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.03),
        prop=times,
        handlelength=1.3, columnspacing=1.2,
    )
    for text in legend.get_texts():
        text.set_color("black")

    fig.savefig(out_png, dpi=300, facecolor="white")
    fig.savefig(out_svg, format="svg", facecolor="white")
    plt.close(fig)
    print(f"已生成：{out_png}")
    print(f"已生成：{out_svg}")


if __name__ == "__main__":
    draw(read_rows())
