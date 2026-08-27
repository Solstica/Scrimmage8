"""从冻结基准结果提取温度场与固化进度绘图数据。"""

import csv
from itertools import zip_longest
from pathlib import Path

import numpy as np


root = Path(__file__).resolve().parents[1]
source = root / "results" / "formal_run_20260826_v2"
out = root / "results" / "EXPERIMENT" / "第一问图形设计_20260827"
out.mkdir(parents=True, exist_ok=True)


def read(name):
    with (source / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# 固定基准 v=5，不重新求解。
rows = [r for r in read("q1_temperature_history.csv") if float(r["扫描速率（K/min）"]) == 5]
cols = {name: np.array([float(r[name]) for r in rows]) for name in (
    "时间（s）", "贴身侧温度（℃）", "功能层平均温度（℃）", "外表面温度（℃）", "固化进度"
)}
t, Tin, _, _, xi = cols.values()
assert np.all(np.diff(t) > 0) and np.all(np.diff(xi) >= 0)

# 接口两侧温度连续，重复端点核对后合并。
profiles = read("q1_temperature_profiles.csv")
tp = np.unique([float(r["时间（s）"]) for r in profiles])
x = np.unique([float(r["距人体侧位置（m）"]) for r in profiles])
field = {}
for r in profiles:
    key = (float(r["时间（s）"]), float(r["距人体侧位置（m）"]))
    value = float(r["温度（℃）"])
    if key in field:
        assert abs(field[key] - value) < 1e-8
    field[key] = value
cols["温度场时刻（s）"] = tp
for pos in x:
    cols[f"位置{pos * 1000:.8f}mm温度（℃）"] = [field[(tt, pos)] for tt in tp]

# 10%/50%/90%为已采用的 DSC 进度节点；完成时刻取首次 xi=1 的网格时刻。
levels = np.array([0.1, 0.5, 0.9, 1.0])
tm = np.r_[np.interp(levels[:3], xi, t), t[np.flatnonzero(xi >= 1)[0]]]
cols["节点进度"] = levels
cols["节点时间（s）"] = tm
res = next(r for r in read("q1_results.csv") if float(r["扫描速率（K/min）"]) == 5)
cols["评价阈值（℃）"] = [15, 10]
cols["达阈值时间（s）"] = [float(res["t15（s）"]), float(res["t10（s）"])]

with (out / "传热固化数据.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(cols)
    writer.writerows(zip_longest(*cols.values(), fillvalue=""))

print(f"基准历史 {len(t)} 点；温度场 {len(tp)}×{len(x)}；接口连续性通过。")
for value, tt in zip(levels, tm):
    print(f"固化进度 {value:.0%}：{tt:.3f} s；贴身侧 {np.interp(tt, t, Tin):.3f} ℃")
print(f"固化完成后 {float(res['t15（s）']) - tm[-1]:.3f} s 达到 15 ℃。")
