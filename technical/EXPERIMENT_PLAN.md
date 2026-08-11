# A题实验计划（实现冻结版）

## 1. 研究目标与假设

- `[CONFIRMED]` Q1：在 G0 支持域内辨识阶段边界及温度、倍率、DOD 主效应；单一 CC-CV 不估计协议效应。
- `[ASSUMED][UPDATEABLE]` H1：压力水平升高时容量衰减和内阻增长加快；阶段阈值为 SOH=0.8。
- `[CONFIRMED]` Q2：比较透明基线与统计学习模型，数据切分单位为电芯；RUL 使用右删失似然或明确标注删失朴素模型。
- `[ASSUMED][UPDATEABLE]` Q3：硬门槛先于优化；组大小=4，成本收益均为无量纲指数。
- `[CONFIRMED]` Q4：只在冻结支持域内做数值鲁棒性；范围外强制弃权。

## 2. 数据设计

1. 全因子 `T=[25.0, 35.0, 45.0]`、`C-rate=[0.5, 1.0, 2.0]`、`DOD=[50.0, 80.0, 100.0]`，每格 4 电芯，每芯 1000 cycles。
2. Q2 历史窗口 100 cycles，预测步长 50 cycles，landmark=300；5 折 `GroupKFold(cell_id)`。
3. 90% 区间按电芯 bootstrap 300 次；AFT 训练事件残差校准分位=0.99；leave-one-condition-out 覆盖全部 27 工况。
4. Q3 退役快照 cycle=750；先筛选，再枚举相似候选组，最后 set-packing MILP。
5. Q4 使用 seeds=[42, 123, 2026, 4096, 8110]，7 参数 +/-10% OAT，并另设假设批次代理。

## 3. 评价与验收

- Q1：主效应权重、总方差占比、膝点可观测/右删失数；同构膝点误差只作实现检查。
- SOH：MAE、RMSE、R2、90% cell-bootstrap 区间；报告 GroupKFold 与 leave-condition-out。
- RUL：仅可观测事件 MAE/RMSE/R2、删失样本提前失效矛盾率、AFT 90% 事件覆盖。
- Q3：筛选率、目标、组数、重复电芯数、错误组规模、MILP 与 greedy 差值。
- Q4：seed 间 p10--p90、SOH 误差、临界比例、筛选/成组率、OAT 局部敏感度、OOD 空数值。

## 4. 更新规则

- `[UPDATEABLE]` 若取得真实 CALCE/企业数据：先建立化学体系和测试协议映射，再校准参数；不得覆盖原仿真标签。
- `[UPDATEABLE]` 若取得成本、安全或评分细则：只修改 JSON 中门槛/权重并全量重跑，不在论文中手改结果。
- `[UNCERTAIN]` 无真实批次与安全事件数据时，不拟合安全概率、不做货币化收益、不宣称行业阈值。
- `[OOD/ABSTAIN]` 任何超出 25--50 degC、0.5--2C、DOD 50--100%、CC-CV 的查询都保持空数值。

执行命令：

```bash
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
```
