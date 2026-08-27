import csv
import math
import sys
from pathlib import Path
from unittest.mock import patch

import q4


def main():
    q3_root = Path(sys.argv[1])
    folder = q3_root / "modules/40_q3/results/EXPERIMENT/低速扫描重审"
    cases = q4.read_q3(folder / "粗扫描最优方案.csv")
    pairs = {(c["v"], c["limit"]) for c in cases}
    assert pairs == {(v, t) for v in [0.5, 1, 1.25, 1.5, 1.75, 2, 5, 10] for t in [10, 15]}
    assert len(cases) == 16
    assert {c["n"] for c in cases} == {0, 1, 2, 3}
    for c in cases:
        assert math.isclose(c["L_q3"], 1223.12748 / c["v"], abs_tol=1e-9)
    by_key = {(c["v"], c["limit"]): c for c in cases}
    assert by_key[1.25, 15]["n"] == 1
    assert by_key[1.25, 10]["n"] == 0
    print("PASS：16个速率/阈值唯一键、潜热关联和0/1/2/3层映射")

    old = q3_root / "modules/40_q3/results/正式运行_20260827/问题三最优方案.csv"
    try:
        q4.read_q3(old)
    except ValueError:
        pass
    else:
        raise AssertionError("旧无阈值表被静默接收")
    for c in q4.read_q3(old, legacy_limit=15):
        new = by_key[c["v"], 15]
        assert c == new
    print("PASS：旧表要求显式阈值；新版三条15℃目标与旧版完全相同")

    # 解析替身只检查阈值路由和搜索分支，不充当真实热模型验证。
    seen = []
    def forward(alpha, v, horizon, threshold, model):
        seen.append(threshold)
        t = 300 * alpha + 5 * (15 - threshold)
        return (t if t <= horizon else None), 1.0, 0.0

    model = {"area": 1223127.48 / 60, "dt": q4.dt}
    with patch.object(q4, "get_tT", side_effect=forward):
        for c in cases:
            seen.clear()
            ans = q4.solve_case(c, model)
            assert seen and set(seen) == {c["limit"]}
            assert ans["Q4阈值（℃）"] == c["limit"]
            assert ans["Q3最优新增层数"] == c["n"]
            assert ans["Q4实际时间（s）"] == min(ans["Q4热安全时间（s）"], q4.tW4)
            assert ans["Q4实际时间（s）"] >= c["target"]
            assert ans["二分上界"] - ans["二分下界"] <= q4.alpha_tol
        base = cases[0] | {"target": 200.0}
        ans = q4.solve_case(base, model)
        assert ans["二分下界"] == ans["二分上界"] == ans["最小放热倍率"] == 1.0
        assert ans["最小提高比例（%）"] == 0
    with patch.object(q4, "get_tT", side_effect=AssertionError("负重不可行不应正演")):
        ans = q4.solve_case(cases[0] | {"target": q4.tW4 + 1}, model)
        assert ans["状态"] == "INFEASIBLE_WEIGHT"
    print("PASS：逐行阈值路由、二分区间、实际时间截限、零提升与负重不可行分支")
    print("说明：以上为接口/解析替身回归；不宣称真实热求解已复算。")
    if len(sys.argv) > 2:
        with Path(sys.argv[2]).open(encoding="utf-8-sig") as f:
            result = list(csv.DictReader(f))
        assert len(result) == len(cases) == 16
        assert {(float(r["扫描速率（K/min）"]), float(r["Q4阈值（℃）"])) for r in result} == pairs
        for r in result:
            c = by_key[float(r["扫描速率（K/min）"]), float(r["Q4阈值（℃）"])]
            assert int(r["Q3最优新增层数"]) == c["n"]
            assert float(r["Q3基准时间（s）"]) == c["target"]
            assert math.isclose(float(r["潜热（kJ/kg）"]), c["L_q3"], abs_tol=1e-9)
            a = float(r["最小放热倍率"])
            assert a >= 1 and r["状态"] == "OK"
            assert math.isclose(float(r["最小提高比例（%）"]), 100 * (a - 1), abs_tol=1e-10)
            assert float(r["Q4实际时间（s）"]) == min(float(r["Q4热安全时间（s）"]), q4.tW4)
            assert float(r["Q4实际时间（s）"]) >= c["target"]
            assert float(r["二分上界"]) - float(r["二分下界"]) <= q4.alpha_tol
        assert sum(float(r["最小放热倍率"]) == 1 for r in result) == 5
        with (Path(__file__).resolve().parents[1] / "results/q4_result.csv").open(encoding="utf-8-sig") as f:
            old_result = list(csv.DictReader(f))
        new15 = {float(r["扫描速率（K/min）"]): r for r in result if float(r["Q4阈值（℃）"]) == 15}
        for r in old_result:
            assert r == new15[float(r["扫描速率（K/min）"])]
        print("PASS：真实16行结果逐场景关联正确、目标均满足、5个零提升；旧三行15℃结果逐字段完全复现")


if __name__ == "__main__":
    main()
