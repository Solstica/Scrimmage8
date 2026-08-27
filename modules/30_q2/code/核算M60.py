import csv
from pathlib import Path

import q2


root = Path(__file__).resolve().parents[3]
result_dir = root / "modules" / "30_q2" / "results"

with (result_dir / "计算结果.csv").open(encoding="utf-8-sig") as f:
    formal = {
        float(row["扫描速率（K/min）"]): row
        for row in csv.DictReader(f)
    }

T, p, xi, area = q2.read_dsc(root / "data" / "raw" / "附件1 放热能力数据.xlsx")

rows = []
for scan in [2.0, 5.0, 10.0]:
    ans, _, _ = q2.solve_case(scan, 0.25, 60, 160, T, p, xi, area)
    t15_40 = float(formal[scan]["t15（s）"])
    t10_40 = float(formal[scan]["t10（s）"])
    rows.append(
        [
            scan,
            ans[1],
            t15_40,
            t10_40,
            ans[2],
            ans[3],
            ans[2] - t15_40,
            ans[3] - t10_40,
            100.0 * (ans[2] - t15_40) / t15_40,
            100.0 * (ans[3] - t10_40) / t10_40,
            ans[4],
            ans[5],
            ans[6],
        ]
    )

with (result_dir / "M60核算.csv").open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "扫描速率（K/min）",
            "潜热（kJ/kg）",
            "M40-t15（s）",
            "M40-t10（s）",
            "M60-t15（s）",
            "M60-t10（s）",
            "t15差值（s）",
            "t10差值（s）",
            "t15相对偏差（%）",
            "t10相对偏差（%）",
            "最大条件数",
            "最大热流残差（W/m2）",
            "最终固化进度",
        ]
    )
    writer.writerows(rows)

for row in rows:
    print(
        f"scan={row[0]:g} K/min, M=60, t15={row[4]:.3f} s, "
        f"t10={row[5]:.3f} s, relative=({row[8]:.3f}%, {row[9]:.3f}%)"
    )
