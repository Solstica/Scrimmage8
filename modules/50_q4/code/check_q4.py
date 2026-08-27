#!/usr/bin/env python3
import csv
from pathlib import Path

import q4


root = Path(__file__).resolve().parents[3]
result_file = root / "modules" / "50_q4" / "results" / "q4_result.csv"
out_file = root / "modules" / "50_q4" / "results" / "q4_validation.csv"


def main():
    with result_file.open(encoding="utf-8-sig") as f:
        formal = list(csv.DictReader(f))

    model = q4.prepare(q4.load_q1(), q4.dt, q4.M, q4.nq)
    rows = []
    for ans in formal:
        if ans["状态"] != "OK":
            continue
        v = float(ans["扫描速率（K/min）"])
        target = float(ans["Q3基准时间（s）"])
        low = float(ans["二分下界"])
        alpha0 = float(ans["最小放热倍率"])
        forward = lambda alpha, horizon: q4.get_tT(alpha, v, horizon, q4.limit, model)
        points = sorted(set([1.0, 1.5, low, alpha0, 2.0]))
        times = []
        sample = {}
        for alpha in points:
            tT, cond, res = q4.exact_tT(alpha, target, forward, q4.dt)
            times.append(tT)
            sample[alpha] = tT
            rows.append([
                v,
                alpha,
                tT,
                target,
                tT - target,
                "是" if tT >= target else "否",
                cond,
                res,
            ])
        if any(b < a for a, b in zip(times, times[1:])):
            raise RuntimeError(f"v={v:g} K/min 的热安全时间未保持单调")
        if low > 1.0 and sample[low] >= target:
            raise RuntimeError(f"v={v:g} K/min 的二分下界仍可行")
        if sample[alpha0] < target:
            raise RuntimeError(f"v={v:g} K/min 的二分上界不可行")

    with out_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "扫描速率（K/min）",
            "放热倍率",
            "热安全时间（s）",
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
