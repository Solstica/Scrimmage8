import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import 图组绘制 as plot


def draw(data):
    values = data.pivot(index="阈值（℃）", columns="扫描速率（K/min）", values="提高比例（%）").loc[[15, 10]]
    layers = data.pivot(index="阈值（℃）", columns="扫描速率（K/min）", values="Q3新增层数").loc[[15, 10]]
    fig, ax = plt.subplots(figsize=(plot.width, 88 / 25.4))
    fig.subplots_adjust(left=0.10, right=0.87, bottom=0.32, top=0.80)
    Z = values.to_numpy()
    im = ax.pcolormesh(np.arange(Z.shape[1] + 1) - 0.5, np.arange(3) - 0.5, Z,
                       cmap="cividis", vmin=0, vmax=Z.max(), edgecolors="white", linewidth=0.9)
    ax.set_ylim(1.5, -0.5)
    for y in range(Z.shape[0]):
        for x in range(Z.shape[1]):
            text = f"{Z[y, x]:.2f}%\nn = {layers.iloc[y, x]:g}"
            ax.text(x, y, text, ha="center", va="center", fontsize=8,
                    color="white" if Z[y, x] < 0.5 * Z.max() else "#111111")
    ax.set_xticks(range(len(values.columns)), [f"{v:g}" for v in values.columns])
    ax.set_yticks([0, 1], ["15 ℃", "10 ℃"])
    ax.set_xticks(np.arange(-0.5, len(values.columns), 1), minor=True)
    ax.set_yticks([-0.5, 0.5, 1.5], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.set_xlabel("扫描速率（K/min；离散场景等距排列）")
    ax.set_ylabel("Q3 / Q4 共同阈值")
    cax = fig.add_axes([0.895, 0.32, 0.019, 0.48])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("最小提高比例（%）", fontsize=8.5)
    cb.solids.set_rasterized(False)
    fig.text(0.10, 0.89, "同一场景：原始厚度＋PCM强化，追平 Q3 最优方案", fontsize=9)
    fig.text(0.98, 0.982, "DRAFT · 双阈值诊断", fontsize=8, ha="right", va="top", color="#777777")
    fig.text(0.08, 0.035, "格内 n 为同条件 Q3 最优新增层数；Q4 自身保持原始厚度。\n低速高潜热工况仅作数学诊断；最终阈值待确认，不作连续相图解释。", fontsize=8, color="#555555")
    return fig


def main():
    path = plot.tables / "双阈值需求.csv"
    if "--重绘" not in sys.argv:
        res = pd.read_csv(plot.module / "results/双阈值结果.csv")
        assert (res["状态"] == "OK").all()
        data = res[["扫描速率（K/min）", "Q4阈值（℃）", "最小提高比例（%）", "Q3最优新增层数"]]
        data.columns = ["扫描速率（K/min）", "阈值（℃）", "提高比例（%）", "Q3新增层数"]
        data.to_csv(path, index=False, encoding="utf-8-sig")
    fig = draw(pd.read_csv(path))
    fig.savefig(plot.figures / "双阈值需求.png", dpi=plot.dpi)
    fig.savefig(plot.figures / "双阈值需求.svg")
    plt.close(fig)
    print("已生成双阈值需求图及逐图数据。")


if __name__ == "__main__":
    main()
