import csv
import importlib.util
from pathlib import Path


根目录 = Path(__file__).resolve().parents[3]
诊断路径 = Path(__file__).with_name("低速扫描诊断.py")
模块规格 = importlib.util.spec_from_file_location("低速扫描诊断", 诊断路径)
诊断 = importlib.util.module_from_spec(模块规格)
模块规格.loader.exec_module(诊断)


def main():
    out = 根目录 / "modules" / "40_q3" / "results" / "EXPERIMENT" / "低速扫描重审"
    with (out / "切换区间.csv").open(encoding="utf-8-sig") as f:
        intervals = list(csv.DictReader(f))

    T_dsc, p_dsc, xi_dsc, area = 诊断.问题三.read_dsc(
        根目录 / "data" / "raw" / "附件1 放热能力数据.xlsx"
    )
    n_all, d3_all, _, _, tW_all = 诊断.问题三.get_candidates()
    b1 = 诊断.问题三.basis1(诊断.模态数, 诊断.积分点数)
    b2 = 诊断.问题三.basis2(诊断.模态数, 诊断.积分点数)
    诊断.时间步长 = 0.125
    with (out / "临界步长检查.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "阈值口径",
                "区间端点",
                "扫描速率（K/min）",
                "较薄方案层数",
                "较薄方案热安全时间（s）",
                "较薄方案有效时间（s）",
                "较厚方案层数",
                "较厚方案热安全时间（s）",
                "较厚方案有效时间（s）",
                "半步长最优层数",
            ]
        )
        f.flush()
        for item in intervals:
            threshold = item["阈值口径"]
            n_left = int(item["下界最优层数"])
            n_right = int(item["上界最优层数"])
            for side, rate in [
                ("下界", float(item["区间下界（K/min）"])),
                ("上界", float(item["区间上界（K/min）"])),
            ]:
                values = []
                for n in [n_left, n_right]:
                    i = int(n)
                    t15, t10, _, _, _ = 诊断.求双阈值时间(
                        rate, d3_all[i], b1, b2, T_dsc, p_dsc, xi_dsc, area
                    )
                    thermal = t15 if threshold == "15℃" else t10
                    effective = min(thermal, tW_all[i])
                    values.append((n, thermal, effective))
                best = max(values, key=lambda x: x[2])[0]
                writer.writerow(
                    [
                        threshold,
                        side,
                        rate,
                        n_left,
                        values[0][1],
                        values[0][2],
                        n_right,
                        values[1][1],
                        values[1][2],
                        best,
                    ]
                )
                f.flush()
                print(f"{threshold} {side} v={rate:.8f}: n*={best}")


if __name__ == "__main__":
    main()
