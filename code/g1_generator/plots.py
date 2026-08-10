"""G1 图表：纯标准库生成 SVG 折线图（零第三方依赖、完全可复现）。

4 类图：容量轨迹、内阻轨迹、膝点前后斜率、工况分组对比。
"""
from __future__ import annotations

import os


def _scale(v, vmin, vmax, p0, p1):
    if vmax == vmin:
        return (p0 + p1) / 2.0
    return p0 + (v - vmin) / (vmax - vmin) * (p1 - p0)


def _ticks(vmin, vmax, n=5):
    if vmax == vmin:
        return [vmin]
    step = (vmax - vmin) / float(n)
    return [vmin + i * step for i in range(n + 1)]


def line_chart(title, xlabel, ylabel, series, out_path, vlines=None, ymin=None, ymax=None, x_floor=None):
    """通用 SVG 折线图。series: [{label,color,x:[],y:[]}]。

    x_floor: 横轴下限（如 0）。当数据从非负计数（cycle/efc）起始时，
    用于避免留白把首刻度推成负数（误导）。
    """
    W, H = 860, 540
    ml, mr, mt, mb = 70, 170, 60, 60
    x0, x1 = ml, W - mr
    y0, y1 = H - mb, mt

    all_x, all_y = [], []
    for s in series:
        all_x.extend(s["x"])
        all_y.extend(s["y"])
    xmin, xmax = min(all_x), max(all_x)
    if ymin is None:
        ymin = min(all_y)
    if ymax is None:
        ymax = max(all_y)
    # 留白
    dx = (xmax - xmin) * 0.02 or 1.0
    xmin, xmax = xmin - dx, xmax + dx
    if x_floor is not None:
        xmin = max(float(x_floor), xmin)
    dy = (ymax - ymin) * 0.05 or 0.01
    ymin, ymax = ymin - dy, ymax + dy

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                 f'font-family="Helvetica,Arial,sans-serif" font-size="12">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    parts.append(f'<text x="{W/2}" y="26" text-anchor="middle" font-size="16" '
                 f'font-weight="bold" fill="#222">{title}</text>')

    # 坐标轴
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333"/>')
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333"/>')
    parts.append(f'<text x="{(x0+x1)/2}" y="{H-18}" text-anchor="middle" fill="#333">{xlabel}</text>')
    parts.append(f'<text x="18" y="{(y0+y1)/2}" text-anchor="middle" fill="#333" '
                 f'transform="rotate(-90 18 {(y0+y1)/2})">{ylabel}</text>')

    # 刻度
    for tx in _ticks(xmin, xmax, 5):
        px = _scale(tx, xmin, xmax, x0, x1)
        parts.append(f'<line x1="{px:.1f}" y1="{y0}" x2="{px:.1f}" y2="{y0+4}" stroke="#333"/>')
        parts.append(f'<text x="{px:.1f}" y="{y0+18}" text-anchor="middle" fill="#666" '
                     f'font-size="10">{tx:.0f}</text>')
    for ty in _ticks(ymin, ymax, 5):
        py = _scale(ty, ymin, ymax, y0, y1)
        parts.append(f'<line x1="{x0-4}" y1="{py:.1f}" x2="{x0}" y2="{py:.1f}" stroke="#333"/>')
        parts.append(f'<text x="{x0-8}" y="{py+3:.1f}" text-anchor="end" fill="#666" '
                     f'font-size="10">{ty:.3f}</text>')

    # 竖线（如膝点）
    if vlines:
        for v in vlines:
            px = _scale(v["x"], xmin, xmax, x0, x1)
            parts.append(f'<line x1="{px:.1f}" y1="{y1}" x2="{px:.1f}" y2="{y0}" '
                         f'stroke="{v.get("color","#c0392b")}" stroke-dasharray="5,4"/>')
            parts.append(f'<text x="{px:.1f}" y="{y1-6}" text-anchor="middle" '
                         f'fill="{v.get("color","#c0392b")}" font-size="10">{v.get("label","")}</text>')

    # 折线
    for s in series:
        pts = " ".join(f"{_scale(s['x'][i], xmin, xmax, x0, x1):.1f},"
                       f"{_scale(s['y'][i], ymin, ymax, y0, y1):.1f}" for i in range(len(s["x"])))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" '
                     f'stroke-width="1.6" opacity="{s.get("opacity", 0.9)}"/>')

    # 图例
    lx = x1 + 16
    ly = mt + 10
    for s in series:
        parts.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+24}" y2="{ly}" stroke="{s["color"]}" stroke-width="2.4"/>')
        parts.append(f'<text x="{lx+30}" y="{ly+4}" fill="#222" font-size="11">{s["label"]}</text>')
        ly += 20

    parts.append('</svg>')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    return out_path
