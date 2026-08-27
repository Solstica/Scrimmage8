import csv
import math
import sys
from pathlib import Path

import q2


root = Path(__file__).resolve().parents[3]
result_dir = root / "modules" / "30_q2" / "results"
out = Path(sys.argv[1]) if len(sys.argv) > 1 else result_dir
out.mkdir(parents=True, exist_ok=True)
T, p, xi, area = q2.read_dsc(root / "data" / "raw" / "附件1 放热能力数据.xlsx")

cases = [
    ("ISO 11079简化", 18.46),
    ("旧PMV关系", 12.1 * math.sqrt(3.0)),
    ("Kuwabara经验", 21.95),
]

rows = []
old = {}
all_result = {}
for name, h in cases:
    q2.h_e = h
    for scan in [2.0, 5.0, 10.0]:
        ans, history, _ = q2.solve_case(scan, 0.25, 40, 160, T, p, xi, area)
        h_nat_max = max(2.38 * abs(row[7] - q2.T_inf) ** 0.25 for row in history)
        all_result[name, scan] = (ans, h_nat_max)
        if name == "旧PMV关系":
            old[scan] = ans

for name, h in cases:
    for scan in [2.0, 5.0, 10.0]:
        ans, h_nat_max = all_result[name, scan]
        ref = old[scan]
        rows.append(
            [
                name,
                h,
                scan,
                ans[1],
                ans[2],
                ans[3],
                ans[2] - ref[2],
                ans[3] - ref[3],
                100.0 * (ans[2] - ref[2]) / ref[2],
                100.0 * (ans[3] - ref[3]) / ref[3],
                h_nat_max,
                ans[5],
            ]
        )

with (out / "外对流核算.csv").open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "外对流模型",
            "h_e（W/(m2 K)）",
            "扫描速率（K/min）",
            "潜热（kJ/kg）",
            "t15（s）",
            "t10（s）",
            "t15较旧值变化（s）",
            "t10较旧值变化（s）",
            "t15较旧值变化（%）",
            "t10较旧值变化（%）",
            "自然支路最大值（W/(m2 K)）",
            "最大热流残差（W/m2）",
        ]
    )
    writer.writerows(rows)

for row in rows:
    print(
        f"{row[0]}, scan={row[2]:g} K/min, t15={row[4]:.3f} s, "
        f"t10={row[5]:.3f} s, relative=({row[8]:.3f}%, {row[9]:.3f}%)"
    )
