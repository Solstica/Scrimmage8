import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


module = Path(__file__).resolve().parents[1]
tables = module / "tables"
figures = module / "figures"
width, dpi = 180 / 25.4, 300
colors = {2: "#0072B2", 5: "#D55E00", 10: "#009E73"}
markers = {2: "o", 5: "s", 10: "^"}
names = ["潜热需求", "约束裕量", "相变响应", "达标边界"]

plt.rcParams.update({
    "font.family": ["Times New Roman", "SimSun"],
    "mathtext.fontset": "stix", "axes.unicode_minus": False,
    "font.size": 8.5, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "axes.linewidth": 0.75,
    "text.color": "#333333", "axes.labelcolor": "#333333",
    "xtick.color": "#333333", "ytick.color": "#333333",
    "svg.fonttype": "none", "savefig.facecolor": "white",
})


def save_data(name, data):
    tables.mkdir(exist_ok=True)
    data.to_csv(tables / f"{name}.csv", index=False, encoding="utf-8-sig")


def make_data(ref_root):
    res = pd.read_csv(module / "results/q4_result.csv").sort_values("扫描速率（K/min）")
    check = pd.read_csv(module / "results/q4_validation.csv")
    assert (res["状态"] == "OK").all()
    latent, capacity, boundary = [], [], []
    for _, row in res.iterrows():
        v, L, a = row["扫描速率（K/min）"], row["潜热（kJ/kg）"], row["最小放热倍率"]
        points = check[check["扫描速率（K/min）"] == v].sort_values("放热倍率")
        t0 = points.loc[points["放热倍率"] == 1, "热安全时间（s）"].item()
        target, cap = row["Q3基准时间（s）"], row["Q4负重上限（s）"]
        t0 = min(t0, cap)
        t4 = row["Q4实际时间（s）"]
        latent.append([v, L, a * L, (a - 1) * L, row["最小提高比例（%）"]])
        capacity.append([v, t0, target, t4, cap, t4 - t0, cap - t4])
        for _, p in points.iterrows():
            alpha, thermal = p["放热倍率"], p["热安全时间（s）"]
            role = "采样"
            if alpha == row["二分下界"]:
                role = "下界"
            if alpha == row["二分上界"]:
                role = "上界"
            margin = min(thermal, cap) - target
            boundary.append([v, alpha, margin, thermal - target, role,
                             1000 * margin if role != "采样" else np.nan])
    save_data("潜热需求", pd.DataFrame(latent, columns=["扫描速率（K/min）", "原始潜热（kJ/kg）",
              "强化潜热（kJ/kg）", "新增潜热（kJ/kg）", "提升比例（%）"]))
    save_data("约束裕量", pd.DataFrame(capacity, columns=["扫描速率（K/min）", "原始时间（s）",
              "Q3目标（s）", "Q4实际时间（s）", "负重上限（s）", "恢复时间（s）", "负重余量（s）"]))
    save_data("达标边界", pd.DataFrame(boundary, columns=["扫描速率（K/min）", "放热倍率",
              "实际裕量（s）", "热安全裕量（s）", "边界角色", "边界裕量（ms）"]))

    # 使用原求解所用的 Q1 接口，不复制 DSC 预处理。
    spec = importlib.util.spec_from_file_location("q1_model", ref_root / "modules/20_q1/code/q1.py")
    q1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q1)
    T, p, _, area = q1.read_dsc(ref_root / "data/raw/附件1 放热能力数据.xlsx")
    w = np.array([q1.get_w(t, T, p, area) for t in T])
    # 仅是显示网格，端点来自已有验证倍率，包含各个最优切片。
    alpha = np.unique(np.r_[np.linspace(check["放热倍率"].min(), check["放热倍率"].max(), 61),
                            res["最小放热倍率"].to_numpy()])
    temp, mult = np.meshgrid(T, alpha)
    data = pd.DataFrame({"温度（℃）": temp.ravel(), "放热倍率": mult.ravel()})
    for _, row in res.iterrows():
        v, L = row["扫描速率（K/min）"], row["潜热（kJ/kg）"]
        assert abs(area * 60 / v / 1000 - L) < 1e-6
        data[f"v={v:g}有效比热（kJ/(kg·K)）"] = (q1.c[1] / 1000 + mult * L * w).ravel()
    # 独立参考线系列只有三点，空白表示该列系列已结束。
    data["参考速率（K/min）"] = pd.Series(res["扫描速率（K/min）"].to_numpy())
    data["参考倍率"] = pd.Series(res["最小放热倍率"].to_numpy())
    save_data("相变响应", data)


def style(ax, grid="x"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#777777")
    ax.set_axisbelow(True)
    ax.grid(axis=grid, color="#E5E7EB", linewidth=0.35)
    ax.tick_params(length=3, width=0.75)


def note(fig, text):
    fig.text(0.08, 0.035, text, fontsize=8, va="bottom", color="#555555")
    fig.text(0.98, 0.982, "DRAFT · 15 ℃目标", fontsize=8, ha="right", va="top", color="#777777")


def draw_latent(data):
    fig, ax = plt.subplots(figsize=(width, 90 / 25.4))
    fig.subplots_adjust(left=0.14, right=0.97, bottom=0.23, top=0.81)
    for y, row in data.iterrows():
        v = row["扫描速率（K/min）"]
        L, enhanced = row["原始潜热（kJ/kg）"], row["强化潜热（kJ/kg）"]
        c, m = colors[v], markers[v]
        ax.plot([L, enhanced], [y, y], color=c, linewidth=2, alpha=0.6)
        ax.scatter(L, y, facecolor="white", edgecolor=c, marker=m, s=34, zorder=3)
        ax.scatter(enhanced, y, color=c, marker=m, s=34, zorder=3)
        ax.annotate(f"{L:.2f}", (L, y), xytext=(-8, 0), textcoords="offset points", ha="right", va="center")
        ax.annotate(f"{enhanced:.2f}", (enhanced, y), xytext=(8, 0), textcoords="offset points", ha="left", va="center")
        ax.annotate(f"+{row['新增潜热（kJ/kg）']:.2f} kJ/kg  /  +{row['提升比例（%）']:.2f}%",
                    ((L + enhanced) / 2, y), xytext=(0, 12), textcoords="offset points", ha="center", color=c)
    ax.set_yticks(range(len(data)), [f"v = {v:g}" for v in data["扫描速率（K/min）"]])
    ax.set_ylim(2.5, -0.65)
    ax.set_xlim(0, 1020)
    ax.set_xticks(np.arange(0, 1001, 200))
    ax.set_xlabel("单位质量潜热（kJ/kg）")
    ax.set_ylabel("扫描速率（K/min）")
    style(ax)
    handles = [Line2D([], [], marker="o", color="#555555", linestyle="none", markerfacecolor="white", label="原始潜热 L"),
               Line2D([], [], marker="o", color="#555555", linestyle="none", label="强化潜热 α*L")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.12, 0.94), ncol=2, frameon=False)
    note(fig, "相对提升最大不等于绝对潜热需求最大；三个速率为离散条件，不作趋势拟合。")
    return fig


def draw_capacity(data):
    fig, ax = plt.subplots(figsize=(width, 100 / 25.4))
    fig.subplots_adjust(left=0.14, right=0.96, bottom=0.27, top=0.80)
    cap = data["负重上限（s）"].iloc[0]
    ax.axvline(cap, color="#777777", linestyle=":", linewidth=0.9)
    for y, row in data.iterrows():
        v, c = row["扫描速率（K/min）"], colors[row["扫描速率（K/min）"]]
        t0, t4 = row["原始时间（s）"], row["Q4实际时间（s）"]
        ax.plot([t0, t4], [y, y], color=c, linewidth=2)
        ax.plot([t4, cap], [y, y], color="#999999", linewidth=1, linestyle="--")
        ax.scatter(t0, y, s=30, facecolor="white", edgecolor=c, marker=markers[v], zorder=3)
        ax.scatter(t4, y, s=75, color=c, marker="*", zorder=4)
        ax.scatter(cap, y, s=26, color="#777777", marker="D", zorder=3)
        for x, label in [(t0, f"{t0:.2f}"), (t4, f"{t4:.2f}")]:
            ax.annotate(label, (x, y), xytext=(0, -16), textcoords="offset points", ha="center")
        ax.annotate(f"恢复 {row['恢复时间（s）']:.2f} s", ((t0 + t4) / 2, y),
                    xytext=(0, 12), textcoords="offset points", ha="center", color=c)
        ax.annotate(f"余量 {row['负重余量（s）']:.2f} s", ((t4 + cap) / 2, y),
                    xytext=(0, 12), textcoords="offset points", ha="center", color="#666666")
    ax.set_yticks(range(len(data)), [f"v = {v:g}" for v in data["扫描速率（K/min）"]])
    ax.set_ylim(2.8, -0.6)
    ax.set_xlim(130, 850)
    ax.set_xticks(np.arange(200, 801, 100))
    ax.set_xlabel("实际坚持时间（s）")
    ax.set_ylabel("扫描速率（K/min）")
    style(ax)
    handles = [Line2D([], [], marker="o", color="#555555", linestyle="none", markerfacecolor="white", label="原始方案"),
               Line2D([], [], marker="*", color="#555555", linestyle="none", markersize=8, label="Q4 达标值"),
               Line2D([], [], marker="D", color="#777777", linestyle="none", label=f"负重上限 {cap:.2f} s")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.10, 0.93), ncol=3, frameon=False)
    note(fig, "Q4 达标值与同速率 Q3 目标在此尺度重合，毫秒差见达标边界图。\n实际时间取热安全时间与负重上限的较小值；余量不等于已实现收益。")
    return fig


def draw_material(data):
    fig, axes = plt.subplots(1, 3, figsize=(width, 102 / 25.4), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.09, right=0.86, bottom=0.29, top=0.85, wspace=0.12)
    T, alpha = np.sort(data["温度（℃）"].unique()), np.sort(data["放热倍率"].unique())
    refs = data[["参考速率（K/min）", "参考倍率"]].dropna()
    cols = [f"v={v:g}有效比热（kJ/(kg·K)）" for v in refs.iloc[:, 0]]
    zmax = data[cols].max().max()
    levels = np.linspace(0, np.ceil(zmax / 20) * 20, 15)
    for ax, (_, row), col, letter in zip(axes, refs.iterrows(), cols, "abc"):
        v, a = row.iloc[0], row.iloc[1]
        Z = data.pivot(index="放热倍率", columns="温度（℃）", values=col).to_numpy()
        pcm = ax.contourf(T, alpha, Z, levels=levels, cmap="cividis", vmin=0, vmax=levels[-1])
        lines = ax.contour(T, alpha, Z, levels=np.arange(40, levels[-1], 40), colors="white", linewidths=0.55, alpha=0.8)
        ax.clabel(lines, fmt="%d", fontsize=7, inline=True)
        peak = T[Z[-1].argmax()]
        ax.axvline(peak, color="white", linestyle=":", linewidth=1)
        ax.spines["top"].set_visible(False)
        ax.axhline(a, color="white", linewidth=2.5, clip_on=False, zorder=5)
        ax.axhline(a, color="#1F2937", linestyle="--", linewidth=1, clip_on=False, zorder=6)
        ax.text(0.03, 1.035, f"({letter})  v = {v:g} K/min", transform=ax.transAxes, fontsize=9)
        ax.text(0.03, -0.20, f"α* = {a:.4f}", transform=ax.transAxes, color=colors[v], fontsize=8.5)
        ax.set_xticks([14, 18, 22, 26])
        ax.set_xlim(T.min(), T.max())
        ax.set_ylim(alpha.min(), alpha.max())
        ax.set_yticks([1.0, 1.5, 2.0, 2.5])
        ax.set_xlabel("温度（℃）")
    axes[0].set_ylabel("放热倍率 α")
    cax = fig.add_axes([0.885, 0.29, 0.019, 0.56])
    cb = fig.colorbar(pcm, cax=cax, ticks=np.arange(0, levels[-1] + 1, 40))
    cb.set_label("有效比热（kJ/(kg·K)）", fontsize=8.5)
    note(fig, f"横虚线：当前达标倍率；竖点线：共同峰温 {peak:.3f} ℃。\n材料本构切片（相变推进时），不是固液相界或热安全可行域。")
    return fig


def draw_boundary(data):
    fig, axes = plt.subplots(1, 2, figsize=(width, 103 / 25.4), gridspec_kw={"width_ratios": [1.3, 1]})
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.29, top=0.80, wspace=0.38)
    ax, zoom = axes
    ax.axhline(0, color="#555555", linewidth=0.9)
    zoom.axvline(0, color="#555555", linewidth=0.9)
    for y, (v, group) in enumerate(data.groupby("扫描速率（K/min）", sort=True)):
        g = group.sort_values("放热倍率")
        c, m = colors[v], markers[v]
        ax.plot(g["放热倍率"], g["实际裕量（s）"], color=c, linewidth=0.8, linestyle=":")
        ax.scatter(g["放热倍率"], g["实际裕量（s）"], color=c, marker=m, s=20, label=f"v = {v:g}", zorder=3)
        upper = g[g["边界角色"] == "上界"].iloc[0]
        ax.scatter(upper["放热倍率"], upper["实际裕量（s）"], s=85, color=c, edgecolor="white", linewidth=0.6, marker="*", zorder=5)
        clipped = g[g["热安全裕量（s）"] > g["实际裕量（s）"] + 1e-8]
        for _, row in clipped.iterrows():
            x, real, thermal = row["放热倍率"], row["实际裕量（s）"], row["热安全裕量（s）"]
            ax.plot([x, x], [real, thermal], color=c, linewidth=1)
            ax.scatter(x, thermal, s=25, facecolor="white", edgecolor=c, marker=m, zorder=3)
            ax.annotate("仅热安全\n受负重截限", (x, (real + thermal) / 2), xytext=(6, 0),
                        textcoords="offset points", fontsize=7.5, va="center", color=c)
        low = g[g["边界角色"] == "下界"]["边界裕量（ms）"].item()
        high = upper["边界裕量（ms）"]
        zoom.plot([low, high], [y, y], color=c, linewidth=1.5)
        zoom.scatter(low, y, color=c, marker="x", s=35, zorder=3)
        zoom.scatter(high, y, color=c, marker="o", s=25, zorder=3)
        for x, offset, align in [(low, -3, "right"), (high, 3, "left")]:
            zoom.annotate(f"{x:+.3f}", (x, y), xytext=(offset, 12), textcoords="offset points", ha=align, color=c)
    ax.set_xlabel("放热倍率 α")
    ax.set_ylabel("相对 Q3 目标的时间裕量（s）")
    ax.set_xlim(0.94, 2.72)
    ax.set_ylim(-210, 275)
    ax.set_xticks([1, 1.5, 2, 2.5])
    ax.set_yticks([-200, -100, 0, 100, 200])
    ax.legend(loc="upper left", frameon=False, title="扫描速率（K/min）", title_fontsize=7.5)
    zoom.set_yticks([0, 1, 2], ["v = 2", "v = 5", "v = 10"])
    zoom.set_xlim(-21, 13)
    zoom.set_xticks([-20, -10, 0, 10])
    zoom.set_ylim(2.55, -0.65)
    zoom.set_xlabel("端点实际时间裕量（ms）")
    style(ax, "y")
    style(zoom, "x")
    ax.text(0, 1.07, "(a) 倍率响应与负重截限", transform=ax.transAxes, fontsize=9)
    zoom.text(0, 1.07, "(b) 二分端点局部放大", transform=zoom.transAxes, fontsize=9)
    zoom.text(0.02, 0.05, "× 下界未达标   ● 上界达标", transform=zoom.transAxes, fontsize=7.5)
    bounds = data[data["边界角色"] != "采样"].groupby("扫描速率（K/min）")["放热倍率"].agg(["min", "max"])
    span = (bounds["max"] - bounds["min"]).max()
    note(fig, f"虚线仅连接已算点，未拟合或补点；★ 为当前达标倍率。\n最大二分倍率区间宽度约 {span:.2e}；不是置信区间，也不代表物理精度。")
    return fig


drawers = [draw_latent, draw_capacity, draw_material, draw_boundary]


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--重绘":
        pass
    else:
        root = Path(sys.argv[1]) if len(sys.argv) > 1 else module.parents[1]
        make_data(root)
    figures.mkdir(exist_ok=True)
    for name, draw in zip(names, drawers):
        fig = draw(pd.read_csv(tables / f"{name}.csv"))
        fig.savefig(figures / f"{name}.png", dpi=dpi)
        fig.savefig(figures / f"{name}.svg")
        plt.close(fig)
        print(f"已生成：{name}（PNG / SVG / CSV）")


if __name__ == "__main__":
    main()
