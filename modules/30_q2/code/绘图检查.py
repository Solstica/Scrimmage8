import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

import 第二问绘图 as draw


def check(fig, out, name):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text = list(fig.texts)
    for legend in fig.legends:
        text.extend(legend.get_texts())
    for ax in fig.axes:
        text.extend(ax.texts)
        text.extend([ax.xaxis.label, ax.yaxis.label])
        for label in ax.get_xticklabels():
            if ax.get_xlim()[0] <= label.get_position()[0] <= ax.get_xlim()[1]:
                text.append(label)
        for label in ax.get_yticklabels():
            if ax.get_ylim()[0] <= label.get_position()[1] <= ax.get_ylim()[1]:
                text.append(label)
    for label in text:
        if not label.get_visible() or not label.get_text():
            continue
        box = label.get_window_extent(renderer)
        if box.x0 < -1 or box.y0 < -1 or box.x1 > fig.bbox.width + 1 or box.y1 > fig.bbox.height + 1:
            raise AssertionError(f"{name} 文字越界：{label.get_text()}")

    svg = ET.parse(out / f"{name}.svg").getroot()
    if list(svg.iter("{http://www.w3.org/2000/svg}image")):
        raise AssertionError(f"{name} SVG 混入位图")
    width_pt = float(svg.attrib["width"].removesuffix("pt"))
    if abs(width_pt * 25.4 / 72 - 180) > 0.01:
        raise AssertionError(f"{name} SVG 宽度不是 180 mm")
    with Image.open(out / "预览" / f"{name}.png") as im:
        expected = tuple(int(v * draw.DPI) for v in fig.get_size_inches())
        if im.size != expected:
            raise AssertionError(f"{name} PNG 尺寸不符")
    print(f"{name}：{len(text)} 处文字边界、SVG 纯矢量和物理宽度、PNG 尺寸均通过")
    plt.close(fig)


if __name__ == "__main__":
    draw.save = check
    draw.main()
