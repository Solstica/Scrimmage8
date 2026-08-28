import json
import sys
from pathlib import Path

import numpy as np

import q2


root = Path(__file__).resolve().parents[3]
out = Path(sys.argv[1])
source = Path(sys.argv[2])
T, p, xi, area = q2.read_dsc(source)

# 与已核对的 ISO 工况保持相同设置。
q2.h_e = 18.46
ans, history, _ = q2.solve_case(5.0, 0.25, 40, 160, T, p, xi, area)
data = np.asarray(history)
assert np.isfinite(data).all()
assert np.all(np.diff(data[:, 2]) > 0)
assert np.all(np.diff(data[:, 8]) >= 0)
assert np.all((data[:, 8] >= 0) & (data[:, 8] <= 1))

out.mkdir(parents=True, exist_ok=True)
with (out / "主模型历程.json").open("w", encoding="utf-8") as f:
    json.dump(
        {
            "时间与贴身侧温度": [[r[2], r[3]] for r in history],
            "阈值时刻与温度": [[ans[2], 15.0], [ans[3], 10.0]],
        },
        f,
        ensure_ascii=False,
        indent=2,
    )
print(f"ISO: t15={ans[2]:.12f} s, t10={ans[3]:.12f} s")
print(f"历程 {len(history)} 点，终点 {history[-1][2]:g} s，热流残差 {ans[5]:.3g}")
