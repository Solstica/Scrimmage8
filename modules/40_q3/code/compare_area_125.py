import csv
from pathlib import Path


# 对照口径：实际衣料面积取人体表面积的 1.25 倍
A_b = 1.6521
A_125 = 1.25 * A_b
m_h = 60.0
d1 = 0.0007
d2 = 0.0004
rho1 = 208.0
rho2 = 552.3
rho3 = 300.0
p1 = 1000.0
p2 = 10.0
p3 = 300.0


def get_row(row, A, name):
    n = int(row["新增层数"])
    d3 = float(row["外层厚度（mm）"]) / 1000.0
    mass = A * (rho1 * d1 + rho2 * d2 + rho3 * d3)
    cost = A * (rho1 * d1 * p1 + p2 + rho3 * d3 * p3)
    tT = float(row["热安全时间（s）"])
    tW = (100.0 - m_h - mass) / 0.05
    t_eff = min(tT, tW)
    limit = "热安全" if tT <= tW else "负重"
    return [
        name,
        round(A / A_b, 2),
        A,
        float(row["扫描速率（K/min）"]),
        float(row["潜热（kJ/kg）"]),
        n,
        d3 * 1000.0,
        float(row["总厚度（mm）"]),
        mass,
        cost,
        tT,
        tW,
        t_eff,
        limit,
    ]


def save(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    root = Path(__file__).resolve().parents[3]
    result_dir = root / "modules" / "40_q3" / "results"
    source = result_dir / "正式运行_20260827" / "问题三候选方案.csv"
    out = result_dir / "EXPERIMENT" / "面积1.25倍对照"
    out.mkdir(parents=True, exist_ok=True)

    with source.open(encoding="utf-8-sig") as f:
        base = list(csv.DictReader(f))

    rows_1 = [get_row(row, A_125, "1.25倍人体表面积") for row in base]
    rows_all = [get_row(row, A_b, "人体表面积") for row in base] + rows_1
    header = [
        "面积口径",
        "面积系数",
        "衣料面积（m²）",
        "扫描速率（K/min）",
        "潜热（kJ/kg）",
        "新增层数",
        "外层厚度（mm）",
        "总厚度（mm）",
        "服装质量（kg）",
        "材料费用（元）",
        "热安全时间（s）",
        "负重时间（s）",
        "有效时间（s）",
        "限制因素",
    ]
    save(out / "问题三1.25倍面积方案.csv", header, rows_1)

    best = []
    for name in ["人体表面积", "1.25倍人体表面积"]:
        for v in [2.0, 5.0, 10.0]:
            group = [row for row in rows_all if row[0] == name and row[3] == v]
            best.append(max(group, key=lambda row: row[12]))
    save(out / "问题三面积口径最优方案对照.csv", header, best)

    C0 = A_125 * (rho1 * d1 * p1 + p2 + rho3 * 0.0003 * p3)
    dC = A_125 * rho3 * 0.0003 * p3
    if C0 + 3 * dC > 1.5 * C0 or C0 + 4 * dC <= 1.5 * C0:
        raise RuntimeError("1.25倍面积下的预算候选数不再是 n=0,1,2,3")

    for row in best:
        print(
            f"{row[0]}, v={row[3]:g} K/min: n={row[5]}, "
            f"d3={row[6]:.1f} mm, t_eff={row[12]:.3f} s, {row[13]}限制"
        )


if __name__ == "__main__":
    main()
