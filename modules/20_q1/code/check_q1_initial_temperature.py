import csv
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import q1


T0_CASES = [27.0, 30.0, 33.0, 37.0]
V = 5.0
DT = 0.25
M = 40
NQ = 160


def solve_case(T0, T_dsc, p_dsc, xi_dsc, area):
    L_pcm = area * 60.0 / V
    b1 = q1.basis1(M, NQ)
    b2 = q1.basis2(M, NQ)

    # 将统一衣料初温投影到正式模型的三层模态基底。
    b1_initial = q1.project(
        np.full(NQ, T0) - q1.w1(b1["y"], T0),
        b1,
    )
    h0 = q1.get_h(T0)
    b3 = q1.basis3(h0, M, NQ)
    b3_initial = q1.project(
        np.full(NQ, T0) - q1.w3(b3["y"], T0, h0),
        b3,
    )
    state = {
        "t": 0.0,
        "T12": T0,
        "T23": T0,
        "b1": b1_initial,
        "b2": np.zeros(M),
        "b3": b3_initial,
        "basis3": b3,
        "h3": h0,
        "xi": 0.0,
    }

    T_in = q1.inner_surface(state, b1)
    history = [[T0, 0.0, T_in]]
    t15 = None
    t10 = None

    while state["t"] < 1800.0 and t10 is None:
        old_t = state["t"]
        old_T = T_in
        state, _, _ = q1.modal_step(
            state,
            DT,
            b1,
            b2,
            M,
            NQ,
            T_dsc,
            p_dsc,
            xi_dsc,
            area,
            L_pcm,
        )
        T_in = q1.inner_surface(state, b1)
        if not np.isfinite(T_in):
            raise RuntimeError(f"T0={T0:g} degC produced a non-finite T_in")
        if t15 is None:
            t15 = q1.first_cross(old_t, state["t"], old_T, T_in, 15.0)
        t10 = q1.first_cross(old_t, state["t"], old_T, T_in, 10.0)
        history.append([T0, state["t"], T_in])

    if t15 is None or t10 is None:
        raise RuntimeError(f"T0={T0:g} degC did not reach both thresholds")
    return t15, t10, history


def save_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def draw(out, history):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00"]

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    data = np.asarray(history)
    for T0, color in zip(T0_CASES, colors):
        rows = data[data[:, 0] == T0]
        ax.plot(rows[:, 1], rows[:, 2], lw=2.0, color=color, label=rf"$T_0={T0:g}^\circ$C")
    ax.axhline(15.0, color="#444444", lw=1.4, ls="--", label=r"$15^\circ$C阈值")
    ax.set_xlabel("时间（s）")
    ax.set_ylabel(r"贴身侧温度 $T_{\rm in}$（$^\circ$C）")
    ax.set_ylim(8.0, 38.5)
    ax.set_xlim(0.0, float(data[:, 1].max()))
    ax.grid(True, color="#D9D9D9", linewidth=0.7, alpha=0.8)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "q1_initial_temperature_sensitivity.png", dpi=300)
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parents[3]
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)

    T_dsc, p_dsc, xi_dsc, area = q1.read_dsc(
        root / "data" / "raw" / "附件1 放热能力数据.xlsx"
    )
    if q1.T_b != 37.0 or min(T0_CASES) <= T_dsc[-1]:
        raise RuntimeError("initial-temperature sensitivity settings do not match the modeler's requirements")

    raw = []
    history = []
    for T0 in T0_CASES:
        t15, t10, rows = solve_case(T0, T_dsc, p_dsc, xi_dsc, area)
        raw.append([T0, t15, t10])
        history.extend(rows)

    ref15, ref10 = raw[-1][1], raw[-1][2]
    results = [
        [T0, t15, t10, 100.0 * (t15 - ref15) / ref15, 100.0 * (t10 - ref10) / ref10]
        for T0, t15, t10 in raw
    ]
    save_csv(
        out / "q1_initial_temperature_results.csv",
        ["衣料初温（℃）", "t15（s）", "t10（s）", "相对37℃的t15变化（%）", "相对37℃的t10变化（%）"],
        results,
    )
    save_csv(
        out / "q1_initial_temperature_plot_data.csv",
        ["衣料初温（℃）", "时间（s）", "贴身侧温度（℃）"],
        history,
    )
    draw(out, history)

    low = results[0]
    analysis = (
        "# 服装初始温度灵敏度\n\n"
        "保持人体边界为 37 ℃，仅改变三层衣料的统一初始温度；"
        "采用基准扫描速率 5 K/min、dt=0.25 s、M=40。\n\n"
        f"衣料初温由 37 ℃ 降至 27 ℃ 时，t15 由 {ref15:.3f} s 变为 {low[1]:.3f} s"
        f"（{low[3]:+.2f}%），t10 由 {ref10:.3f} s 变为 {low[2]:.3f} s"
        f"（{low[4]:+.2f}%）。该结果只用于评价衣料预热初温的影响，"
        "不把 37 ℃ 解释为附件给定的衣料初温。\n"
    )
    (out / "analysis.md").write_text(analysis, encoding="utf-8")

    for row in results:
        print(
            f"T0={row[0]:g} degC: t15={row[1]:.3f} s, t10={row[2]:.3f} s, "
            f"relative={row[3]:+.2f}%/{row[4]:+.2f}%"
        )


if __name__ == "__main__":
    main()
