import csv
import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


根目录 = Path(__file__).resolve().parents[3]
模块路径 = Path(__file__).with_name("q3.py")
模块规格 = importlib.util.spec_from_file_location("问题三原程序", 模块路径)
问题三 = importlib.util.module_from_spec(模块规格)
模块规格.loader.exec_module(问题三)

输出目录 = 根目录 / "modules" / "40_q3" / "results" / "EXPERIMENT" / "低速扫描重审"
粗扫描速率 = [0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 5.0, 10.0]
时间步长 = 0.25
模态数 = 40
积分点数 = 160
切换精度 = 0.01


def 保存表格(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def 更新潜热审查():
    with (输出目录 / "粗扫描方案.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    潜热行 = []
    for v in 粗扫描速率:
        row = next(item for item in rows if float(item["扫描速率（K/min）"]) == v)
        L = float(row["潜热（kJ/kg）"])
        if L > 260.0:
            结论 = "超出本次商业PCM对照上限，仅作数学诊断"
        else:
            结论 = "未超出本次商业PCM对照上限"
        潜热行.append([v, L, 260.0, 结论])
    保存表格(
        输出目录 / "潜热数量级审查.csv",
        ["扫描速率（K/min）", "反演潜热（kJ/kg）", "商业PCM对照上限（kJ/kg）", "数量级结论"],
        潜热行,
    )


def 求双阈值时间(v, d3, b1, b2, T_dsc, p_dsc, xi_dsc, area):
    L_pcm = area * 60.0 / v
    h0 = 问题三.get_h(问题三.T_b)
    b3 = 问题三.basis3(d3, h0, 模态数, 积分点数)
    b3_initial = 问题三.project(
        np.full(积分点数, 问题三.T_b)
        - 问题三.w3(b3["y"], 问题三.T_b, h0, d3),
        b3,
    )
    state = {
        "t": 0.0,
        "T12": 问题三.T_b,
        "T23": 问题三.T_b,
        "b1": np.zeros(模态数),
        "b2": np.zeros(模态数),
        "b3": b3_initial,
        "basis3": b3,
        "h3": h0,
        "xi": 0.0,
    }
    t15 = None
    t10 = None
    max_cond = 0.0
    max_res = 0.0

    while state["t"] < 7200.0 and t10 is None:
        old_t = state["t"]
        old_T = 问题三.inner_surface(state, b1)
        state, cond, res = 问题三.modal_step(
            state,
            时间步长,
            b1,
            b2,
            d3,
            模态数,
            积分点数,
            T_dsc,
            p_dsc,
            xi_dsc,
            area,
            L_pcm,
        )
        new_T = 问题三.inner_surface(state, b1)
        max_cond = max(max_cond, cond)
        max_res = max(max_res, res)
        if t15 is None:
            t15 = 问题三.first_cross(old_t, state["t"], old_T, new_T, 15.0)
        t10 = 问题三.first_cross(old_t, state["t"], old_T, new_T, 10.0)

    if t15 is None or t10 is None:
        raise RuntimeError(
            f"v={v:g} K/min, d3={1000*d3:g} mm在7200 s内未达到两个阈值"
        )
    return t15, t10, L_pcm / 1000.0, max_cond, max_res


def 限制因素(tT, tW):
    return "热安全" if tT <= tW else "负重"


def 最优层数(rows, key):
    return max(rows, key=lambda row: row[key])["新增层数"]


def 画图(rows):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    rates = [1.0, 1.25, 1.5, 1.75, 2.0]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.8), sharex=True, sharey=True)
    axes = axes.ravel()

    for ax, v in zip(axes, rates):
        group = [row for row in rows if abs(row["扫描速率"] - v) < 1e-12]
        n = np.array([row["新增层数"] for row in group])
        t15 = np.array([row["15℃时间"] for row in group])
        t10 = np.array([row["10℃时间"] for row in group])
        tW = np.array([row["负重时间"] for row in group])
        ax.plot(n, t15, "o-", label="15℃时间", color="#1f77b4")
        ax.plot(n, t10, "s-", label="10℃时间", color="#d95f02")
        ax.plot(n, tW, "^-", label="负重时间", color="#2b8c4b")

        for thermal, color in [(t15, "#1f77b4"), (t10, "#d95f02")]:
            active = thermal >= tW
            ax.scatter(n[active], tW[active], s=75, facecolors="none", edgecolors=color, linewidths=1.6)

        best15 = 最优层数(group, "15℃有效时间")
        best10 = 最优层数(group, "10℃有效时间")
        ax.axvline(best15, color="#1f77b4", alpha=0.18, linewidth=5)
        ax.axvline(best10, color="#d95f02", alpha=0.18, linewidth=5)
        ax.set_title(f"扫描速率 {v:g} K/min")
        ax.set_xticks([0, 1, 2, 3])
        ax.grid(alpha=0.25)

    axes[5].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.92, 0.13), frameon=False)
    fig.supxlabel("新增层数")
    fig.supylabel("时间（s）")
    fig.suptitle("新增层数与热安全、负重时间（空心圆表示负重约束已活动）")
    fig.tight_layout(rect=[0.03, 0.04, 0.98, 0.94])
    fig.savefig(输出目录 / "层数时间曲线.png", dpi=220)
    plt.close(fig)


def main():
    输出目录.mkdir(parents=True, exist_ok=True)
    T_dsc, p_dsc, xi_dsc, area = 问题三.read_dsc(
        根目录 / "data" / "raw" / "附件1 放热能力数据.xlsx"
    )
    n_all, d3_all, mass_all, cost_all, tW_all = 问题三.get_candidates()
    b1 = 问题三.basis1(模态数, 积分点数)
    b2 = 问题三.basis2(模态数, 积分点数)
    cache = {}
    worst_cond = 0.0
    worst_res = 0.0

    def 计算速率(v):
        nonlocal worst_cond, worst_res
        key = round(float(v), 10)
        if key in cache:
            return cache[key]
        group = []
        for i, n in enumerate(n_all):
            t15, t10, L_pcm, cond, res = 求双阈值时间(
                v, d3_all[i], b1, b2, T_dsc, p_dsc, xi_dsc, area
            )
            worst_cond = max(worst_cond, cond)
            worst_res = max(worst_res, res)
            row = {
                "扫描速率": float(v),
                "潜热": L_pcm,
                "新增层数": int(n),
                "外层厚度": d3_all[i] * 1000.0,
                "总厚度": (问题三.d1 + 问题三.d2 + d3_all[i]) * 1000.0,
                "服装质量": mass_all[i],
                "材料费用": cost_all[i],
                "15℃时间": t15,
                "10℃时间": t10,
                "负重时间": tW_all[i],
                "15℃有效时间": min(t15, tW_all[i]),
                "10℃有效时间": min(t10, tW_all[i]),
                "15℃限制因素": 限制因素(t15, tW_all[i]),
                "10℃限制因素": 限制因素(t10, tW_all[i]),
            }
            group.append(row)
            print(
                f"v={v:.6g}, n={n}: t15={t15:.3f}, t10={t10:.3f}, "
                f"tW={tW_all[i]:.3f}"
            )
        cache[key] = group
        return group

    for v in 粗扫描速率:
        计算速率(v)

    切换 = []

    def 细分(lo, hi, key, 口径):
        left = 最优层数(计算速率(lo), key)
        right = 最优层数(计算速率(hi), key)
        if left == right:
            return
        if hi - lo <= 切换精度:
            切换.append([口径, lo, hi, left, right, hi - lo])
            return
        mid = 0.5 * (lo + hi)
        middle = 最优层数(计算速率(mid), key)
        if left != middle:
            细分(lo, mid, key, 口径)
        if middle != right:
            细分(mid, hi, key, 口径)

    for key, 口径 in [("15℃有效时间", "15℃"), ("10℃有效时间", "10℃")]:
        for lo, hi in zip(粗扫描速率[:-1], 粗扫描速率[1:]):
            if 最优层数(计算速率(lo), key) != 最优层数(计算速率(hi), key):
                细分(lo, hi, key, 口径)

    粗结果 = [row for v in 粗扫描速率 for row in 计算速率(v)]
    header = [
        "扫描速率（K/min）",
        "潜热（kJ/kg）",
        "新增层数",
        "外层厚度（mm）",
        "总厚度（mm）",
        "服装质量（kg）",
        "材料费用（元）",
        "15℃时间（s）",
        "10℃时间（s）",
        "负重时间（s）",
        "15℃有效时间（s）",
        "10℃有效时间（s）",
        "15℃限制因素",
        "10℃限制因素",
    ]
    keys = [
        "扫描速率",
        "潜热",
        "新增层数",
        "外层厚度",
        "总厚度",
        "服装质量",
        "材料费用",
        "15℃时间",
        "10℃时间",
        "负重时间",
        "15℃有效时间",
        "10℃有效时间",
        "15℃限制因素",
        "10℃限制因素",
    ]
    保存表格(输出目录 / "粗扫描方案.csv", header, [[row[k] for k in keys] for row in 粗结果])

    best_rows = []
    for v in 粗扫描速率:
        group = 计算速率(v)
        for key, 口径 in [("15℃有效时间", "15℃"), ("10℃有效时间", "10℃")]:
            best = max(group, key=lambda row: row[key])
            best_rows.append(
                [
                    v,
                    口径,
                    best["新增层数"],
                    best["外层厚度"],
                    best[key],
                    best[f"{口径}时间"],
                    best["负重时间"],
                    best[f"{口径}限制因素"],
                ]
            )
    保存表格(
        输出目录 / "粗扫描最优方案.csv",
        ["扫描速率（K/min）", "阈值口径", "最优新增层数", "外层厚度（mm）", "最大有效时间（s）", "热安全时间（s）", "负重时间（s）", "活动限制"],
        best_rows,
    )
    保存表格(
        输出目录 / "切换区间.csv",
        ["阈值口径", "区间下界（K/min）", "区间上界（K/min）", "下界最优层数", "上界最优层数", "区间宽度（K/min）"],
        sorted(切换, key=lambda row: (row[0], row[1])),
    )

    更新潜热审查()

    图表结果 = [row for row in 粗结果 if row["扫描速率"] in [1.0, 1.25, 1.5, 1.75, 2.0]]
    保存表格(输出目录 / "层数时间曲线数据.csv", header, [[row[k] for k in keys] for row in 图表结果])
    画图(粗结果)

    新增质量 = 问题三.A * 问题三.rho[2] * 问题三.d3_0
    if abs(新增质量 - 0.148689) > 1e-9:
        raise RuntimeError(f"新增一层质量核查失败：{新增质量:.9f} kg")
    print(f"新增一层质量={新增质量:.6f} kg")
    print(f"最大条件数={worst_cond:.6e}，最大热流残差={worst_res:.6e} W/m2")


if __name__ == "__main__":
    main()
