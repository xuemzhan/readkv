# ReadKV 完整候选评分运行清单

| 顺序 | 拟用 run ID | 输入 / 目标 | 状态 |
| --- | --- | --- | --- |
| 0 | CPU 数据审计 | 旧/修复版 × seed 0/1/2 的全量与主分析分母 | 已核对 6×60 对，主分析旧 42/42/41、修复 46/46/46 |
| 1 | `audit_seq_smoke_A11_s0` | 单 token、多 token、Identity、顺序和审计 | 待运行 |
| 2 | `audit_seq_smoke_A00_s0` | 旧版对角格、相同候选与旧读数 | 待运行 |
| 3 | `audit_seq_A11_s0` | 修复版 60 对，固定 mapper 比较评分方式 | 待运行 |
| 4 | `audit_seq_A00_s0` | 旧版 60 对，核验对角翻转 | 待运行 |
| 5–6 | `audit_seq_A11_s1`、`audit_seq_A00_s1` | seed 1 重复上述两格 | 待运行 |
| 7–8 | `audit_seq_A11_s2`、`audit_seq_A00_s2` | seed 2 重复上述两格 | 待运行 |
| 9 | `audit_seq_summary` | CPU 复算、逐 seed 主表与敏感性表 | 待运行 |

全量格中首 token、整串 logprob 和长度归一同次输出。先运行候选边界与缓存审计，再核对 A00/A11 的历史首 token 锚点。 [完整方案](GPU_SEQUENCE_SCORING_PLAN.md)
