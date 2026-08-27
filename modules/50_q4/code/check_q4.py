#!/usr/bin/env python3
import csv
from pathlib import Path

import q4


root = Path(__file__).resolve().parents[3]
result_file = root / "modules" / "50_q4" / "results" / "q4_result.csv"
out_file = root / "modules" / "50_q4" / "results" / "q4_validation.csv"


def main():
    with result_file.open(encoding="utf-8-sig") as f:
        base = next(csv.DictReader(f))
    alpha0 = float(base["最小放热倍率"])
    tT0 = float(base["热安全时间（s）"])

    rows = []
    model = q4.prepare(q4.load_q1(), q4.dt, q4.M, q4.nq)
    forward = lambda alpha, horizon: q4.get_tT(alpha, horizon, model)
    for alpha in [1.0, 1.5, alpha0 - q4.alpha_tol, alpha0, 2.0]:
        tT, cond, res = q4.exact_tT(alpha, q4.t3_best, forward)
        rows.append(["单调性/边界", "dt=0.25 s, M=40", alpha, tT, alpha - alpha0, tT - q4.t3_best, cond, res])

    for setting, step, modes, quad in [
        ("dt=0.125 s, M=40", 0.125, 40, 160),
        ("dt=0.25 s, M=60", 0.25, 60, 160),
    ]:
        ans = q4.solve(step=step, modes=modes, quad=quad, save=False)
        alpha = ans["最小放热倍率"]
        tT = ans["热安全时间（s）"]
        rows.append([
            "离散稳定性",
            setting,
            alpha,
            tT,
            alpha - alpha0,
            tT - tT0,
            ans["最大条件数"],
            ans["最大热流残差（W/m2）"],
        ])

    with out_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "检查",
            "设置",
            "放热倍率",
            "热安全时间（s）",
            "倍率相对正式解差",
            "时间差（s）",
            "最大条件数",
            "最大热流残差（W/m2）",
        ])
        writer.writerows(rows)

    print(f"验证结果: {out_file}")


if __name__ == "__main__":
    main()
