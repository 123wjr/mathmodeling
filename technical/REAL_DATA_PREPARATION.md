# 真实数据准备：NMC aging modes 候选层

状态：`PREPARED_LOCALLY_NOT_YET_ACCEPTED`。本文件描述候选真实数据的下载、解析和质量闸门；它不改变 V1 合成实验，也不自动生成论文结果。

## 数据源

- 数据集：`Battery-aging-modes-across-NMC`
- DOI：`10.5281/zenodo.7250553`
- 记录页：<https://zenodo.org/records/7250553>
- 许可证：`CC BY 4.0`
- 原始内容：44 个 NMC/Graphite 单层软包电芯，逐循环容量、库仑效率、充电末端电压和放电末端电压；本轮只接入容量 CSV。
- 公开代码：<https://github.com/hypochen/Battery-aging-modes-across-NMC>

原始压缩包不进入 Git。仓库只保存解析器、运行协议和哈希/质量报告；下载后的文件路径由命令行参数传入。

解析器依赖 `normal` conda 环境中的 `pandas`/`openpyxl`；V1 的 `requirements-study.txt` 不因此扩展。

## 本轮解析边界

`technical/prepare_nmc_modes.py` 只做四件事：读取 `Capacity_CellXX.csv`、解析 `Cycle`/`CycleReorder` 和唯一容量列、连接 `Pouch cell_summary.xlsx` 的电芯元数据、输出 V2 canonical long table。

以下字段故意不猜：

- 容量单位：`UNVERIFIED`。CSV 数值原样保留，不把约 `0.02` 的数值擅自写成 Ah 或 mAh。
- `CycleReorder` 的物理含义：只作为来源提供的循环索引；不推断为 EFC。
- 温度、DOD、内阻：本轮 CSV/summary 未提供可直接映射字段，留空并在 V2 中弃权相关分析。
- RPT 去趋势：原始值不删除、不平滑、不用异常值修饰结果；若后续需要去趋势，必须形成独立预处理版本并报告差异。

NMC532 与 NMC811 只作为分层标签，禁止在一次 V2 运行中混合拟合同一退化参数。

## 运行

```bash
conda run -n normal python technical/prepare_nmc_modes.py \
  --raw-root /path/to/Battery\ raw\ data \
  --summary /path/to/Pouch\ cell_summary.xlsx \
  --raw-zip /path/to/Battery\ raw\ data.zip \
  --readme /path/to/README.txt \
  --out-dir /tmp/nmc_modes_prepared
```

输出：

- `canonical_capacity.csv`：V2 所需的长表；每行是一个电芯-循环观测。
- `canonical_capacity_NMC532.csv`、`canonical_capacity_NMC811.csv`：验证器可直接读取的分层长表；禁止把两者合并拟合。
- `cell_metadata.csv`：每个电芯的化学体系、倍率、协议、寿命摘要和原文件回指。
- `quality_report.json`：文件数、电芯数、行数、循环连续性、summary 对齐和缺失字段。
- `provenance.json`：DOI、许可证、输入路径和 SHA-256。

V2 验证器的入口字段为 `source_id, chemistry, cell_id, cycle, capacity`。`capacity_unit_status=UNVERIFIED` 时，数据只能用于“候选真实数据结构/方向检查”，不能直接写入论文精度表。

## 接受标准

1. 44 个容量文件与 summary 电芯一一对应，且没有重复 `(source_id, cell_id, cycle)`。
2. 每个电芯的循环索引从 1 连续到 CSV 最大循环；summary 的 EOL cycles 与 CSV 最大循环逐芯记录差异。
3. 容量值全部为有限正数；原始文件没有被删行、平滑或重标定。
4. 化学体系、许可证、输入哈希和运行命令写入 provenance；未确认字段保持 `UNVERIFIED`。
5. 通过 V2 的 `GroupKFold(cell_id)`、留工况、bootstrap 和未来信息泄漏闸门后，才允许形成“实测候选验证”结果；在此之前不覆盖 V1 事实表。

当前预期用途：先验证容量退化方向、循环索引完整性和电芯级留组协议。它不是 CALCE INR18650-20R 数据，也不能作为 NMC 18650 主线的直接替代。
