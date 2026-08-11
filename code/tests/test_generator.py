"""G1 必测规则：先写失败测试，再实现生成器后跑全套通过。

覆盖 G1_TASK_DISPATCH 第三节「必测规则」：
1. 相同配置 + 相同 seed 输出逐字节一致
2. 不同 seed 产生合理电芯差异
3. 容量总体下降，内阻总体上升；膝点后斜率高于膝点前
4. 拒绝超出 G0 冻结范围的温度、DOD、倍率、协议和模型参数
5. 不随机拆分同一电芯循环记录；字段完整
6. 输出标签、图标题、路径和换行可移植且不硬编码
"""
import os
import sys
import csv
import json
import random
import tempfile
from collections import defaultdict

import pytest

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(CODE_ROOT)
sys.path.insert(0, CODE_ROOT)

from g1_generator import config as cfgmod
from g1_generator import degradation as deg
from g1_generator import simulate
from g1_generator import cli

CFG_PATH = os.path.join(REPO_ROOT, "configs", "g1_smoke.json")
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


def test_all_core_outputs_are_byte_identical_across_runs():
    cfg = load_cfg()
    with tempfile.TemporaryDirectory() as directory:
        first = simulate.run(cfg, os.path.join(directory, "first"))
        second = simulate.run(cfg, os.path.join(directory, "second"))
        first_paths = [first["csv"], first["dictionary"], *first["figures"].values()]
        second_paths = [second["csv"], second["dictionary"], *second["figures"].values()]
        for first_path, second_path in zip(first_paths, second_paths):
            with open(first_path, "rb") as first_file, open(second_path, "rb") as second_file:
                assert first_file.read() == second_file.read()


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


def test_stress_scenarios_end_below_baseline_mean_soh():
    rows = simulate.generate_dataset(load_cfg())["rows"]
    final_soh = defaultdict(list)
    max_cycle = max(row["cycle"] for row in rows)
    for row in rows:
        if row["cycle"] == max_cycle:
            scenario_id = row["cell_id"].rsplit("_", 1)[0]
            final_soh[scenario_id].append(row["soh"])
    means = {
        scenario_id: sum(values) / len(values)
        for scenario_id, values in final_soh.items()
    }
    assert means["stress_highT"] < means["baseline"]
    assert means["stress_highC"] < means["baseline"]
    assert means["stress_highDOD"] < means["baseline"]


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


@pytest.mark.parametrize("value", [0.49, 2.01])
def test_reject_crate_outside_frozen_range(value):
    cfg = load_cfg()
    cfg.scenarios[0].c_rate = value
    with pytest.raises(ValueError, match="c_rate"):
        simulate.generate_dataset(cfg)


def test_reject_dod_below_frozen_range():
    cfg = load_cfg()
    cfg.scenarios[0].dod_pct = 49.9
    with pytest.raises(ValueError, match="dod_pct"):
        simulate.generate_dataset(cfg)


def test_reject_unsupported_protocol():
    cfg = load_cfg()
    cfg.scenarios[0].protocol = "CV-only"
    with pytest.raises(ValueError):
        simulate.generate_dataset(cfg)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("chemistry", "LFP"),
        ("Q_nom_Ah", 2.1),
        ("R0_nom_Ohm", 0.101),
        ("N_cycles", 1001),
        ("n_k_EFC", 851.0),
        ("knee_gain", 2.1),
        ("SOH_EOL_pct", 79.0),
        ("alpha", 0.0029),
        ("beta", 0.0201),
        ("k_T", 0.009),
        ("k_C", 0.201),
        ("k_D", 0.19),
        ("sigma_Q_pct", 1.01),
        ("sigma_R_pct", 3.01),
        ("sigma_cell", 0.101),
        ("protocol", "CC"),
    ],
)
def test_reject_global_values_outside_frozen_ledger(field, value):
    cfg = load_cfg()
    setattr(cfg, field, value)
    with pytest.raises(ValueError):
        simulate.generate_dataset(cfg)


def test_reject_duplicate_scenario_id():
    cfg = load_cfg()
    cfg.scenarios[1].id = cfg.scenarios[0].id
    with pytest.raises(ValueError, match="重复"):
        simulate.generate_dataset(cfg)


def test_reject_nonpositive_cell_count():
    cfg = load_cfg()
    cfg.scenarios[0].n_cells = 0
    with pytest.raises(ValueError, match="n_cells"):
        simulate.generate_dataset(cfg)


def test_cell_random_effects_stay_inside_ledger_ranges():
    cfg = load_cfg()
    cfg.R0_nom_Ohm = cfgmod.PARAMETER_BOUNDS["R0_nom_Ohm"][1]
    cfg.alpha = cfgmod.PARAMETER_BOUNDS["alpha"][1]
    cfg.beta = cfgmod.PARAMETER_BOUNDS["beta"][1]
    cfg.sigma_cell = cfgmod.PARAMETER_BOUNDS["sigma_cell"][1]
    cfgmod.validate_config(cfg)

    for seed in range(100):
        params = deg.make_cell_params(random.Random(seed), cfg)
        assert cfgmod.PARAMETER_BOUNDS["R0_nom_Ohm"][0] <= params["R0"] <= cfgmod.PARAMETER_BOUNDS["R0_nom_Ohm"][1]
        assert cfgmod.PARAMETER_BOUNDS["alpha"][0] <= params["alpha"] <= cfgmod.PARAMETER_BOUNDS["alpha"][1]
        assert cfgmod.PARAMETER_BOUNDS["beta"][0] <= params["beta"] <= cfgmod.PARAMETER_BOUNDS["beta"][1]


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


# ---- 6. 可移植证据链 / 动态标签 ----
def test_default_config_and_test_paths_point_to_repository_config():
    assert os.path.samefile(cfgmod.DEFAULT_CONFIG_PATH, CFG_PATH)
    assert os.path.isfile(CFG_PATH)


def test_csv_uses_explicit_lf_line_endings():
    rows = simulate.generate_dataset(load_cfg())["rows"][:2]
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "sample.csv")
        simulate.write_csv(rows, path)
        with open(path, "rb") as handle:
            content = handle.read()
    assert b"\r\n" not in content
    assert content.endswith(b"\n")


def test_dictionary_does_not_label_synthetic_inputs_as_observed():
    cfg = load_cfg()
    dataset = simulate.generate_dataset(cfg)
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "dictionary.md")
        simulate.write_data_dictionary(path, cfg, dataset["meta"])
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    assert "本 G1 CSV 不包含此类字段" in text
    assert "| cell_id | str | - | 仿真电芯标识" in text
    assert "| cycle | int | cycle | 配置的循环序号（时间轴） | OBSERVED |" not in text


def test_plot_titles_follow_configuration_and_soh_definition():
    cfg = load_cfg()
    cfg.N_cycles = 10
    cfg.scenarios[0].n_cells = 2
    for scenario in cfg.scenarios[1:]:
        scenario.n_cells = 1
    dataset = simulate.generate_dataset(cfg)
    with tempfile.TemporaryDirectory() as directory:
        figures = simulate.generate_plots(cfg, dataset["rows"], directory)
        with open(figures["capacity"], "r", encoding="utf-8") as handle:
            capacity_svg = handle.read()
        with open(figures["knee"], "r", encoding="utf-8") as handle:
            knee_svg = handle.read()
    assert "5 电芯" in capacity_svg
    assert "12 电芯" not in capacity_svg
    assert "baseline SOH 均值" in knee_svg
    assert "baseline_0" not in knee_svg
    assert "SOH (=capacity_true / Q0_i)" in knee_svg


def test_manifest_contains_only_portable_relative_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    out_dir = tmp_path / "g1"
    assert cli.main(["--config", "configs/g1_smoke.json", "--out", str(out_dir)]) == 0
    with open(out_dir / "run_manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    path_fields = [manifest["config_path"], manifest["csv"], manifest["dictionary"]]
    path_fields.extend(manifest["figures"].values())
    assert all(not os.path.isabs(path) for path in path_fields)
    assert all("X:\\" not in path for path in path_fields)
    assert manifest["command"].startswith("PYTHONPATH=code python -m g1_generator.cli")
