# A题支撑材料说明

论文主笔 Agent 的编辑源是 [论文草稿.md](../论文草稿.md)；技术过渡入口是 [PAPER_TECHNICAL_BRIDGE.md](PAPER_TECHNICAL_BRIDGE.md)。本页只负责复跑和支撑材料打包。

## 1. 最小复跑

环境：Python 3.13；精确运行版本见 `study_output/run_manifest.json`，安装清单见 `requirements-study.txt`。

```bash
python -m pip install -r requirements-study.txt
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
```

## 2. 目录

- `code/g1_generator/`：G1 分段平方根退化生成器。
- `code/battery_study/`：Q1 阶段/主效应、Q2 SOH/RUL、Q3 MILP、Q4 鲁棒性和报告生成。
- `configs/`：全部固定参数、工况、seed、阈值和权重。
- `g1_output/`：G1 冒烟数据、图和清单。
- `study_output/`：G2-G4 CSV/JSON/SVG、验证闸门和 SHA-256 清单。
- `technical/`：四段最小技术报告、实验计划、验证报告、论文取数表和 A5 技术过渡层。
- `handoffs/A1-A5*.md`：论文与代码之间的交接证据包。

## 3. 事实源顺序

1. `study_output/run_manifest.json` 中的配置/源码/产物哈希。
2. `study_output/validation_gates.json` 和 CSV/JSON 结果。
3. `technical/PAPER_WRITING_FACT_SHEET.md` 的论文可写数字。
4. 图表和叙述文档；聊天数字不作为事实源。

108000 行全因子原始合成记录不重复提交；它们由固定代码、配置和 seed 确定性重建。支撑材料保留 108 行电芯摘要和全部模型预测，减少提交体积但不牺牲复现性。

## 4. 科学边界

- `[CONFIRMED]` 这是 NMC 合成仿真，不是 CALCE 实测拟合。
- `[ASSUMED][UPDATEABLE]` 退化参数、80% SOH、筛选门槛、批次代理、经济权重。
- `[UNCERTAIN]` 真实泛化、安全概率和货币收益。
- `[OOD/ABSTAIN]` 低温、过充、过放和 >2C 均无数值预测。

提交前只需将论文 PDF 与本目录结构一并打包；不要提交 `.git/`、`__pycache__/`、`.pytest_cache/` 或浏览器临时文件。
