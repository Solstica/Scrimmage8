import csv
import sys
from pathlib import Path

import q1


root = Path(__file__).resolve().parents[3]
out = Path(sys.argv[1])

# 同一模型仅增加模态截断数
T, p, xi, area = q1.read_dsc(root / "data" / "raw" / "附件1 放热能力数据.xlsx")
with (root / "modules" / "20_q1" / "results" / "formal_run_20260826_v2" / "q1_results.csv").open(
    encoding="utf-8-sig"
) as f:
    old = {float(row["扫描速率（K/min）"]): row for row in csv.DictReader(f)}

rows = []
for v in [2.0, 5.0, 10.0]:
    ans, _, _ = q1.solve_case(v, 0.25, 60, 200, T, p, xi, area)
    old15 = float(old[v]["t15（s）"])
    old10 = float(old[v]["t10（s）"])
    rows.append(
        [
            v,
            ans[1],
            ans[2],
            ans[3],
            ans[2] - old15,
            ans[3] - old10,
            100.0 * (ans[2] - old15) / old15,
            100.0 * (ans[3] - old10) / old10,
            ans[4],
            ans[5],
            ans[6],
        ]
    )

out.mkdir(parents=True, exist_ok=True)
with (out / "m60_results.csv").open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "扫描速率（K/min）",
            "潜热（kJ/kg）",
            "M60_t15（s）",
            "M60_t10（s）",
            "相对M40_t15变化（s）",
            "相对M40_t10变化（s）",
            "相对M40_t15变化（%）",
            "相对M40_t10变化（%）",
            "最大条件数",
            "最大热流残差（W/m2）",
            "最终固化进度",
        ]
    )
    writer.writerows(rows)

for row in rows:
    print(
        f"v={row[0]:g} K/min: t15={row[2]:.6f} s, t10={row[3]:.6f} s, "
        f"change={row[6]:+.4f}%/{row[7]:+.4f}%"
    )
