#!/usr/bin/env python3
import csv
import importlib.util
from pathlib import Path

import numpy as np


# 原始三层厚度下的服装质量与承重上限
m_c = 1.6521 * (208.0 * 0.0007 + 552.3 * 0.0004 + 300.0 * 0.0003)
tW4 = 20.0 * (40.0 - m_c)

# 当前 Q3 阶段口径与数值参数
limit = 15.0
dt = 0.25
M = 40
nq = 160
alpha_tol = 1e-4

root = Path(__file__).resolve().parents[3]
q3_file = root / "modules" / "40_q3" / "results" / "正式运行_20260827" / "问题三最优方案.csv"
out_file = root / "modules" / "50_q4" / "results" / "q4_result.csv"


def load_q1():
    path = root / "modules" / "20_q1" / "code" / "q1.py"
    spec = importlib.util.spec_from_file_location("q1_model", path)
    q1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q1)
    return q1


def read_q3(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "v": float(row["扫描速率（K/min）"]),
            "L_q3": float(row["潜热（kJ/kg）"]),
            "n": int(float(row["新增层数"])),
            "target": float(row["有效时间（s）"]),
        }
        for row in rows
    ]


def prepare(q1, step, modes, quad):
    T, p, xi, area = q1.read_dsc(root / "data" / "raw" / "附件1 放热能力数据.xlsx")
    return {
        "q1": q1,
        "dt": step,
        "M": modes,
        "nq": quad,
        "T": T,
        "p": p,
        "xi_dsc": xi,
        "area": area,
        "b1": q1.basis1(modes, quad),
        "b2": q1.basis2(modes, quad),
    }


def get_tT(alpha, v, horizon, threshold, model):
    q1 = model["q1"]
    modes = model["M"]
    quad = model["nq"]
    b1 = model["b1"]
    b2 = model["b2"]
    h0 = q1.get_h(q1.T_b)
    b3 = q1.basis3(h0, modes, quad)
    state = {
        "t": 0.0,
        "T12": q1.T_b,
        "T23": q1.T_b,
        "b1": np.zeros(modes),
        "b2": np.zeros(modes),
        "b3": q1.project(np.full(quad, q1.T_b) - q1.w3(b3["y"], q1.T_b, h0), b3),
        "basis3": b3,
        "h3": h0,
        "xi": 0.0,
    }
    L_pcm = alpha * model["area"] * 60.0 / v
    max_cond = 0.0
    max_res = 0.0

    while state["t"] < horizon - 1e-12:
        old_t = state["t"]
        old_T = q1.inner_surface(state, b1)
        step = min(model["dt"], horizon - old_t)
        state, cond, res = q1.modal_step(
            state,
            step,
            b1,
            b2,
            modes,
            quad,
            model["T"],
            model["p"],
            model["xi_dsc"],
            model["area"],
            L_pcm,
        )
        new_T = q1.inner_surface(state, b1)
        max_cond = max(max_cond, cond)
        max_res = max(max_res, res)
        t_cross = q1.first_cross(old_t, state["t"], old_T, new_T, threshold)
        if t_cross is not None:
            return t_cross, max_cond, max_res

    # None 只表示给定 horizon 内未越过阈值
    return None, max_cond, max_res


def reach(tT, target):
    return tT is None or tT >= target


def search_alpha(forward, target):
    t1 = forward(1.0, target)[0]
    if reach(t1, target):
        return 1.0, 1.0

    low = 1.0
    high = 2.0
    while not reach(forward(high, target)[0], target):
        low = high
        high *= 2.0

    while high - low > alpha_tol:
        mid = 0.5 * (low + high)
        if reach(forward(mid, target)[0], target):
            high = mid
        else:
            low = mid
    return low, high


def exact_tT(alpha, target, forward, step):
    horizon = max(target + step, 1.1 * target)
    while True:
        ans = forward(alpha, horizon)
        if ans[0] is not None:
            return ans
        horizon *= 2.0


def solve_case(case, model):
    v = case["v"]
    target = case["target"]
    L_pcm = model["area"] * 60.0 / v
    if abs(L_pcm / 1000.0 - case["L_q3"]) > 1e-6:
        raise RuntimeError(f"v={v:g} K/min 的 Q1/Q3 潜热不一致")

    base = {
        "扫描速率（K/min）": v,
        "潜热（kJ/kg）": L_pcm / 1000.0,
        "Q3最优新增层数": case["n"],
        "Q3基准时间（s）": target,
        "Q4阈值（℃）": limit,
        "Q4负重上限（s）": tW4,
    }
    if tW4 < target:
        return base | {
            "二分下界": "",
            "二分上界": "",
            "最小放热倍率": "",
            "最小提高比例（%）": "",
            "Q4热安全时间（s）": "",
            "Q4实际时间（s）": tW4,
            "活动约束": "负重",
            "状态": "INFEASIBLE_WEIGHT",
            "最大条件数": "",
            "最大热流残差（W/m2）": "",
        }

    forward = lambda alpha, horizon: get_tT(alpha, v, horizon, limit, model)
    low, alpha = search_alpha(forward, target)
    tT, max_cond, max_res = exact_tT(alpha, target, forward, model["dt"])
    t_eff = min(tT, tW4)
    return base | {
        "二分下界": low,
        "二分上界": alpha,
        "最小放热倍率": alpha,
        "最小提高比例（%）": 100.0 * (alpha - 1.0),
        "Q4热安全时间（s）": tT,
        "Q4实际时间（s）": t_eff,
        "活动约束": "热安全" if tT <= tW4 else "负重",
        "状态": "OK",
        "最大条件数": max_cond,
        "最大热流残差（W/m2）": max_res,
    }


def solve(q3_path=q3_file, step=dt, modes=M, quad=nq, save=True):
    cases = read_q3(q3_path)
    model = prepare(load_q1(), step, modes, quad)
    rows = [solve_case(case, model) for case in cases]

    if save:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with out_file.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    for row in rows:
        if row["状态"] == "OK":
            print(
                f"v={row['扫描速率（K/min）']:g} K/min, "
                f"alpha={row['最小放热倍率']:.8f}, "
                f"提高={row['最小提高比例（%）']:.6f}%, "
                f"t_eff={row['Q4实际时间（s）']:.6f} s"
            )
        else:
            print(f"v={row['扫描速率（K/min）']:g} K/min: INFEASIBLE_WEIGHT")
    return rows


if __name__ == "__main__":
    solve()
