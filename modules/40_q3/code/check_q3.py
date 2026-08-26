import csv
import importlib.util
from pathlib import Path


root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("q3", Path(__file__).with_name("q3.py"))
q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3)


def main():
    out = root / "modules" / "40_q3" / "results"
    with (out / "问题三最优方案.csv").open(encoding="utf-8-sig") as f:
        best = list(csv.DictReader(f))

    T, p, xi, area = q3.read_dsc(root / "data" / "raw" / "附件1 放热能力数据.xlsx")
    rows = []
    for item in best:
        v = float(item["扫描速率（K/min）"])
        d3 = float(item["外层厚度（mm）"]) / 1000.0
        formal = float(item["热安全时间（s）"])
        cases = [
            ("时间步减半", 0.125, 40, 160),
            ("模态数增加", 0.25, 60, 200),
        ]
        for name, dt, M, nq in cases:
            value, _, _, _ = q3.solve_t15(v, d3, dt, M, nq, T, p, xi, area)
            rows.append([v, d3 * 1000.0, name, dt, M, formal, value, abs(value - formal) / formal * 100.0])
            print(f"v={v:g} K/min, {name}: t15={value:.6f} s")

    with (out / "问题三数值检查.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "扫描速率（K/min）",
                "外层厚度（mm）",
                "检查",
                "时间步（s）",
                "模态数",
                "正式热安全时间（s）",
                "检查热安全时间（s）",
                "相对差异（%）",
            ]
        )
        writer.writerows(rows)


if __name__ == "__main__":
    main()
