import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

import q2


font_manager.fontManager.addfont("C:/Windows/Fonts/NotoSansSC-VF.ttf")
plt.rcParams["font.family"] = "Noto Sans SC"
plt.rcParams["axes.unicode_minus"] = False

root = Path(__file__).resolve().parents[3]
fig_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "modules" / "30_q2" / "figures"
source = Path(sys.argv[2])
table_dir = fig_dir / "editable"
fig_dir.mkdir(parents=True, exist_ok=True)
table_dir.mkdir(parents=True, exist_ok=True)

T, p, xi, area = q2.read_dsc(source)
q2.h_e = 18.46
ans, history, profiles = q2.solve_case(
    5.0, 0.25, 40, 160, T, p, xi, area, save_detail=True
)

target_times = [0.0, 40.0, 80.0, 110.0]
selected = {}
for t in target_times:
    rows = [r for r in profiles if abs(r[0] - t) < 1e-9]
    if len(rows) != 93:
        raise RuntimeError(f"缺少完整温度剖面: t={t:g} s, rows={len(rows)}")
    rows = sorted(rows, key=lambda r: r[2])
    uniq = []
    for row in rows:
        if not uniq or abs(row[2] - uniq[-1][2]) > 1e-12:
            uniq.append(row)
    if len(uniq) != 91:
        raise RuntimeError(f"界面去重后点数异常: t={t:g} s, rows={len(uniq)}")
    selected[t] = uniq

csv_path = table_dir / "温度剖面补充.csv"
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["距人体侧位置（mm）"] + [f"{t:g} s" for t in target_times])
    for i in range(91):
        x = selected[target_times[0]][i][2] * 1000.0
        values = [selected[t][i][3] for t in target_times]
        writer.writerow([x] + values)

fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.4), sharex=True, sharey=True)
colors = ["#F87586", "#F39A6B", "#5BC0BE", "#3A9FD9"]
xmax = max(selected[target_times[0]][-1][2] * 1000.0, 1.4)
for ax, t, color in zip(axes.flat, target_times, colors):
    rows = selected[t]
    x = [r[2] * 1000.0 for r in rows]
    y = [r[3] for r in rows]
    ax.axvspan(0.0, 0.7, color="#F2E5CC", alpha=0.8, zorder=0)
    ax.axvspan(0.7, 1.1, color="#D8EBDD", alpha=0.8, zorder=0)
    ax.axvspan(1.1, 1.4, color="#E5F3F5", alpha=0.8, zorder=0)
    ax.plot(x, y, color=color, lw=2.0, label=f"{t:g} s", zorder=2)
    ax.axvline(0.7, color="#6B7280", lw=0.8, zorder=1)
    ax.axvline(1.1, color="#6B7280", lw=0.8, zorder=1)
    ax.axhline(15.0, color="#F59E0B", lw=0.8, ls=":")
    ax.axhline(10.0, color="#2563EB", lw=0.8, ls=":")
    ax.legend(loc="upper right", frameon=False, fontsize=9, handlelength=2.5)
    ax.set_xlim(-0.2, xmax * 1.05)
    ax.set_ylim(0, 40)
    ax.set_xticks(np.arange(0, 1.61, 0.2))
    ax.set_yticks(np.arange(10, 41, 5))
    ax.tick_params(direction="in", length=4, width=0.8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

for ax in axes[1, :]:
    ax.set_xlabel("距人体侧位置（mm）")
for ax in axes[:, 0]:
    ax.set_ylabel("温度（℃）")
fig.suptitle("ISO 11079 主模型下三层防护服温度剖面（β_DSC=5 K/min）", y=0.99, fontsize=12)
fig.tight_layout()
fig.savefig(fig_dir / "温度剖面补充.png", dpi=220, bbox_inches="tight")
plt.close(fig)

print(f"ISO: t15={ans[2]:.12f} s, t10={ans[3]:.12f} s")
print(f"输出 {csv_path}，91 行、5 列宽表")
