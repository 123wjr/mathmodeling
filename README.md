# A题数学建模项目

这是“锂电池剩余寿命预测与梯次利用筛选优化”项目的代码与证据仓库。

论文主笔 Agent 的唯一入口：[PAPER_AGENT_START_HERE.md](PAPER_AGENT_START_HERE.md)。

| 角色 | 工作位置 | 边界 |
|---|---|---|
| 论文主笔 | `论文草稿.md`（Git canonical）→ 在线文档副本 | 依据仓库事实源写作、维护证据表和引用；不改代码或实验结果 |
| 建模/代码负责人 | GitHub | 修改模型、配置、测试和可复跑产物；每次修改都形成新 commit |
| 总负责人 | 总控台与验收 | 裁决路线、批准数字、执行红队和最终提交 |

## 快速入口

~~~bash
git pull --ff-only origin main
~~~

然后阅读 [PAPER_AGENT_START_HERE.md](PAPER_AGENT_START_HERE.md)，不要从聊天记录或单个 CSV 开始写论文。

最小复跑命令、目录说明和支撑材料边界见 [technical/SUPPORTING_MATERIALS_README.md](technical/SUPPORTING_MATERIALS_README.md)。
