#!/usr/bin/env python3
import csv
import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


root = Path(__file__).resolve().parents[3]
result_file = root / "modules" / "50_q4" / "results" / "q4_result.csv"
dsc_file = root / "data" / "raw" / "附件1 放热能力数据.xlsx"
figure_dir = root / "modules" / "50_q4" / "figures"
table_dir = root / "modules" / "50_q4" / "tables"

colors = ["#0072B2", "#D55E00", "#009E73"]


def load_q1():
    path = root / "modules" / "20_q1" / "code" / "q1.py"
    spec = importlib.util.spec_from_file_location("q1_model", path)
    q1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q1)
    return q1


def read_result():
    with result_file.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return sorted(
        [
            {
                "v": float(row["扫描速率（K/min）"]),
                "L": float(row["潜热（kJ/kg）"]),
                "alpha": float(row["最小放热倍率"]),
                "increase": float(row["最小提高比例（%）"]),
            }
            for row in rows
        ],
        key=lambda row: row["v"],
    )


def save_data(rows, T, curves):
    table_dir.mkdir(parents=True, exist_ok=True)
    path = table_dir / "第四问演示图数据.csv"
    header = ["扫描速率（K/min）", "最小提高比例（%）", "温度（℃）"]
    header += [f"v={row['v']:g}有效比热（kJ/(kg·K)）" for row in rows]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for i, temp in enumerate(T):
            left = [rows[i]["v"], rows[i]["increase"]] if i < len(rows) else ["", ""]
            writer.writerow(left + [temp] + [curve[i] for curve in curves])
    return path


def draw(rows, T, p, curves):
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "font.size": 10.5,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
        }
    )

    v = np.array([row["v"] for row in rows])
    increase = np.array([row["increase"] for row in rows])
    half = T[p >= 0.5 * np.max(p)]
    T_peak = T[np.argmax(p)]

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), constrained_layout=True)
    ax1, ax2 = axes

    ax1.plot(v, increase, color="#667085", linewidth=1.4, zorder=1)
    for i, row in enumerate(rows):
        ax1.scatter(row["v"], row["increase"], s=66, color=colors[i], edgecolor="white", linewidth=1.0, zorder=2)
        ax1.annotate(
            f"{row['increase']:.2f}%",
            (row["v"], row["increase"]),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            color=colors[i],
            fontweight="bold",
        )
    ax1.set_title("(a) 不同扫描速率下的最小放热提升", loc="left", fontweight="bold")
    ax1.set_xlabel("DSC 扫描速率  v（K/min）")
    ax1.set_ylabel("最小提高比例  100(α*−1)（%）")
    ax1.set_xticks(v)
    ax1.set_ylim(0, max(increase) * 1.22)
    ax1.grid(axis="y", color="#D0D5DD", linewidth=0.7, alpha=0.65)

    ax2.axvspan(half[0], half[-1], color="#98A2B3", alpha=0.16, linewidth=0, label="主相变区间")
    for i, (row, curve) in enumerate(zip(rows, curves)):
        ax2.plot(
            T,
            curve,
            color=colors[i],
            linewidth=2.0,
            label=f"v={row['v']:g} K/min，α*={row['alpha']:.3f}",
        )
    ax2.axvline(T_peak, color="#475467", linestyle="--", linewidth=1.1)
    ax2.annotate(
        f"峰温 {T_peak:.2f} ℃",
        (T_peak, max(curve.max() for curve in curves)),
        xytext=(8, -8),
        textcoords="offset points",
        va="top",
        color="#475467",
    )
    ax2.set_title("(b) 最优倍率下的相变有效比热", loc="left", fontweight="bold")
    ax2.set_xlabel("温度  T（℃）")
    ax2.set_ylabel("有效比热  c_eff（kJ/(kg·K)）")
    ax2.set_xlim(T.min(), T.max())
    ax2.set_ylim(bottom=0)
    ax2.grid(axis="y", color="#D0D5DD", linewidth=0.7, alpha=0.65)
    ax2.legend(frameon=False, loc="upper right", fontsize=9)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#667085")
        ax.spines["bottom"].set_color("#667085")
        ax.tick_params(colors="#344054")

    fig.text(0.995, 0.995, "阶段结果 · 演示候选", ha="right", va="top", color="#667085", fontsize=9)
    figure_dir.mkdir(parents=True, exist_ok=True)
    png = figure_dir / "第四问演示图.png"
    svg = figure_dir / "第四问演示图.svg"
    fig.savefig(png, dpi=220, facecolor="white")
    fig.savefig(svg, facecolor="white")
    plt.close(fig)
    return png, svg


def main():
    q1 = load_q1()
    rows = read_result()
    T, p, _, area = q1.read_dsc(dsc_file)
    w = np.array([q1.get_w(temp, T, p, area) for temp in T])
    curves = [q1.c[1] / 1000.0 + row["alpha"] * row["L"] * w for row in rows]

    data = save_data(rows, T, curves)
    png, svg = draw(rows, T, p, curves)
    print(f"已生成：{png}")
    print(f"已生成：{svg}")
    print(f"已生成：{data}")


if __name__ == "__main__":
    main()
