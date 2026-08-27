#!/usr/bin/env python3
import csv
import importlib.util
from pathlib import Path

import numpy as np


# Q3 的 v=5 K/min 最优方案，单位 s
t3_best = 416.0379012473915

# 原始三层厚度下的服装质量与承重上限
m_c = 1.6521 * (208.0 * 0.0007 + 552.3 * 0.0004 + 300.0 * 0.0003)
tW4 = 20.0 * (40.0 - m_c)

# Q1 基线与数值参数
v = 5.0
dt = 0.25
M = 40
nq = 160
alpha_tol = 1e-4

root = Path(__file__).resolve().parents[3]
out_file = root / "modules" / "50_q4" / "results" / "q4_result.csv"


def load_q1():
    path = root / "modules" / "20_q1" / "code" / "q1.py"
    spec = importlib.util.spec_from_file_location("q1_model", path)
    q1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q1)
    return q1


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


def get_tT(alpha, horizon, model):
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
        t15 = q1.first_cross(old_t, state["t"], old_T, new_T, 15.0)
        if t15 is not None:
            return t15, max_cond, max_res

    # None 只表示给定 horizon 内未越过阈值，不解释为无穷大
    return None, max_cond, max_res


def reach(tT, target):
    return tT is None or tT >= target


def search_alpha(forward, target, tW):
    if tW < target:
        raise RuntimeError("固定厚度的承重上限小于 Q3 基准，Q4 无可行解")

    t1 = forward(1.0, target)[0]
    if reach(t1, target):
        return 1.0

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
    return high


def exact_tT(alpha, target, forward):
    horizon = max(target + dt, 1.1 * target)
    while True:
        ans = forward(alpha, horizon)
        if ans[0] is not None:
            return ans
        horizon *= 2.0


def solve(step=dt, modes=M, quad=nq, save=True):
    model = prepare(load_q1(), step, modes, quad)
    forward = lambda alpha, horizon: get_tT(alpha, horizon, model)
    alpha = search_alpha(forward, t3_best, tW4)
    tT, max_cond, max_res = exact_tT(alpha, t3_best, forward)
    t_eff = min(tT, tW4)
    row = {
        "Q3基准时间（s）": t3_best,
        "服装质量（kg）": m_c,
        "承重上限（s）": tW4,
        "最小放热倍率": alpha,
        "最小提高比例（%）": 100.0 * (alpha - 1.0),
        "热安全时间（s）": tT,
        "实际坚持时间（s）": t_eff,
        "最大条件数": max_cond,
        "最大热流残差（W/m2）": max_res,
    }

    if save:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with out_file.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)

    for name, value in row.items():
        print(f"{name}: {value}")
    return row


if __name__ == "__main__":
    solve()
