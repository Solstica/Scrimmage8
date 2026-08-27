import importlib.util
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.text import Text
import numpy as np
import pandas as pd
from PIL import Image

import 图组绘制 as plot


def main():
    root = Path(sys.argv[1])
    res = pd.read_csv(plot.module / "results/q4_result.csv")
    raw = pd.read_csv(plot.module / "results/q4_validation.csv")
    latent, cap, material, edge = [pd.read_csv(plot.tables / f"{n}.csv") for n in plot.names]
    report = ["# 图组检查", "", "前四图：Q4-1.1 三速率15℃对照；可选双阈值需求图：Q4-1.2 新16场景。", ""]
    for _, r in res.iterrows():
        v, a, L = r["扫描速率（K/min）"], r["最小放热倍率"], r["潜热（kJ/kg）"]
        x = latent[latent.iloc[:, 0] == v].iloc[0]
        np.testing.assert_allclose(x.iloc[1:].to_numpy(), [L, a * L, (a - 1) * L, 100 * (a - 1)], rtol=1e-12)
        x = cap[cap.iloc[:, 0] == v].iloc[0]
        r0 = raw[(raw.iloc[:, 0] == v) & (raw["放热倍率"] == 1)].iloc[0]
        t0 = min(r0["热安全时间（s）"], r["Q4负重上限（s）"])
        t4, tw, target = r["Q4实际时间（s）"], r["Q4负重上限（s）"], r["Q3基准时间（s）"]
        np.testing.assert_allclose(x.iloc[1:].to_numpy(), [t0, target, t4, tw, t4 - t0, tw - t4], rtol=1e-12)
        assert t4 == min(r["Q4热安全时间（s）"], tw)
        g = edge[edge.iloc[:, 0] == v].sort_values("放热倍率")
        source = raw[raw.iloc[:, 0] == v].sort_values("放热倍率")
        np.testing.assert_allclose(g["放热倍率"], source["放热倍率"], rtol=0, atol=0)
        np.testing.assert_allclose(g["热安全裕量（s）"], source["热安全时间（s）"] - target, atol=1e-10)
        np.testing.assert_allclose(g["实际裕量（s）"], np.minimum(source["热安全时间（s）"], tw) - target, atol=1e-10)
        assert np.all(np.diff(g["实际裕量（s）"]) >= 0)
        lo, hi = g[g["边界角色"] == "下界"].iloc[0], g[g["边界角色"] == "上界"].iloc[0]
        assert lo["实际裕量（s）"] < 0 <= hi["实际裕量（s）"]
        assert hi["放热倍率"] - lo["放热倍率"] <= 1e-4
        np.testing.assert_allclose([lo["边界裕量（ms）"], hi["边界裕量（ms）"]],
                                   1000 * np.array([lo["实际裕量（s）"], hi["实际裕量（s）"]]))
        report.append(f"- v={v:g}：数据映射通过；强化潜热 {a * L:.6f} kJ/kg；"
                      f"端点裕量 {lo['边界裕量（ms）']:.6f}/{hi['边界裕量（ms）']:.6f} ms。")
    assert len(edge) == len(raw) == 15
    report.append("- 三组各5个真实采样，未增补点；仅在采样点上单调，不宣称连续全域证明。")

    spec = importlib.util.spec_from_file_location("q1_model", root / "modules/20_q1/code/q1.py")
    q1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q1)
    T, p, _, area = q1.read_dsc(root / "data/raw/附件1 放热能力数据.xlsx")
    alpha = np.sort(material["放热倍率"].unique())
    err_max = 0
    for _, r in res.iterrows():
        v, L = r["扫描速率（K/min）"], r["潜热（kJ/kg）"]
        col = f"v={v:g}有效比热（kJ/(kg·K)）"
        Z = material.pivot(index="放热倍率", columns="温度（℃）", values=col)
        np.testing.assert_allclose(Z.columns.to_numpy(), T)
        exact = q1.c[1] / 1000 + alpha[:, None] * L * (p / area)
        np.testing.assert_allclose(Z.to_numpy(), exact, rtol=1e-12, atol=1e-10)
        heat = np.trapezoid(Z.to_numpy() - q1.c[1] / 1000, T, axis=1)
        err_max = max(err_max, float(np.max(np.abs(heat / (alpha * L) - 1))))
        assert np.all(T[Z.to_numpy().argmax(axis=1)] == T[p.argmax()])
        refs = material[["参考速率（K/min）", "参考倍率"]].dropna()
        assert refs[refs.iloc[:, 0] == v].iloc[0, 1] == r["最小放热倍率"]
        assert np.isfinite(Z.to_numpy()).all()
    assert err_max < 1e-12
    report += [f"- 材料图共 {len(alpha)} 个倍率切片×{len(T)} 个温度点×3场景。",
               f"- 相变项积分与 αL 最大相对误差 {err_max:.3e}；所有切片峰温 {T[p.argmax()]:.3f} ℃。",
               "- 以上验证数据变换与公式一致性，不独立验证材料模型的物理真实性。", "", "## 文件与重绘检查", ""]

    plots = list(zip(plot.names, plot.drawers))
    if "--双阈值" in sys.argv:
        import 双阈值绘图 as dual
        full = pd.read_csv(plot.module / "results/双阈值结果.csv")
        data = pd.read_csv(plot.tables / "双阈值需求.csv")
        expected = full[["扫描速率（K/min）", "Q4阈值（℃）", "最小提高比例（%）", "Q3最优新增层数"]]
        np.testing.assert_allclose(data.to_numpy(), expected.to_numpy(), rtol=0, atol=0)
        assert data.shape == (16, 4)
        assert (data["提高比例（%）"] == 0).sum() == 5
        plots.append(("双阈值需求", dual.draw))
        report.append("- 双阈值需求：16个离散场景与新结果逐格一致，保留5个零提升，不作连续速率插值。")
    for name, draw in plots:
        fig = draw(pd.read_csv(plot.tables / f"{name}.csv"))
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=plot.dpi)
        before = np.asarray(Image.open(plot.figures / f"{name}.png"))
        after = np.asarray(Image.open(buf))
        np.testing.assert_array_equal(before, after)
        nonwhite = float(np.mean(np.any(before[:, :, :3] < 245, axis=2)))
        assert nonwhite > 0.01
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        outside = []
        for text in fig.findobj(Text):
            if text.get_visible() and text.get_text():
                b = text.get_window_extent(renderer)
                if b.width and b.height and (b.x0 < -0.5 or b.y0 < -0.5 or b.x1 > fig.bbox.width + 0.5 or b.y1 > fig.bbox.height + 0.5):
                    outside.append(text.get_text())
        assert not outside, (name, outside)
        svg = ET.parse(plot.figures / f"{name}.svg").getroot()
        svg_ns = "{http://www.w3.org/2000/svg}"
        assert list(svg.iter(svg_ns + "text"))
        assert not list(svg.iter(svg_ns + "image"))
        assert abs(float(svg.attrib["width"].removesuffix("pt")) / 72 * 25.4 - 180) < 0.01
        report.append(f"- {name}：{before.shape[1]}×{before.shape[0]} px；仅凭逐图CSV重绘像素一致；"
                      "未检出文字越出画布；SVG宽180 mm、保留文字、无嵌入位图。")
        plt.close(fig)
    report += ["", "结论：PASS（数据与导出检查）。遮挡和信息层级仍需实际目视复核。"]
    (plot.module / "results/绘图检查.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
