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

## B0 rerun（2026-11-24 · R1 关闭执行）

> PI 裁决 `docs/decisions/sequence_scoring_baseline_ruling.md`；冻结基线 `35e78e06917eb16461d6c925c8b0a435e99fd39c`（短 `35e78e0`）。
> B0 后产出代码 diff 为空（执行前已确认，执行后再次确认）；未改判据/数据/论文；未做 A01/A10、未碰封存 test。

| 顺序 | run ID | 状态 | wall |
| --- | --- | --- | --- |
| B0-1 | `audit_seq_smoke_A11_s0_b0` | SMOKE_GATE_PASSED_NON_AUTHORITATIVE（git_hash=35e78e0） | 52s |
| B0-2 | `audit_seq_smoke_A00_s0_b0` | SMOKE_GATE_PASSED_NON_AUTHORITATIVE（git_hash=35e78e0） | 54s |
| B0-3 | `audit_seq_A11_s0_b0` | OK | 95s |
| B0-4 | `audit_seq_A00_s0_b0` | OK | 91s |
| B0-5 | `audit_seq_A11_s1_b0` | OK | 91s |
| B0-6 | `audit_seq_A00_s1_b0` | OK | 90s |
| B0-7 | `audit_seq_A11_s2_b0` | OK | 92s |
| B0-8 | `audit_seq_A00_s2_b0` | OK | 90s |
| B0-汇总 | `audit_seq_summary_b0` | CPU 汇总已生成（`reports/review/sequence_scoring_summary_b0.md`），无 GPU run | — |

- 权威集仅 `_b0` 八格 + `audit_seq_summary_b0`；旧 6 正式 + 2 v2 冒烟 + 原失败冒烟共 9 id 已在
  `reports/runs_index.json` 标 `superseded=true` / `authoritative=false`，reason 用裁决 §4.2 原文；文件保留未删改。
- 重跑审计（临时输出，未覆盖仓库报告）：`consistency_check` 对 6 个正式 `_b0` run 报
  `git_hash_in_history=true`、`traceable=true`、`run_code_unchanged_vs_head=true`、
  `protocol_compat.ok=true`、`v28_fields.ok=true`，problems 为空；`bootstrap_ci_report` 对 6 格产出
  first/full/length_normalized 三读数主 CI + pair 敏感性，排除数 0。结果交 reviewer。
- 显存峰值入口未采集，如实记录；B0 后未改 §2.2 产出代码，无 B1 需求。
