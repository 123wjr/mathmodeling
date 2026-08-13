# V3-A+B 实验实施计划

> **执行者要求：** 按 TDD 顺序逐项执行；每个行为先写失败测试，再写最小实现。
> **目标：** 建立 cycle 750 条件 RUL、区间风险编组、固定编组压力追踪、稳定性扫描和 Q2 消融的可复跑证据链。
> **架构：** 复用 `battery_study` 的数据、AFT、MILP 和输出工具；V3 增量集中在 `battery_study/v3.py`，独立 CLI 和输出目录，不修改 V1/V2 结果。
> **技术栈：** Python、NumPy、SciPy、scikit-learn、pytest。

## 任务 1：配置与风险集

- [x] 风险集测试与实现：排除 `T<=750`，剩余 duration 按 `T-750` 或 250 构造；定向测试通过。
- [x] 配置、窗口、门槛、seed 和支持域校验已实现。
- [x] `retirement_risk_set` 只读取 cycle=750 特征，风险集计数闭合。

## 任务 2：条件 RUL 与决策对照

- [x] OOF AFT 留组、条件 RUL、POINT/INTERVAL_RISK 门槛和 Q3 输出已实现并通过测试。

## 任务 3：固定编组压力追踪

- [x] 固定组成员/组号、cycle=750 连续、增量退化和三态触发已实现；5 场景 x 8 组 x 4 芯输出闭合。

## 任务 4：稳定性与消融

- [x] 5 seed x 9 OAT 点、Jaccard/实际门槛裕度和 48 项消融已实现；完整矩阵通过闸门。

## 任务 5：流水线与证据

- [x] 独立 CLI、12 个自动验证闸门、V3 验证报告和 manifest SHA-256 已完成。
- [ ] 运行：

```bash
PYTHONPATH=code python -m battery_study.v3_cli \
  --config configs/study_pipeline_v3.json \
  --out study_output_v3
PYTHONPATH=.:code python -m pytest code/tests -q
git diff --check
```

- [x] 最终复跑：12 个闸门 PASS；全量测试 `93 passed, 1 skipped`；manifest PASS；文档已按最新产物更新。

> 区间风险注意：AFT 预测上下界保留原始拟合值；`max_lifetime_interval_width` 只作为显式、可更新的筛选门槛，不得先截断上下界再计算宽度。

## 停止条件

- 条件 AFT 无法稳定拟合：停止 V3 RUL/编组数字，保留设计与失败报告。
- 风险集事件数不足或折内无事件：减少折数必须先记录设计变更，不静默改口径。
- Q4 无法证明成员固定或 cycle 750 连续：不得称纵向压力追踪。
- 任一 manifest 哈希缺失、V1/V2 被覆盖：V3 不放行。
