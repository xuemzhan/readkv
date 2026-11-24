# ReadKV 完整候选评分运行清单

> 更新：2026-11-24。PI 授权后用修正入口以新 run id 重跑冒烟并通过；六个正式格串行完成，全部 rc=0。
> 原失败冒烟产物按要求保留、未覆盖；未做 A01/A10，未读封存 test。

| 顺序 | run ID | 输入 / 目标 | 状态 |
| --- | --- | --- | --- |
| 0 | CPU 数据审计 | 旧/修复版 × seed 0/1/2 全量与主分析分母 | 已核对 6×60 对，主分析旧 42/42/41、修复 46/46/46；token 边界异常 0 |
| — | `audit_seq_smoke_A11_s0`（原失败） | 首 token 回放验证脚本字段错配 | **FAILED 产物保留**（`reports/_non_authoritative/`），未覆盖；根因与修复见 `reports/review/sequence_scoring_run_report.md` |
| 1 | `audit_seq_smoke_A11_s0_v2` | fixed/seed0 冒烟（新 ID） | **PASS**（`SMOKE_GATE_PASSED_NON_AUTHORITATIVE`，51s）；回放 max diff 4.768e-07 |
| 2 | `audit_seq_smoke_A00_s0_v2` | legacy/seed0 冒烟（新 ID） | **PASS**（`SMOKE_GATE_PASSED_NON_AUTHORITATIVE`，50s）；回放 max diff 2.384e-07 |
| 3 | `audit_seq_A11_s0` | 修复版 60 对全量 | **OK**（91s）；120 scores / 480 audit records |
| 4 | `audit_seq_A00_s0` | 旧版 60 对全量 | **OK**（92s）；120 / 480 |
| 5 | `audit_seq_A11_s1` | 修复版 seed1 全量 | **OK**（97s）；120 / 480 |
| 6 | `audit_seq_A00_s1` | 旧版 seed1 全量 | **OK**（91s）；120 / 480 |
| 7 | `audit_seq_A11_s2` | 修复版 seed2 全量 | **OK**（95s）；120 / 480 |
| 8 | `audit_seq_A00_s2` | 旧版 seed2 全量 | **OK**（92s）；120 / 480 |
| 9 | `audit_seq_summary` | CPU 复算、逐 seed 主表与敏感性表 | 未运行（scientist 任务；本次 engineer 交付止于正式格产物） |

## 验收摘要（2026-11-24）

- 两个 v2 冒烟门全通过：self arm 比归档 `D_self`、joint arm 比归档 `D_trans`；首 token 回放 12 对
  max diff 4.768e-07 / 2.384e-07（tol 0.02）；逐次审计 76 条 / 152 次 forward 全 pass、
  zero re-prefill=true、候选缓存实例 76/76 互异、Self/Identity max diff=0、A/B 顺序交换 max diff=0、
  token 边界异常 0、未读封存 test。单 token full=first 在冒烟 6 对上为空检（候选均 2 token），
  已在正式格 scores 上非空核验（A11 28 对、A00 112 对候选，max diff=0）。
- 六格全部 `status=OK`，无 ABORTED；每格 120 scores / 480 audit records，
  三读数（first/full/length_normalized）齐全；逐次审计与 zero re-prefill 全 pass；
  config 含 git_hash `a05e9b3`、protocol_version=2.8、版本标签、seed、train/val SHA-256、
  bf16/sdpa、模型路径与 tokenizer 指纹 `5b99b566…`、`sealed_test_read=false`。
- 显存峰值：入口未采集，如实记为未采集（不编造）。六格 wall 合计 558s，冒烟 v2 合计 101s。

全量格中首 token、整串 logprob 和长度归一同次输出。先运行候选边界与缓存审计，再核对 A00/A11 的历史首 token 锚点。 [完整方案](GPU_SEQUENCE_SCORING_PLAN.md)
