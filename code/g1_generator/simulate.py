"""G1 编排：生成数据集、写出 CSV/数据字典/4 类图，并计算 SHA-256。"""
from __future__ import annotations

import os
import csv
import hashlib
import io
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
FALLBACK_COLORS = ("#6f4e7c", "#17becf", "#8c564b", "#7f7f7f", "#bcbd22")


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
            "n_cycles": cfg.N_cycles,
            "scenarios": [s.id for s in cfg.scenarios],
            "scenario_specs": [
                {
                    "id": s.id,
                    "temperature_C": s.temperature_C,
                    "c_rate": s.c_rate,
                    "dod_pct": s.dod_pct,
                    "n_cells": s.n_cells,
                    "protocol": s.protocol,
                }
                for s in cfg.scenarios
            ],
        },
    }


def csv_text(rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
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
    lines = [
        "# G1 数据字典（Data Dictionary）",
        "",
        "> 由 `g1_generator` 自动生成。本文件描述的是合成仿真数据，不是 CALCE 或其他实验实测数据。",
        "",
        f"- 化学体系: {cfg.chemistry}（NMC / LiNiMnCo-graphite）",
        "- 参考边界对象: CALCE INR18650-20R（未读取原始数据、未做参数拟合）",
        f"- 随机种子 seed: {cfg.seed}",
        f"- 电芯数: {meta['n_cells']}；总行数: {meta['n_rows']}",
        f"- 工况: {', '.join(meta['scenarios'])}",
        "",
        "## 来源标签",
        "",
        "- `OBSERVED`: 外部真实测量。本 G1 CSV 不包含此类字段。",
        "- `LITERATURE_FIXED`: 文献或 G0 冻结的建模约定；本配置中的 80% SOH 仅为可调退役/RUL 阈值，不是普适安全阈值。",
        "- `ASSUMED/CONFIGURED`: 仿真者设定的参数或工况；不是实测。",
        "- `DERIVED_FROM_ASSUMED`: 由仿真设定和模型公式计算出的合成量。",
        "",
        "## 字段说明",
        "",
    ]
    lines.append("| 字段 | 类型 | 单位 | 含义 | 来源标签 |")
    lines.append("|---|---|---|---|---|")
    field_doc = [
        ("cell_id", "str", "-", "仿真电芯标识 = 场景 id + 序号", "DERIVED_FROM_ASSUMED"),
        ("cycle", "int", "cycle", "配置的循环序号（时间轴）", "ASSUMED/CONFIGURED"),
        ("efc", "float", "EFC", "等效完整循环数 = Σ DOD/100", "DERIVED_FROM_ASSUMED"),
        ("temperature", "float", "degC", "仿真环境温度", "ASSUMED/CONFIGURED"),
        ("c_rate", "float", "C", "仿真充放电倍率", "ASSUMED/CONFIGURED"),
        ("dod", "float", "%", "仿真放电深度", "ASSUMED/CONFIGURED"),
        ("protocol", "str", "-", "仿真充电协议（仅 CC-CV）", "LITERATURE_FIXED/CONFIGURED"),
        ("capacity_true", "float", "Ah", "模型内部无噪声容量 = Q0_i·(1-α_i·u·L(e))", "DERIVED_FROM_ASSUMED"),
        ("capacity_obs", "float", "Ah", "合成观测容量 = capacity_true + N(0,σ_Q·Q_nom)", "DERIVED_FROM_ASSUMED"),
        ("soh", "float", "1", "capacity_true / Q0_i = 1-alpha_i·u·L(e)", "DERIVED_FROM_ASSUMED"),
        ("resistance_true", "float", "Ohm", "模型内部无噪声内阻 = R0_i·(1+β_i·u·L(e))", "DERIVED_FROM_ASSUMED"),
        ("resistance_obs", "float", "Ohm", "合成观测内阻 = resistance_true + N(0,σ_R·R_true)", "DERIVED_FROM_ASSUMED"),
        ("seed", "int", "-", "本运行主随机种子", "ASSUMED/CONFIGURED"),
    ]
    for name, typ, unit, desc, tag in field_doc:
        lines.append(f"| {name} | {typ} | {unit} | {desc} | {tag} |")

    lines.extend(["", "## 公式与边界", ""])
    lines.append("- EFC = Σ(DODᵢ/100)；本数据为恒定 DOD，故 efc = cycle·DOD/100。")
    lines.append(
        "- L(e)=√min(e,nₖ) + knee_gain·max(0,√e−√nₖ)，"
        f"knee_gain={cfg.knee_gain:.1f}，nₖ={cfg.n_k_EFC:.0f} EFC。"
    )
    lines.append("- u_T=exp(k_T·(T−25))，u_C=1+k_C·(C_rate−0.5)，u_D=1+k_D·(DOD/100−0.5)。")
    lines.append("- 随机效应：截断正态 N(0,σ_cell) 截断于 [−2σ,2σ]，作用于初始容量/内阻与退化速率。")
    lines.append("- 观测噪声仅加在 obs 字段，不改变总体退化方向。")
    lines.append("- 同配置 + 同 seed → CSV 逐字节一致；不同 seed → 合理电芯差异。")
    lines.append("- 模拟数据非实测数据，不声称复现真实电芯或电池内部机理。")

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _scenario_color(scenario_id, index):
    return SCENARIO_COLORS.get(scenario_id, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def generate_plots(cfg, rows, out_dir):
    bycell = defaultdict(list)
    for r in rows:
        bycell[r["cell_id"]].append(r)

    if not bycell:
        raise ValueError("没有可绘制的数据行")

    scenario_ids = [scenario.id for scenario in cfg.scenarios]
    color_by_scenario = {
        scenario_id: _scenario_color(scenario_id, index)
        for index, scenario_id in enumerate(scenario_ids)
    }
    figs = {}

    # 1. 容量轨迹
    s1 = []
    for cid, rr in bycell.items():
        rr = sorted(rr, key=lambda x: x["cycle"])
        scenario_id = cid.rsplit("_", 1)[0]
        s1.append({"label": cid, "color": color_by_scenario[scenario_id],
                   "x": [r["cycle"] for r in rr], "y": [r["capacity_true"] for r in rr]})
    figs["capacity"] = plots.line_chart(
        f"容量轨迹（capacity_true，{len(bycell)} 电芯）", "cycle", "Capacity (Ah)", s1,
        os.path.join(out_dir, "fig_capacity_trajectories.svg"), x_floor=0)

    # 2. 内阻轨迹
    s2 = []
    for cid, rr in bycell.items():
        rr = sorted(rr, key=lambda x: x["cycle"])
        scenario_id = cid.rsplit("_", 1)[0]
        s2.append({"label": cid, "color": color_by_scenario[scenario_id],
                   "x": [r["cycle"] for r in rr], "y": [r["resistance_true"] for r in rr]})
    figs["resistance"] = plots.line_chart(
        f"内阻轨迹（resistance_true，{len(bycell)} 电芯）", "cycle", "Resistance (Ohm)", s2,
        os.path.join(out_dir, "fig_resistance_trajectories.svg"), x_floor=0)

    byscen = defaultdict(list)
    for r in rows:
        byscen[r["cell_id"].rsplit("_", 1)[0]].append(r)

    # 3. 基准工况所有电芯的 SOH 均值，不依赖某个硬编码 cell_id。
    baseline_id = "baseline" if "baseline" in byscen else scenario_ids[0]
    baseline_by_cycle = defaultdict(list)
    for row in byscen[baseline_id]:
        baseline_by_cycle[row["cycle"]].append(row)
    baseline_cycles = sorted(baseline_by_cycle)
    baseline_efc = [baseline_by_cycle[cycle][0]["efc"] for cycle in baseline_cycles]
    baseline_soh = [
        sum(row["soh"] for row in baseline_by_cycle[cycle]) / len(baseline_by_cycle[cycle])
        for cycle in baseline_cycles
    ]
    s3 = [{"label": f"{baseline_id} SOH 均值", "color": color_by_scenario[baseline_id],
           "x": baseline_efc, "y": baseline_soh}]
    vlines = [{"x": cfg.n_k_EFC, "label": f"knee n_k={cfg.n_k_EFC:.0f}"}]
    figs["knee"] = plots.line_chart(
        f"膝点前后 SOH 斜率（{baseline_id} 均值）", "EFC", "SOH (=capacity_true / Q0_i)", s3,
        os.path.join(out_dir, "fig_knee_slope.svg"), vlines=vlines, x_floor=0)

    # 4. 工况分组对比（各场景 SOH 均值）
    s4 = []
    for sid in scenario_ids:
        if sid not in byscen:
            continue
        bycycle = defaultdict(list)
        for r in byscen[sid]:
            bycycle[r["cycle"]].append(r["soh"])
        cycles = sorted(bycycle)
        means = [sum(bycycle[c]) / len(bycycle[c]) for c in cycles]
        s4.append({"label": f"{sid} 均值", "color": color_by_scenario[sid],
                   "x": cycles, "y": means})
    figs["scenario"] = plots.line_chart(
        "工况分组对比（各场景 SOH 均值 vs cycle）", "cycle", "SOH mean", s4,
        os.path.join(out_dir, "fig_scenario_comparison.svg"), x_floor=0)

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
