"""从 V3 证据表生成四张中文期刊风格图。"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "study_output_v3"
OUT = DATA / "final_figures"
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
COLORS = {
    "blue": "#0077BB", "cyan": "#33BBEE", "teal": "#009988",
    "orange": "#EE7733", "red": "#CC3311", "grey": "#A7A9AC",
    "dark": "#24292F", "light": "#EEF1F4",
}


def configure_style() -> None:
    if not FONT_REGULAR.is_file() or not FONT_BOLD.is_file():
        raise FileNotFoundError("缺少 Noto Sans CJK 中文字体，停止生成图片")
    regular = FontProperties(fname=FONT_REGULAR).get_name()
    mpl.font_manager.fontManager.addfont(FONT_REGULAR)
    mpl.font_manager.fontManager.addfont(FONT_BOLD)
    mpl.rcParams.update({
        "font.family": regular, "font.size": 9, "axes.titlesize": 11,
        "axes.labelsize": 9.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "axes.spines.top": False,
        "axes.spines.right": False, "axes.linewidth": 0.8,
        "grid.color": "#D9DDE2", "grid.linewidth": 0.55,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "savefig.bbox": "tight",
        "svg.fonttype": "none", "svg.hashsalt": "mathmodeling-v3-final",
    })


def save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.svg")
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    plt.close(fig)


def read_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.is_file():
        raise FileNotFoundError(f"缺少实验结果：{path}")
    return pd.read_csv(path)


def plot_capacity_landscape() -> None:
    frame = read_csv("q3_stability_sweep.csv")
    if len(frame) != 45 or frame["infeasible"].astype(str).str.lower().eq("true").sum() != 44:
        raise ValueError("OAT 证据口径变化：预期 45 行、44 次显式弃权")
    fig, ax = plt.subplots(figsize=(6.9, 4.8), constrained_layout=True)
    styles = {
        "ACCEPT_FIXED_GROUPS": (COLORS["teal"], "o", "接受固定编组"),
        "ABSTAIN_INSUFFICIENT_FEASIBILITY": (COLORS["orange"], "X", "显式弃权"),
    }
    for status, (color, marker, label) in styles.items():
        part = frame[frame["decision_status"] == status]
        ax.scatter(part["eligible_cells"], part["max_feasible_groups"], s=54,
                   color=color, marker=marker, edgecolor="white", linewidth=0.5,
                   alpha=0.82, label=f"{label}（n={len(part)}）", zorder=3)
    ax.axhline(8, color=COLORS["red"], linestyle="--", linewidth=1.2,
               label="目标产能：8 组", zorder=2)
    ax.set(xlabel="风险筛选后可用电芯数（个）", ylabel="最大可信编组数（组）",
           title="参数扰动下的可信产能景观")
    ax.set_ylim(2.6, 8.5)
    ax.grid(axis="both", zorder=0)
    ax.legend(frameon=False, loc="lower right")
    ax.text(0.01, 0.98, "45 个离散 OAT 参数点；重合点保留透明叠加",
            transform=ax.transAxes, ha="left", va="top", color="#5B616B", fontsize=8)
    save(fig, "fig1_capacity_landscape")


def _short_cell_id(value: str) -> str:
    return value.replace("baseline", "基准").replace("_C", "·C").replace("_D", "·D")


def plot_selection_stability() -> None:
    frame = read_csv("q3_stability_sweep.csv")
    if len(frame) != 45 or "selected_cell_ids" not in frame:
        raise ValueError("电芯稳定性图要求 45 行 OAT 及 selected_cell_ids")
    selections = [set(str(value).split(";")) - {"", "nan"} for value in frame["selected_cell_ids"]]
    if any(len(ids) != count for ids, count in zip(selections, frame["selected_cell_count"])):
        raise ValueError("selected_cell_ids 与 selected_cell_count 不一致")
    all_ids = sorted(set().union(*selections))
    matrix = pd.DataFrame([[cell in ids for ids in selections] for cell in all_ids],
                          index=all_ids, dtype=int)
    frequency = matrix.sum(axis=1)
    ranked = frequency.sort_values(kind="stable")
    chosen = list(ranked.head(8).index) + list(ranked.tail(8).index)
    chosen = list(dict.fromkeys(chosen))
    matrix = matrix.loc[chosen]
    frequency = frequency.loc[chosen]

    fig = plt.figure(figsize=(6.9, 5.3), constrained_layout=True)
    grid = fig.add_gridspec(1, 2, width_ratios=(5.7, 1.25), wspace=0.04)
    ax = fig.add_subplot(grid[0, 0])
    bar = fig.add_subplot(grid[0, 1], sharey=ax)
    ax.imshow(matrix.values, aspect="auto", interpolation="nearest",
              cmap=ListedColormap([COLORS["light"], COLORS["blue"]]), vmin=0, vmax=1)
    ax.set_title("电芯入选稳定性（高频与低频代表电芯）", loc="left")
    ax.set_xlabel("OAT 参数点（按 5 个随机种子分块）")
    ax.set_ylabel("电芯编号")
    ax.set_yticks(range(len(matrix)), labels=[_short_cell_id(x) for x in matrix.index])
    ax.set_xticks(range(0, 45, 5), labels=range(1, 46, 5))
    for boundary in (8.5, 17.5, 26.5, 35.5):
        ax.axvline(boundary, color="white", linewidth=1.4)
    bar.barh(range(len(frequency)), frequency.values / 45 * 100,
             color=COLORS["teal"], height=0.65)
    bar.set_title("入选频率", fontsize=9)
    bar.set_xlabel("%")
    bar.set_xlim(0, 100)
    bar.tick_params(axis="y", left=False, labelleft=False)
    bar.grid(axis="x")
    for y, count in enumerate(frequency.values):
        bar.text(count / 45 * 100 + 1.5, y, f"{count}/45", va="center", fontsize=7.2)
    bar.spines["left"].set_visible(False)
    ax.legend(handles=[
        Line2D([0], [0], marker="s", linestyle="", color=COLORS["blue"], label="入选"),
        Line2D([0], [0], marker="s", linestyle="", color=COLORS["light"], label="未入选"),
    ], frameon=True, facecolor="white", edgecolor="none", ncol=2, loc="upper right")
    save(fig, "fig2_cell_selection_stability")


def plot_observation_sensitivity() -> None:
    metrics = read_csv("observation_model_metrics.csv")
    decisions = read_csv("observation_decision_sensitivity.csv")
    regimes = ["none", "light", "heavy"]
    regime_cn = ["无压力", "轻度", "重度"]
    model_cn = {"ridge": "岭回归", "random_forest": "随机森林",
                "local_linear": "局部线性", "persistence": "持续性基线"}
    model_order = ["ridge", "random_forest", "local_linear", "persistence"]
    if set(metrics["regime"]) != set(regimes) or set(decisions["regime"]) != set(regimes):
        raise ValueError("观测压力档位必须为 none/light/heavy")
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 4.5), constrained_layout=True,
                             gridspec_kw={"width_ratios": (1.2, 1)})
    ax = axes[0]
    markers = ["o", "s", "^", "D"]
    palette = [COLORS["blue"], COLORS["orange"], COLORS["teal"], COLORS["grey"]]
    for model, marker, color in zip(model_order, markers, palette):
        part = metrics[metrics["model"] == model].set_index("regime").loc[regimes]
        ax.plot(regime_cn, part["rmse"], marker=marker, color=color, linewidth=1.6,
                markersize=5, label=model_cn[model])
    ax.set(title="a 预测误差", xlabel="观测压力档", ylabel="SOH 预测 RMSE")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y")
    ax.legend(frameon=False, loc="upper left")

    ax = axes[1]
    table = decisions.set_index("regime").loc[regimes]
    raw = np.array([
        table["eligible_cells"].to_numpy(),
        table["max_feasible_groups"].to_numpy(),
        table["selected_cell_jaccard_vs_none"].to_numpy(),
    ], dtype=float)
    row_min, row_max = raw.min(axis=1, keepdims=True), raw.max(axis=1, keepdims=True)
    normalized = np.divide(raw - row_min, row_max - row_min,
                           out=np.full_like(raw, 0.5), where=(row_max > row_min))
    ax.imshow(normalized, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set(title="b 决策敏感性", xticks=range(3), xticklabels=regime_cn,
           yticks=range(3), yticklabels=["可用电芯数（个）", "最大可信组数（组）", "成员 Jaccard"])
    for row in range(3):
        for col in range(3):
            label = f"{raw[row, col]:.3f}" if row == 2 else f"{int(raw[row, col])}"
            ax.text(col, row, label, ha="center", va="center",
                    color="white" if normalized[row, col] > 0.58 else COLORS["dark"],
                    fontweight="bold")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.suptitle("观测层压力下的预测与决策敏感性", fontweight="bold")
    save(fig, "fig3_observation_decision_sensitivity")


def plot_fixed_group_matrix() -> None:
    frame = read_csv("q4_fixed_group_summary.csv")
    scenario_order = list(dict.fromkeys(frame["scenario"]))
    groups = sorted(frame["group_number"].unique())
    if len(frame) != 40 or len(scenario_order) != 5 or groups != list(range(1, 9)):
        raise ValueError("固定编组矩阵要求 5 个场景 × 8 组")
    if frame["group_signature"].nunique() != 1:
        raise ValueError("压力追踪期间编组签名发生变化")
    statuses = ["STABLE_UNDER_SCENARIO", "REINSPECT", "REJECT_FORCED_ASSIGNMENT"]
    labels = ["稳定", "复检", "拒绝强制编组"]
    colors = [COLORS["teal"], COLORS["orange"], COLORS["red"]]
    code = {status: i for i, status in enumerate(statuses)}
    pivot = frame.pivot(index="scenario", columns="group_number", values="trigger").loc[scenario_order, groups]
    matrix = pivot.map(code.__getitem__).to_numpy()
    scenario_cn = {
        "baseline_use": "基准使用", "high_temperature": "高温",
        "high_c_rate": "高倍率", "high_dod": "深放电", "deep_dod": "深放电",
        "combined_stress": "复合压力",
    }
    fig, ax = plt.subplots(figsize=(6.9, 4.1), constrained_layout=True)
    ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap=ListedColormap(colors), vmin=-0.5, vmax=2.5)
    ax.set(title="固定编组压力追踪触发状态矩阵", xlabel="固定组号",
           ylabel="压力场景", xticks=range(8), xticklabels=[f"第{x}组" for x in groups],
           yticks=range(5), yticklabels=[scenario_cn.get(x, x) for x in scenario_order])
    ax.set_title("固定编组压力追踪触发状态矩阵", pad=22)
    ax.set_xticks(np.arange(-0.5, 8, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.6)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.legend(handles=[Line2D([0], [0], marker="s", linestyle="", color=color, label=label)
                       for color, label in zip(colors, labels)],
              frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    counts = frame["trigger"].value_counts()
    ax.text(0.5, 1.02,
            f"同一批电芯，不重新筛选/优化；稳定 {counts.get(statuses[0], 0)}，复检 {counts.get(statuses[1], 0)}，拒绝 {counts.get(statuses[2], 0)}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8, color="#5B616B")
    save(fig, "fig4_fixed_group_trigger_matrix")


def write_captions() -> None:
    text = "# 最终图组图注\n\n"
    text += "1. **参数扰动下的可信产能景观。** 45 个离散单因素扰动（OAT）参数点中，颜色表示接受固定编组或因可行性不足而显式弃权；虚线为 8 组目标。点重合不代表连续 Pareto 前沿。\n"
    text += "2. **电芯入选稳定性。** 展示跨 45 个 OAT 参数点入选频率最高和最低的代表性电芯；频率分母固定为 45，是仿真参数扫描频率，不是真实可靠性概率。\n"
    text += "3. **观测层压力下的预测与决策敏感性。** 左图比较四种模型在无、轻度和重度观测压力下的 SOH 预测 RMSE；右图分别按行着色并标注可用电芯数、最大可信组数和成员 Jaccard 原值，行间颜色不可比较。\n"
    text += "4. **固定编组压力追踪状态矩阵。** 对 Q3 选出的同一 8 组电芯在 5 个压力场景中追踪触发状态，全程不重新筛选、不重新优化。\n"
    (OUT / "CAPTIONS.md").write_text(text, encoding="utf-8")


def main() -> None:
    configure_style()
    plot_capacity_landscape()
    plot_selection_stability()
    plot_observation_sensitivity()
    plot_fixed_group_matrix()
    write_captions()
    print(f"已生成 4 张 SVG + 4 张 600 DPI PNG：{OUT}")


if __name__ == "__main__":
    main()
