"""G1 必测规则：先写失败测试，再实现生成器后跑全套通过。

覆盖 G1_TASK_DISPATCH 第三节「必测规则」：
1. 相同配置 + 相同 seed 输出逐字节一致
2. 不同 seed 产生合理电芯差异
3. 容量总体下降，内阻总体上升；膝点后斜率高于膝点前
4. 拒绝温度超出 25--50、DOD 不在 0--100%、非正倍率和不支持协议
5. 不随机拆分同一电芯循环记录；字段完整
"""
import os
import sys
import csv
import math
import hashlib
import tempfile
from collections import defaultdict

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g1_generator import config as cfgmod
from g1_generator import degradation as deg
from g1_generator import simulate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "configs", "g1_smoke.json")
REQUIRED_COLUMNS = [
    "cell_id", "cycle", "efc", "temperature", "c_rate", "dod", "protocol",
    "capacity_true", "capacity_obs", "soh", "resistance_true", "resistance_obs", "seed",
]


def load_cfg():
    return cfgmod.load_config(CFG_PATH)


# ---- 1. 同配置同 seed 逐字节一致 ----
def test_reproducibility_same_seed():
    cfg = load_cfg()
    ds_a = simulate.generate_dataset(cfg)["rows"]
    ds_b = simulate.generate_dataset(cfg)["rows"]
    assert simulate.csv_text(ds_a) == simulate.csv_text(ds_b)

    with tempfile.TemporaryDirectory() as d:
        p1 = os.path.join(d, "a.csv")
        p2 = os.path.join(d, "b.csv")
        simulate.write_csv(ds_a, p1)
        simulate.write_csv(ds_b, p2)
        h1 = simulate.sha256_file(p1)
        h2 = simulate.sha256_file(p2)
        assert h1 == h2


# ---- 2. 不同 seed 合理差异 ----
def test_different_seed_reasonable_difference():
    cfg42 = load_cfg()
    cfg99 = load_cfg()
    cfg99.seed = 99

    rows42 = simulate.generate_dataset(cfg42)["rows"]
    rows99 = simulate.generate_dataset(cfg99)["rows"]
    assert len(rows42) == len(rows99)

    # 首行（cell0 第 1 循环）容量应不同
    assert rows42[0]["capacity_true"] != rows99[0]["capacity_true"]

    # 但趋势都应下降（合理差异，不是乱序）
    def decreasing(rows):
        by = defaultdict(list)
        for r in rows:
            by[r["cell_id"]].append(r["capacity_true"])
        return all(all(v[i] > v[i + 1] for i in range(len(v) - 1)) for v in by.values())

    assert decreasing(rows42) and decreasing(rows99)


# ---- 3. 容量降 / 内阻升，膝点后斜率更高 ----
def test_capacity_decreasing():
    cfg = load_cfg()
    rows = simulate.generate_dataset(cfg)["rows"]
    by = defaultdict(list)
    for r in rows:
        by[r["cell_id"]].append(r["capacity_true"])
    for cid, v in by.items():
        assert all(v[i] > v[i + 1] for i in range(len(v) - 1)), f"{cid} 容量未单调下降"


def test_resistance_increasing():
    cfg = load_cfg()
    rows = simulate.generate_dataset(cfg)["rows"]
    by = defaultdict(list)
    for r in rows:
        by[r["cell_id"]].append(r["resistance_true"])
    for cid, v in by.items():
        assert all(v[i] < v[i + 1] for i in range(len(v) - 1)), f"{cid} 内阻未单调上升"


def test_knee_slope_after_gt_before():
    cfg = load_cfg()
    s = cfg.scenarios[0]
    params = {"Q0": cfg.Q_nom_Ah, "R0": cfg.R0_nom_Ohm, "alpha": cfg.alpha, "beta": cfg.beta}
    u = deg.u_factors(s.temperature_C, s.c_rate, s.dod_pct, cfg)
    nk = cfg.n_k_EFC
    # 膝点前（取 e 在 nk 附近两侧）
    e_b1, e_b2 = nk - 250.0, nk - 50.0
    e_a1, e_a2 = nk + 20.0, nk + 60.0
    f_b1 = deg.soh_factor(e_b1, params["alpha"], *u, cfg)
    f_b2 = deg.soh_factor(e_b2, params["alpha"], *u, cfg)
    f_a1 = deg.soh_factor(e_a1, params["alpha"], *u, cfg)
    f_a2 = deg.soh_factor(e_a2, params["alpha"], *u, cfg)
    slope_before = (f_b2 - f_b1) / (e_b2 - e_b1)
    slope_after = (f_a2 - f_a1) / (e_a2 - e_a1)
    assert slope_before < 0 and slope_after < 0
    assert abs(slope_after) > abs(slope_before)


# ---- 4. 输入边界拒绝 ----
def test_reject_bad_temperature():
    cfg = load_cfg()
    cfg.scenarios[0].temperature_C = 60.0
    with pytest.raises(ValueError):
        simulate.generate_dataset(cfg)


def test_reject_bad_dod():
    cfg = load_cfg()
    cfg.scenarios[0].dod_pct = 120.0
    with pytest.raises(ValueError):
        simulate.generate_dataset(cfg)


def test_reject_nonpositive_crate():
    cfg = load_cfg()
    cfg.scenarios[0].c_rate = -1.0
    with pytest.raises(ValueError):
        simulate.generate_dataset(cfg)


def test_reject_unsupported_protocol():
    cfg = load_cfg()
    cfg.scenarios[0].protocol = "CV-only"
    with pytest.raises(ValueError):
        simulate.generate_dataset(cfg)


# ---- 5. 字段完整 / 电芯数 / 工况覆盖 / 不拆分循环 ----
def test_data_dictionary_columns():
    cfg = load_cfg()
    rows = simulate.generate_dataset(cfg)["rows"]
    assert set(REQUIRED_COLUMNS).issubset(rows[0].keys())

    cells = {r["cell_id"] for r in rows}
    assert len(cells) >= 3

    scenarios = {cid.rsplit("_", 1)[0] for cid in cells}
    assert "baseline" in scenarios
    stress = {"stress_highT", "stress_highC", "stress_highDOD"}
    assert stress.issubset(scenarios)

    for r in rows:
        assert r["capacity_true"] > 0 and r["resistance_true"] > 0
        assert 0.0 < r["soh"] <= 1.2
        assert r["capacity_obs"] > 0 and r["resistance_obs"] > 0
        assert r["efc"] > 0


def test_no_cycle_split_per_cell():
    cfg = load_cfg()
    rows = simulate.generate_dataset(cfg)["rows"]
    by = defaultdict(list)
    for r in rows:
        by[r["cell_id"]].append(r["cycle"])
    for cid, cyc in by.items():
        assert sorted(cyc) == list(range(1, len(cyc) + 1)), f"{cid} 循环不连续"


def test_csv_roundtrip_header():
    cfg = load_cfg()
    rows = simulate.generate_dataset(cfg)["rows"]
    text = simulate.csv_text(rows)
    reader = csv.DictReader(text.splitlines())
    assert reader.fieldnames == REQUIRED_COLUMNS
