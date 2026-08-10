"""G1 核心退化逻辑：分段平方根容量/内阻退化生成器。

严格遵循 docs/Simulation_Protocol.md 第 6/7/8/10 节与 G0 冻结决策：
- 分段平方根 L(e)，膝点处连续，膝点后仅提高斜率（knee_gain=2.0）
- 工况修正 u_T, u_C, u_D
- 截断正态个体差异（初始容量/内阻 + 退化速率）
- 测量噪声（仅作用于观测值，不改变总体方向）
- 输入边界校验
"""
from __future__ import annotations

import math
import random


def truncated_normal(rng: random.Random, mu: float, sigma: float, low: float, high: float) -> float:
    """在 [low, high] 内拒绝采样截断正态。"""
    while True:
        x = rng.gauss(mu, sigma)
        if low <= x <= high:
            return x


def cell_seed(master_seed: int, scenario_idx: int, cell_index: int) -> int:
    """确定性组合主种子与电芯索引，保证可复现且不同主种子产生不同电芯。"""
    s = (int(master_seed) * 1000003 + scenario_idx * 10007 + cell_index * 101) & 0x7FFFFFFF
    return s


def make_cell_params(rng: random.Random, cfg):
    """每颗电芯的独立参数：初始容量/内阻 + 退化速率，均带截断正态随机效应。"""
    sigma = cfg.sigma_cell
    low, high = -2.0 * sigma, 2.0 * sigma
    eps_Q = truncated_normal(rng, 0.0, sigma, low, high)
    eps_R = truncated_normal(rng, 0.0, sigma, low, high)
    eta_Q = truncated_normal(rng, 0.0, sigma, low, high)
    eta_R = truncated_normal(rng, 0.0, sigma, low, high)

    Q0 = cfg.Q_nom_Ah * (1.0 + eps_Q)
    R0 = cfg.R0_nom_Ohm * (1.0 + eps_R)
    alpha_i = cfg.alpha * (1.0 + eta_Q)
    beta_i = cfg.beta * (1.0 + eta_R)

    # 物理/台账范围兜底（协议要求截断后仍在可行域）
    Q0 = max(0.01, Q0)
    R0 = min(max(0.005, R0), 0.20)
    alpha_i = min(max(0.001, alpha_i), 0.02)
    beta_i = min(max(0.001, beta_i), 0.05)
    return {"Q0": Q0, "R0": R0, "alpha": alpha_i, "beta": beta_i}


def u_factors(T: float, C: float, DOD: float, cfg):
    """工况修正系数。"""
    u_T = math.exp(cfg.k_T * (T - 25.0))
    u_C = 1.0 + cfg.k_C * (C - 0.5)
    u_D = 1.0 + cfg.k_D * (DOD / 100.0 - 0.5)
    return u_T, u_C, u_D


def L(e: float, cfg) -> float:
    """分段平方根累计退化量，膝点 n_k 处连续。"""
    nk = cfg.n_k_EFC
    return math.sqrt(min(e, nk)) + cfg.knee_gain * max(0.0, math.sqrt(e) - math.sqrt(nk))


def soh_factor(e: float, alpha_i: float, u_T: float, u_C: float, u_D: float, cfg) -> float:
    """退化因子（相对额定容量）：SOH_factor = 1 - alpha_i*u*L(e)。"""
    return 1.0 - alpha_i * u_T * u_C * u_D * L(e, cfg)


def capacity_at(e: float, params: dict, u, cfg) -> float:
    return params["Q0"] * soh_factor(e, params["alpha"], u[0], u[1], u[2], cfg)


def resistance_at(e: float, params: dict, u, cfg) -> float:
    return params["R0"] * (1.0 + params["beta"] * u[0] * u[1] * u[2] * L(e, cfg))


def generate_cell(cfg, scenario, scenario_idx: int, cell_index: int):
    """生成单颗电芯的完整循环轨迹（1..N_cycles）。"""
    rng = random.Random(cell_seed(cfg.seed, scenario_idx, cell_index))
    params = make_cell_params(rng, cfg)
    u = u_factors(scenario.temperature_C, scenario.c_rate, scenario.dod_pct, cfg)

    N = cfg.N_cycles
    dod = scenario.dod_pct
    sigma_Q_std = (cfg.sigma_Q_pct / 100.0) * cfg.Q_nom_Ah

    rows = []
    for cycle in range(1, N + 1):
        efc = cycle * dod / 100.0
        e = efc
        c_true = capacity_at(e, params, u, cfg)
        r_true = resistance_at(e, params, u, cfg)

        c_obs = c_true + rng.gauss(0.0, sigma_Q_std)
        r_obs = r_true + rng.gauss(0.0, (cfg.sigma_R_pct / 100.0) * r_true)
        c_obs = max(1e-4, c_obs)
        r_obs = max(1e-4, r_obs)

        # SOH 严格按协议第6节定义为相对该电芯初始容量 Q0_i 的健康度：
        # SOH_i(e) = 1 - alpha_i*u*L(e) = capacity_true / Q0_i（起点恒为 1）
        soh = c_true / params["Q0"]
        rows.append({
            "cell_id": f"{scenario.id}_{cell_index}",
            "cycle": cycle,
            "efc": round(efc, 6),
            "temperature": scenario.temperature_C,
            "c_rate": scenario.c_rate,
            "dod": dod,
            "protocol": scenario.protocol,
            "capacity_true": round(c_true, 6),
            "capacity_obs": round(c_obs, 6),
            "soh": round(soh, 6),
            "resistance_true": round(r_true, 6),
            "resistance_obs": round(r_obs, 6),
            "seed": cfg.seed,
        })
    return rows


def validate_config(cfg):
    """输入边界校验：温度 25-50、DOD 0-100、正倍率、CC-CV 协议。"""
    errs = []
    if cfg.seed is None:
        errs.append("seed 未设置")
    for s in cfg.scenarios:
        if not (25.0 <= s.temperature_C <= 50.0):
            errs.append(f"scenario {s.id}: 温度 {s.temperature_C} 超出 [25,50] degC")
        if not (0.0 < s.dod_pct <= 100.0):
            errs.append(f"scenario {s.id}: DOD {s.dod_pct} 不在 (0,100]")
        if not (s.c_rate > 0.0):
            errs.append(f"scenario {s.id}: 倍率 {s.c_rate} 非正")
        if s.protocol != "CC-CV":
            errs.append(f"scenario {s.id}: 协议 {s.protocol} 不支持（仅 CC-CV）")
    if errs:
        raise ValueError("; ".join(errs))
