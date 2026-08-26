import csv
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import solve_banded

import q2


def make_grid(n):
    x = [0.0]
    material = []
    offset = 0.0
    for i in range(3):
        local = np.linspace(0.0, q2.d[i], n + 1)
        for value in local[1:]:
            x.append(offset + value)
            material.append(i)
        offset += q2.d[i]
    x = np.array(x)
    material = np.array(material)
    dx = np.diff(x)
    G = q2.k[material] / dx
    C = np.zeros(len(x))
    m_pcm = np.zeros(len(x))
    for edge, i in enumerate(material):
        cap = q2.rho[i] * q2.c[i] * dx[edge]
        C[edge] += 0.5 * cap
        C[edge + 1] += 0.5 * cap
        if i == 1:
            mass = q2.rho[i] * dx[edge]
            m_pcm[edge] += 0.5 * mass
            m_pcm[edge + 1] += 0.5 * mass
    return x, G, C, m_pcm


def outer_flux(Tout, full_max):
    delta = max(Tout - q2.T_inf, 0.0)
    h_nat = 2.38 * delta**0.25
    if full_max and h_nat > q2.h_e:
        return 2.38 * delta**1.25, 2.38 * 1.25 * delta**0.25
    return q2.h_e * delta, q2.h_e


def get_net(T, G, full_max):
    net = np.zeros(len(T))
    flux = G * (T[:-1] - T[1:])
    net[:-1] -= flux
    net[1:] += flux
    net[0] += q2.h_b * (q2.T_b - T[0])
    net[-1] -= outer_flux(T[-1], full_max)[0]
    return net


def implicit_step(T0, xi0, dt, G, C, m_pcm, L_pcm, T_dsc, p_dsc, xi_dsc, area, full_max):
    T = T0.copy()
    for it in range(30):
        xi_try = np.interp(T, T_dsc, xi_dsc, left=1.0, right=0.0)
        xi = np.maximum(xi0, xi_try)
        net = get_net(T, G, full_max)
        res = C * (T - T0) - m_pcm * L_pcm * (xi - xi0) - dt * net
        scale = max(float(np.max(np.abs(C * (T - T0)))), float(np.max(np.abs(dt * net))), 1.0)
        if np.max(np.abs(res)) < 1e-10 * scale:
            return T, xi, it + 1, float(np.max(np.abs(res)))

        active = (m_pcm > 0.0) & (xi_try > xi0 + 1e-12)
        w = np.interp(T, T_dsc, p_dsc / area, left=0.0, right=0.0)
        diag = C + m_pcm * L_pcm * w * active
        diag[:-1] += dt * G
        diag[1:] += dt * G
        diag[0] += dt * q2.h_b
        diag[-1] += dt * outer_flux(T[-1], full_max)[1]
        ab = np.zeros((3, len(T)))
        ab[0, 1:] = -dt * G
        ab[1] = diag
        ab[2, :-1] = -dt * G
        T += solve_banded((1, 1), ab, -res)
    raise RuntimeError("finite-volume Newton iteration did not converge")


def crossing(t0, t1, y0, y1, limit):
    if y0 > limit >= y1:
        return t0 + (y0 - limit) / (y0 - y1) * (t1 - t0)
    return None


def solve_fvm(scan, dt, n, T_dsc, p_dsc, xi_dsc, area, full_max=False, save_history=False):
    L_pcm = area * 60.0 / scan
    x, G, C, m_pcm = make_grid(n)
    T = np.full(len(x), q2.T_b)
    xi = np.zeros(len(x))
    t = 0.0
    t15 = None
    t10 = None
    max_iter = 0
    max_res = 0.0
    history = [[scan, t, T[0], T[n], T[2 * n], T[-1], 0.0]] if save_history else []

    while t < 1800.0 and t10 is None:
        T0 = T.copy()
        xi0 = xi.copy()
        T, xi, nit, res = implicit_step(
            T0, xi0, dt, G, C, m_pcm, L_pcm, T_dsc, p_dsc, xi_dsc, area, full_max
        )
        t0 = t
        t += dt
        max_iter = max(max_iter, nit)
        max_res = max(max_res, res)
        if np.any(xi + 1e-13 < xi0):
            raise RuntimeError("solidification progress decreased")
        if t15 is None:
            t15 = crossing(t0, t, T0[0], T[0], 15.0)
        t10 = crossing(t0, t, T0[0], T[0], 10.0)
        if save_history:
            xi_avg = float(np.sum(m_pcm * xi) / np.sum(m_pcm))
            history.append([scan, t, T[0], T[n], T[2 * n], T[-1], xi_avg])

    if t15 is None or t10 is None:
        raise RuntimeError(f"FVM scan={scan:g} K/min did not reach both thresholds")
    latent = float(np.sum(m_pcm * L_pcm * xi))
    bound = float(np.sum(m_pcm) * L_pcm)
    return [scan, L_pcm / 1000.0, t15, t10, dt, n, max_iter, max_res, latent, bound], history


def read_formal(path):
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {
        float(row["扫描速率（K/min）"]): (float(row["t15（s）"]), float(row["t10（s）"]))
        for row in rows
    }


def add_compare(rows, method, setting, ans, formal):
    scan, L_pcm, t15, t10 = ans[:4]
    ref15, ref10 = formal[scan]
    rows.append(
        [method, setting, scan, L_pcm, t15, t10, 100.0 * (t15 - ref15) / ref15, 100.0 * (t10 - ref10) / ref10]
    )


def save_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    root = Path(__file__).resolve().parents[3]
    formal_dir = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    formal = read_formal(formal_dir / "计算结果.csv")
    T_dsc, p_dsc, xi_dsc, area = q2.read_dsc(root / "data" / "raw" / "附件1 放热能力数据.xlsx")

    comparison = []
    fvm_detail = []
    fvm_history = []
    for scan in [2.0, 5.0, 10.0]:
        ans, hist = solve_fvm(scan, 0.025, 24, T_dsc, p_dsc, xi_dsc, area, save_history=(scan == 5.0))
        fvm_detail.append(ans)
        fvm_history.extend(hist)
        add_compare(comparison, "有限体积", "dt=0.025 s, n=24/layer", ans, formal)

    modal_dt, _, _ = q2.solve_case(5.0, 0.125, 40, 160, T_dsc, p_dsc, xi_dsc, area)
    modal_M, _, _ = q2.solve_case(5.0, 0.25, 60, 200, T_dsc, p_dsc, xi_dsc, area)
    fvm_dt, _ = solve_fvm(5.0, 0.0125, 24, T_dsc, p_dsc, xi_dsc, area)
    fvm_grid, _ = solve_fvm(5.0, 0.025, 36, T_dsc, p_dsc, xi_dsc, area)
    full_max, _ = solve_fvm(5.0, 0.025, 24, T_dsc, p_dsc, xi_dsc, area, full_max=True)
    add_compare(comparison, "模态法", "dt=0.125 s, M=40", modal_dt, formal)
    add_compare(comparison, "模态法", "dt=0.25 s, M=60", modal_M, formal)
    add_compare(comparison, "有限体积", "dt=0.0125 s, n=24/layer", fvm_dt, formal)
    add_compare(comparison, "有限体积", "dt=0.025 s, n=36/layer", fvm_grid, formal)
    add_compare(comparison, "有限体积", "完整max(h_nat,h_for)", full_max, formal)

    save_csv(
        out / "数值验证.csv",
        ["方法", "设置", "扫描速率（K/min）", "潜热（kJ/kg）", "t15（s）", "t10（s）", "t15相对正式解偏差（%）", "t10相对正式解偏差（%）"],
        comparison,
    )
    save_csv(
        out / "有限体积检查.csv",
        ["扫描速率（K/min）", "潜热（kJ/kg）", "t15（s）", "t10（s）", "时间步（s）", "每层网格数", "最大Newton迭代", "最大方程残差", "累计潜热（J/m2）", "潜热上界（J/m2）"],
        fvm_detail,
    )
    save_csv(
        out / "有限体积历程.csv",
        ["扫描速率（K/min）", "时间（s）", "贴身侧温度（℃）", "界面12温度（℃）", "界面23温度（℃）", "外表面温度（℃）", "平均固化进度"],
        fvm_history,
    )
    for row in comparison:
        print(f"{row[0]} {row[1]}: scan={row[2]:g}, t15={row[4]:.3f} s, t10={row[5]:.3f} s")


if __name__ == "__main__":
    main()
