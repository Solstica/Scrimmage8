#!/usr/bin/env python3
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import q4


root = Path(__file__).resolve().parents[3]
result_file = root / "modules/50_q4/results/双阈值结果.csv"
out_file = root / "modules/50_q4/results/双阈值验证.csv"


def check_case(ans):
    if ans["状态"] != "OK":
        return []
    model = q4.prepare(q4.load_q1(), q4.dt, q4.M, q4.nq)
    rows = []
    v = float(ans["扫描速率（K/min）"])
    limit = float(ans["Q4阈值（℃）"])
    target = float(ans["Q3基准时间（s）"])
    low = float(ans["二分下界"])
    alpha0 = float(ans["最小放热倍率"])
    forward = lambda alpha, horizon: q4.get_tT(alpha, v, horizon, limit, model)
    # 复核原始方案和最终边界；alpha=1时只需验证可行域下界。
    points = sorted(set([1.0, low, alpha0]))
    times = []
    sample = {}
    for alpha in points:
        tT, cond, res = q4.exact_tT(alpha, target, forward, q4.dt)
        times.append(tT)
        sample[alpha] = tT
        t_eff = min(tT, float(ans["Q4负重上限（s）"]))
        rows.append([
            v, limit, alpha, tT, t_eff, target,
            t_eff - target, "是" if t_eff >= target else "否", cond, res,
        ])
    if any(b < a for a, b in zip(times, times[1:])):
        raise RuntimeError(f"v={v:g}, 阈值={limit:g}℃ 的热安全时间未保持单调")
    if low > 1.0 and sample[low] >= target:
        raise RuntimeError(f"v={v:g}, 阈值={limit:g}℃ 的二分下界仍可行")
    if min(sample[alpha0], float(ans["Q4负重上限（s）"])) < target:
        raise RuntimeError(f"v={v:g}, 阈值={limit:g}℃ 的二分上界不可行")
    return rows


def main():
    with result_file.open(encoding="utf-8-sig") as f:
        formal = list(csv.DictReader(f))
    # 工况彼此独立，两个进程不改变阈值、步长或检查点。
    with ProcessPoolExecutor(max_workers=2) as pool:
        rows = [row for group in pool.map(check_case, formal) for row in group]

    with out_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "扫描速率（K/min）",
            "Q4阈值（℃）",
            "放热倍率",
            "热安全时间（s）",
            "实际时间（s）",
            "Q3基准时间（s）",
            "时间裕量（s）",
            "满足目标",
            "最大条件数",
            "最大热流残差（W/m2）",
        ])
        writer.writerows(rows)

    print(f"验证结果: {out_file}")


if __name__ == "__main__":
    main()
