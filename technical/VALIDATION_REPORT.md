# A题技术验证报告

## 1. 自动闸门

| 闸门 | 状态 | 证据 |
|---|---|---|
| factorial_shape | PASS | 27 conditions, 108 cells, 108000 rows |
| q1_weights_capacity_fade | PASS | three main-effect weights sum to 1 |
| q1_weights_final_resistance_growth | PASS | three main-effect weights sum to 1 |
| q1_protocol_honesty | PASS | one CC-CV level produces no fabricated protocol weight |
| q2_cell_group_split | PASS | GroupKFold cell overlap = 0 |
| q2_censor_accounting | PASS | 43 events + 65 censored = 108 |
| q3_milp_constraints | PASS | exact target groups; duplicate cells = 0; wrong group sizes = 0 |
| q4_ood_abstention | PASS | four OOD cases have null numeric predictions |
| q4_seed_completeness | PASS | all scenarios include 5 seeds |

## 2. 统计完整性

- `[CONFIRMED]` 数据划分为 `GroupKFold(cell_id)`，5 折的 `cell_id` 交集均为 0。
- `[CONFIRMED]` RUL 可观测事件 43，右删失 65；点误差未把删失下界当真值，AFT 名义 90% 事件覆盖率为 0.9070。
- `[CONFIRMED]` Q1 膝点只在实际覆盖 nominal knee 的电芯上检测；未覆盖者写 `RIGHT_CENSORED`。
- `[CONFIRMED]` Q3 MILP 重复分配=0，错误组规模=0。
- `[CONFIRMED]` OOD 表的所有 `numeric_prediction` 均为空。

## 3. 科学诚信闸门

- `[CONFIRMED]` 全部数值来自合成数据；文档未使用“CALCE 实测校准”“外部验证”或“真实安全概率”表述。
- `[CONFIRMED]` 结构匹配 RUL 结果单独标为 simulator ceiling，不能反向证明 G1 生成器真实。
- `[ASSUMED][UPDATEABLE]` 80% SOH、筛选门槛、批次代理、权重与成本收益均可从配置追溯。
- `[UNCERTAIN]` 真实数据泛化、范围外工况、货币收益及安全失效概率仍未解决。

## 4. 可能推翻当前结论的证据

1. 真实同化学体系数据若显示温度/倍率/DOD 方向或阶段结构相反，应重开 G0 并替换生成器。
2. 若独立数据留组误差显著高于仿真，论文必须以独立数据为准，仿真精度降为机制演示。
3. 若筛选门槛无法对应真实检测误差或安全规范，Q3 只保留优化框架，不保留阈值结论。
4. 若批次分布可取得，应删除当前批次代理，改用分层随机效应或实测批次固定效应。

## 5. 复核命令

```bash
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
git diff --check
```

实际 pytest 数量和 stdout 以最终总验收记录为准；本文件只声明流水线内部闸门。
