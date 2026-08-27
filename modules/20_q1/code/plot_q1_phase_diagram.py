"""Draw the Q1 functional-layer phase-change schematic."""

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


root = Path(__file__).resolve().parents[3]
out = root / "modules" / "20_q1" / "figures"
out.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 传统二元共晶相图结构示意，组分与相界不参与定量计算。
x_e, T_e = 0.58, 14.7
T_A, T_B = 32.0, 29.5
x_alpha, x_beta = 0.10, 0.91

x_left = np.linspace(0.0, x_e, 300)
x_right = np.linspace(x_e, 1.0, 300)
liq_left = T_e + (T_A - T_e) * (1.0 - x_left / x_e) ** 0.72
liq_right = T_e + (T_B - T_e) * ((x_right - x_e) / (1.0 - x_e)) ** 0.78

x_s1 = np.linspace(0.025, x_alpha, 120)
x_s2 = np.linspace(x_beta, 0.985, 120)
T_s1 = 5.0 + (T_e - 5.0) * ((x_s1 - 0.025) / (x_alpha - 0.025)) ** 0.62
T_s2 = T_e - (T_e - 5.0) * ((x_s2 - x_beta) / (0.985 - x_beta)) ** 0.62

fig, ax = plt.subplots(figsize=(9.2, 5.6))

# 相区
ax.fill_between(x_left, liq_left, 35.0, color="#EAF2F8")
ax.fill_between(x_right, liq_right, 35.0, color="#EAF2F8")
ax.fill_between(x_left, T_e, liq_left, color="#F8E3BD")
ax.fill_between(x_right, T_e, liq_right, color="#DDEBD5")
ax.fill_between([x_alpha, x_beta], [5.0, 5.0], [T_e, T_e], color="#E9DDEC")
ax.fill_between(x_s1, 5.0, T_s1, color="#DFECF3")
ax.fill_between(x_s2, 5.0, T_s2, color="#E6EDDF")

# 相界
edge = "#203A59"
ax.plot(x_left, liq_left, color=edge, lw=2.8)
ax.plot(x_right, liq_right, color=edge, lw=2.8)
ax.hlines(T_e, x_alpha, x_beta, color="#8C3438", lw=2.4)
ax.plot(x_s1, T_s1, color="#547284", lw=2.0)
ax.plot(x_s2, T_s2, color="#65795C", lw=2.0)

# 冷却路径：题面约 25℃开始固化，约 14.7℃固化完成。
x_pcm = float(np.interp(25.0, liq_left[::-1], x_left[::-1]))
ax.annotate(
    "",
    xy=(x_pcm, 7.2),
    xytext=(x_pcm, 31.4),
    arrowprops={"arrowstyle": "-|>", "color": "#D07819", "lw": 2.0, "linestyle": "--"},
)
ax.text(x_pcm - 0.015, 31.8, "冷却路径", ha="center", va="bottom", fontsize=10.5, color="#9A5918")

ax.scatter([x_pcm], [25.0], s=64, color="#D07819", edgecolor="white", linewidth=1.2, zorder=5)
ax.annotate(
    "开始固化放热",
    xy=(x_pcm, 25.0),
    xytext=(x_pcm + 0.075, 26.8),
    fontsize=10.5,
    color="#9A5918",
    arrowprops={"arrowstyle": "-", "color": "#D07819", "lw": 1.1},
)
ax.scatter([x_pcm], [T_e], s=64, color="#A33C40", edgecolor="white", linewidth=1.2, zorder=5)
ax.annotate(
    "固化完成",
    xy=(x_pcm, T_e),
    xytext=(x_pcm - 0.13, 12.1),
    fontsize=10.5,
    color="#8C3438",
    arrowprops={"arrowstyle": "-", "color": "#A34A4A", "lw": 1.1},
)

# 相区标签
ax.text(0.52, 31.4, "液态", ha="center", fontsize=16, weight="bold", color=edge)
ax.text(0.20, 20.2, r"液 + 固 $\alpha$", ha="center", fontsize=14, weight="bold", color="#8A5A15")
ax.text(0.81, 20.6, r"液 + 固 $\beta$", ha="center", fontsize=14, weight="bold", color="#45623E")
ax.text(0.59, 9.1, r"固 $\alpha + \beta$", ha="center", fontsize=14, weight="bold", color="#664D70")
ax.text(0.045, 8.9, r"$\alpha$", ha="center", fontsize=15, color="#315A70")
ax.text(0.957, 8.9, r"$\beta$", ha="center", fontsize=15, color="#53684C")

# 共晶点保留为传统相图的必要结构。
ax.scatter([x_e], [T_e], s=76, color="#B54246", edgecolor="white", linewidth=1.3, zorder=5)
ax.annotate(
    "共晶点 E",
    xy=(x_e, T_e),
    xytext=(x_e + 0.035, T_e - 2.3),
    fontsize=10.5,
    color="#8C3438",
    arrowprops={"arrowstyle": "-", "color": "#A34A4A", "lw": 1.1},
)

ax.set_xlim(0.0, 1.0)
ax.set_ylim(5.0, 35.0)
ax.set_xlabel("组分 B 含量", fontsize=12)
ax.set_ylabel("温度", fontsize=12)
ax.set_title("中间功能层相变示意图", fontsize=17, pad=14, weight="bold")
ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_xticklabels(["组分 A", "20%", "40%", "60%", "80%", "组分 B"])
ax.set_yticks([T_e, 25.0])
ax.set_yticklabels(["约 14.7℃", "约 25℃"])
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_linewidth(1.2)
ax.tick_params(axis="both", labelsize=10, width=1.0, length=5)

fig.tight_layout(rect=(0.03, 0.04, 0.98, 0.98))
fig.savefig(out / "q1_phase_diagram.png", dpi=260, bbox_inches="tight")
plt.close(fig)

print(out / "q1_phase_diagram.png")
