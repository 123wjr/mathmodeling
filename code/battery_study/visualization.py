"""零额外依赖、确定性 SVG 图表。"""
from __future__ import annotations

import os
from html import escape


COLORS = ("#176B87", "#D1495B", "#2A9D8F", "#E9A23B", "#5B5F97", "#6C757D", "#8F5D5D")


def horizontal_bar_chart(title: str, ylabel: str, labels, values, out_path: str, value_format=".3f") -> str:
    if not labels or len(labels) != len(values):
        raise ValueError("条形图标签和值必须非空且等长")
    width = 940
    height = max(420, 115 + 46 * len(labels))
    margin_left, margin_right, margin_top, margin_bottom = 245, 80, 58, 58
    chart_left, chart_right = margin_left, width - margin_right
    chart_top, chart_bottom = margin_top, height - margin_bottom
    maximum = max(float(value) for value in values)
    minimum = min(0.0, min(float(value) for value in values))
    if maximum <= minimum:
        maximum = minimum + 1.0

    def x_position(value):
        return chart_left + (value - minimum) / (maximum - minimum) * (chart_right - chart_left)

    zero_x = x_position(0.0)
    row_height = (chart_bottom - chart_top) / len(labels)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="Arial,Microsoft YaHei,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-size="18" font-weight="700" fill="#202124">{escape(title)}</text>',
    ]
    for tick in range(6):
        value = minimum + tick * (maximum - minimum) / 5.0
        x = x_position(value)
        parts.append(f'<line x1="{x:.1f}" y1="{chart_top}" x2="{x:.1f}" y2="{chart_bottom}" stroke="#e1e5e8"/>')
        parts.append(f'<text x="{x:.1f}" y="{chart_bottom+22}" text-anchor="middle" font-size="11" fill="#5f6368">{value:.3f}</text>')
    parts.append(f'<line x1="{zero_x:.1f}" y1="{chart_top}" x2="{zero_x:.1f}" y2="{chart_bottom}" stroke="#59636b"/>')
    for index, (label, raw_value) in enumerate(zip(labels, values)):
        value = float(raw_value)
        center = chart_top + (index + 0.5) * row_height
        bar_height = min(25.0, row_height * 0.58)
        value_x = x_position(value)
        x = min(zero_x, value_x)
        bar_width = max(1.0, abs(value_x - zero_x))
        color = COLORS[index % len(COLORS)]
        parts.append(f'<text x="{chart_left-12}" y="{center+4:.1f}" text-anchor="end" font-size="12" fill="#30363b">{escape(str(label))}</text>')
        parts.append(f'<rect x="{x:.1f}" y="{center-bar_height/2:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="2" fill="{color}"/>')
        anchor = "start" if value >= 0 else "end"
        offset = 7 if value >= 0 else -7
        parts.append(f'<text x="{value_x+offset:.1f}" y="{center+4:.1f}" text-anchor="{anchor}" font-size="11" fill="#202124">{format(value, value_format)}</text>')
    parts.append(f'<text x="{(chart_left+chart_right)/2:.1f}" y="{height-12}" text-anchor="middle" font-size="12" fill="#30363b">{escape(ylabel)}</text>')
    parts.append('</svg>')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(parts) + "\n")
    return out_path


def scatter_chart(title: str, xlabel: str, ylabel: str, points: list[dict], out_path: str) -> str:
    if not points:
        raise ValueError("散点图不得为空")
    width, height = 860, 540
    left, right, top, bottom = 78, 155, 58, 62
    x0, x1, y0, y1 = left, width - right, height - bottom, top
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xpad = (xmax - xmin) * 0.08 or 0.1
    ypad = (ymax - ymin) * 0.08 or 0.1
    xmin, xmax, ymin, ymax = xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad

    def sx(value):
        return x0 + (value - xmin) / (xmax - xmin) * (x1 - x0)

    def sy(value):
        return y0 - (value - ymin) / (ymax - ymin) * (y0 - y1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Arial,Microsoft YaHei,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width/2:.1f}" y="28" text-anchor="middle" font-size="18" font-weight="700" fill="#202124">{escape(title)}</text>',
        f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#30363b"/>',
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#30363b"/>',
    ]
    for tick in range(6):
        xv = xmin + tick * (xmax - xmin) / 5
        yv = ymin + tick * (ymax - ymin) / 5
        px, py = sx(xv), sy(yv)
        parts.append(f'<line x1="{px:.1f}" y1="{y0}" x2="{px:.1f}" y2="{y0+4}" stroke="#30363b"/>')
        parts.append(f'<text x="{px:.1f}" y="{y0+19}" text-anchor="middle" font-size="10" fill="#5f6368">{xv:.3f}</text>')
        parts.append(f'<line x1="{x0-4}" y1="{py:.1f}" x2="{x0}" y2="{py:.1f}" stroke="#30363b"/>')
        parts.append(f'<text x="{x0-8}" y="{py+3:.1f}" text-anchor="end" font-size="10" fill="#5f6368">{yv:.3f}</text>')
    for index, point in enumerate(points):
        color = COLORS[index % len(COLORS)]
        px, py = sx(float(point["x"])), sy(float(point["y"]))
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        parts.append(f'<text x="{x1+14}" y="{top+15+20*index}" font-size="11" fill="{color}">{escape(str(point["label"]))}</text>')
    parts.append(f'<text x="{(x0+x1)/2:.1f}" y="{height-14}" text-anchor="middle" font-size="12" fill="#30363b">{escape(xlabel)}</text>')
    parts.append(f'<text x="19" y="{(y0+y1)/2:.1f}" text-anchor="middle" transform="rotate(-90 19 {(y0+y1)/2:.1f})" font-size="12" fill="#30363b">{escape(ylabel)}</text>')
    parts.append('</svg>')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(parts) + "\n")
    return out_path
