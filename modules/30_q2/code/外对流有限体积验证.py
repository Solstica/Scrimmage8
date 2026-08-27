import csv
import sys
from pathlib import Path

import numpy as np

import check_q2
import q2


def read_modal(path):
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "name": row["外对流模型"],
            "h": float(row["h_e（W/(m2 K)）"]),
            "scan": float(row["扫描速率（K/min）"]),
            "t15": float(row["t15（s）"]),
            "t10": float(row["t10（s）"]),
        }
        for row in rows
    ]


def add_row(rows, case, setting, ans, base=None):
    t15, t10 = ans[2], ans[3]
    if not np.all(np.isfinite(ans)):
        raise RuntimeError(f"{case['name']} {case['scan']:g} K/min 出现非有限数值")
    if ans[8] > ans[9] + 1e-8:
        raise RuntimeError(f"{case['name']} {case['scan']:g} K/min 潜热越界")
    d15 = 0.0 if base is None else 100.0 * (t15 - base[2]) / base[2]
    d10 = 0.0 if base is None else 100.0 * (t10 - base[3]) / base[3]
    rows.append(
        [
            case["name"],
            case["h"],
            case["scan"],
            setting,
            ans[4],
            ans[5],
            case["t15"],
            t15,
            100.0 * (t15 - case["t15"]) / case["t15"],
            case["t10"],
            t10,
            100.0 * (t10 - case["t10"]) / case["t10"],
            d15,
            d10,
            ans[6],
            ans[7],
            ans[8],
            ans[9],
        ]
    )


def main():
    data_path = Path(sys.argv[1])
    modal_path = Path(sys.argv[2])
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)

    cases = read_modal(modal_path)
    if len(cases) != 9:
        raise RuntimeError("外对流核算表应包含 3 种关系乘 3 种扫描速率共 9 行")
    T, p, xi, area = q2.read_dsc(data_path)

    rows = []
    base = {}
    for case in cases:
        q2.h_e = case["h"]
        ans, _ = check_q2.solve_fvm(case["scan"], 0.025, 24, T, p, xi, area)
        base[case["name"], case["scan"]] = ans
        add_row(rows, case, "基准", ans)

    iso = next(case for case in cases if case["name"] == "ISO 11079简化" and case["scan"] == 5.0)
    q2.h_e = iso["h"]
    for setting, dt, n in [("时间步减半", 0.0125, 24), ("网格加密", 0.025, 36)]:
        ans, _ = check_q2.solve_fvm(5.0, dt, n, T, p, xi, area)
        add_row(rows, iso, setting, ans, base[iso["name"], 5.0])

    header = [
        "外对流模型",
        "h_e（W/(m2 K)）",
        "扫描速率（K/min）",
        "设置",
        "时间步（s）",
        "每层网格数",
        "模态t15（s）",
        "有限体积t15（s）",
        "t15较模态偏差（%）",
        "模态t10（s）",
        "有限体积t10（s）",
        "t10较模态偏差（%）",
        "t15较基准有限体积变化（%）",
        "t10较基准有限体积变化（%）",
        "最大Newton迭代",
        "最大方程残差",
        "累计潜热（J/m2）",
        "潜热上界（J/m2）",
    ]
    with (out / "外对流有限体积验证.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    base_rows = rows[:9]
    modal_err = max(max(abs(row[8]), abs(row[11])) for row in base_rows)
    refine_err = max(max(abs(row[12]), abs(row[13])) for row in rows[9:])
    print(f"9 个工况有限体积复核完成，较模态解最大偏差 {modal_err:.4f}%")
    print(f"ISO 11079、5 K/min 加密检查最大变化 {refine_err:.4f}%")


if __name__ == "__main__":
    main()
