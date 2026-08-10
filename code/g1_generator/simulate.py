"""G1 编排：生成数据集、写出 CSV/数据字典/4 类图，并计算 SHA-256。"""
from __future__ import annotations

import os
import csv
import hashlib
import json
import tempfile
from collections import defaultdict

from . import degradation as deg
from . import plots

COLUMNS = [
    "cell_id", "cycle", "efc", "temperature", "c_rate", "dod", "protocol",
    "capacity_true", "capacity_obs", "soh", "resistance_true", "resistance_obs", "seed",
]

SCENARIO_COLORS = {
    "baseline": "#1f77b4",
    "stress_highT": "#d62728",
    "stress_highC": "#2ca02c",
    "stress_highDOD": "#ff7f0e",
}


def generate_dataset(cfg):
    deg.validate_config(cfg)
    rows = []
    for si, s in enumerate(cfg.scenarios):
        for ci in range(s.n_cells):
            rows.extend(deg.generate_cell(cfg, s, si, ci))
    return {
        "rows": rows,
        "meta": {
            "n_cells": sum(s.n_cells for s in cfg.scenarios),
            "n_rows": len(rows),
            "seed": cfg.seed,
            "scenarios": [s.id for s in cfg.scenarios],
        },
    }


def csv_text(rows):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_data_dictionary(path, cfg, meta):
    lines = []
    lines.append("# G1 数据字典（Data Dictionary）\n")
    lines.append("> 由 `g1_generator` 自动生成。所有仿真系数为 `ASSUMED`，"
                 "完整范围见 `evidence/parameter_ledger.txt`。\n")
    lines.append(f"- 化学体系: {cfg.chemistry}（NMC / LiNiMnCo-graphite）")
    lines.append(f"- 主校准对象: CALCE INR18650-20R（仅作仿真边界，非拟合来源）")
    lines.append(f"- 随机种子 seed: {cfg.seed}（冒烟固定值）")
    lines.append(f"- 电芯数: {meta['n_cells']}；总行数: {meta['n_rows']}")
    lines.append(f"- 工况: {', '.join(meta['scenarios'])}\n")

    lines.append("## 字段说明\n")
    lines.append("| 字段 | 类型 | 单位 | 含义 | 来源标签 |")
    lines.append("|---|---|---|---|---|")
    field_doc = [
        ("cell_id", "str", "-", "电芯标识 = 场景id_序号", "LITERATURE_FIXED"),
        ("cycle", "int", "cycle", "循环次数（时间轴）", "OBSERVED"),
        ("efc", "float", "EFC", "等效完整循环数 = Σ DOD/100", "OBSERVED"),
        ("temperature", "float", "degC", "环境温度", "OBSERVED"),
        ("c_rate", "float", "C", "充放电倍率", "OBSERVED"),
        ("dod", "float", "%", "放电深度", "OBSERVED"),
        ("protocol", "str", "-", "充电协议（仅 CC-CV）", "OBSERVED"),
        ("capacity_true", "float", "Ah", "真实可用容量 = Q0·(1-α·u·L(e))", "ASSUMED"),
        ("capacity_obs", "float", "Ah", "观测容量 = true + N(0,σ_Q·Q_nom)", "ASSUMED"),
        ("soh", "float", "-", "健康状态 = capacity_true / Q0_i = 1 - alpha_i·u·L(e)（起点=1）", "ASSUMED/DERIVED"),
        ("resistance_true", "float", "Ohm", "真实内阻 = R0·(1+β·u·L(e))", "ASSUMED"),
        ("resistance_obs", "float", "Ohm", "观测内阻 = true + N(0,σ_R·R_true)", "ASSUMED"),
        ("seed", "int", "-", "本运行主随机种子", "ASSUMED"),
    ]
    for name, typ, unit, desc, tag in field_doc:
        lines.append(f"| {name} | {typ} | {unit} | {desc} | {tag} |")

    lines.append("\n## 公式与边界\n")
    lines.append("- EFC = Σ(DODᵢ/100)；本数据为恒定 DOD，故 efc = cycle·DOD/100。")
    lines.append("- L(e)=√min(e,nₖ) + knee_gain·max(0,√e−√nₖ)，knee_gain=2.0，nₖ=%.0f EFC。" % cfg.n_k_EFC)
    lines.append("- u_T=exp(k_T·(T−25))，u_C=1+k_C·(C_rate−0.5)，u_D=1+k_D·(DOD/100−0.5)。")
    lines.append("- 随机效应：截断正态 N(0,σ_cell) 截断于 [−2σ,2σ]，作用于初始容量/内阻与退化速率。")
    lines.append("- 观测噪声仅加在 obs 字段，不改变总体退化方向。")
    lines.append("- 同配置 + 同 seed → CSV 逐字节一致；不同 seed → 合理电芯差异。")
    lines.append("- 模拟数据非实测数据，不声称复现真实电芯或电池内部机理。")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _color_for(cell_id):
    sid = cell_id.rsplit("_", 1)[0]
    return SCENARIO_COLORS.get(sid, "#9467bd")


def generate_plots(cfg, rows, out_dir):
    bycell = defaultdict(list)
    for r in rows:
        bycell[r["cell_id"]].append(r)

    figs = {}

    # 1. 容量轨迹
    s1 = []
    for cid, rr in bycell.items():
        rr = sorted(rr, key=lambda x: x["cycle"])
        s1.append({"label": cid, "color": _color_for(cid),
                   "x": [r["cycle"] for r in rr], "y": [r["capacity_true"] for r in rr]})
    figs["capacity"] = plots.line_chart(
        "容量轨迹（capacity_true，12 电芯）", "cycle", "Capacity (Ah)", s1,
        os.path.join(out_dir, "fig_capacity_trajectories.svg"))

    # 2. 内阻轨迹
    s2 = []
    for cid, rr in bycell.items():
        rr = sorted(rr, key=lambda x: x["cycle"])
        s2.append({"label": cid, "color": _color_for(cid),
                   "x": [r["cycle"] for r in rr], "y": [r["resistance_true"] for r in rr]})
    figs["resistance"] = plots.line_chart(
        "内阻轨迹（resistance_true，12 电芯）", "cycle", "Resistance (Ohm)", s2,
        os.path.join(out_dir, "fig_resistance_trajectories.svg"))

    # 3. 膝点前后斜率
    base = sorted(bycell.get("baseline_0", []), key=lambda x: x["cycle"])
    s3 = [{"label": "baseline_0 SOH", "color": "#1f77b4",
           "x": [r["efc"] for r in base], "y": [r["soh"] for r in base]}]
    vlines = [{"x": cfg.n_k_EFC, "label": f"knee n_k={cfg.n_k_EFC:.0f}"}]
    figs["knee"] = plots.line_chart(
        "膝点前后 SOH 斜率（baseline_0）", "EFC", "SOH (=Q/Q_nom)", s3,
        os.path.join(out_dir, "fig_knee_slope.svg"), vlines=vlines)

    # 4. 工况分组对比（各场景 SOH 均值）
    byscen = defaultdict(list)
    for r in rows:
        byscen[r["cell_id"].rsplit("_", 1)[0]].append(r)
    s4 = []
    for sid in SCENARIO_COLORS:
        if sid not in byscen:
            continue
        bycycle = defaultdict(list)
        for r in byscen[sid]:
            bycycle[r["cycle"]].append(r["soh"])
        cycles = sorted(bycycle)
        means = [sum(bycycle[c]) / len(bycycle[c]) for c in cycles]
        s4.append({"label": f"{sid} 均值", "color": SCENARIO_COLORS[sid],
                   "x": cycles, "y": means})
    figs["scenario"] = plots.line_chart(
        "工况分组对比（各场景 SOH 均值 vs cycle）", "cycle", "SOH mean", s4,
        os.path.join(out_dir, "fig_scenario_comparison.svg"))

    return figs


def run(cfg, out_dir):
    ds = generate_dataset(cfg)
    rows = ds["rows"]
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, "degradation_data.csv")
    write_csv(rows, csv_path)
    dict_path = os.path.join(out_dir, "data_dictionary.md")
    write_data_dictionary(dict_path, cfg, ds["meta"])
    figs = generate_plots(cfg, rows, out_dir)

    return {
        "csv": csv_path,
        "csv_sha256": sha256_file(csv_path),
        "dictionary": dict_path,
        "dictionary_sha256": sha256_file(dict_path),
        "figures": figs,
        "figure_sha256": {k: sha256_file(v) for k, v in figs.items()},
        "rows": rows,
        "meta": ds["meta"],
    }
