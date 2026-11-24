# 完整候选评分 · GPU 运行报告（protocol-v2.8）

> 日期：2026-11-24。单卡 RTX 4090 串行；bf16/sdpa、28→28 identity affine λ=0.001、zero re-prefill=true。
> PI 授权：保留原失败冒烟产物、以新 run id 重跑冒烟；两冒烟通过后串行跑六正式格。
> 不读封存 test、不做 A01/A10、不重算主终点、不恢复贡献；未改冻结判据/方案/论文/既有正式 run。

## 1. 运行状态总表

| run_id | 版本 / seed | 状态 | 耗时(wall) | 入口内 elapsed | scores / audit records |
| --- | --- | --- | --- | --- | --- |
| `audit_seq_smoke_A11_s0` | fixed/0（原失败，保留） | FAILED（验证脚本 bug，见 §4） | 55s | 49.6s | 18 / 76 |
| `audit_seq_smoke_A11_s0_v2` | fixed/0 冒烟 | **SMOKE_GATE_PASSED_NON_AUTHORITATIVE** | 51s | 46.6s | 18 / 76 |
| `audit_seq_smoke_A00_s0_v2` | legacy/0 冒烟 | **SMOKE_GATE_PASSED_NON_AUTHORITATIVE** | 50s | 45.0s | 18 / 76 |
| `audit_seq_A11_s0` | fixed/0 全量 | **OK** | 91s | 86.6s | 120 / 480 |
| `audit_seq_A00_s0` | legacy/0 全量 | **OK** | 92s | 86.8s | 120 / 480 |
| `audit_seq_A11_s1` | fixed/1 全量 | **OK** | 97s | 92.5s | 120 / 480 |
| `audit_seq_A00_s1` | legacy/1 全量 | **OK** | 91s | 86.3s | 120 / 480 |
| `audit_seq_A11_s2` | fixed/2 全量 | **OK** | 95s | 90.3s | 120 / 480 |
| `audit_seq_A00_s2` | legacy/2 全量 | **OK** | 92s | 87.6s | 120 / 480 |

- 全部 8 个新 run（2 冒烟 v2 + 6 正式）退出码 0；**无 ABORTED、无审计失败**。
- 冒烟 v2 产物在 `reports/_non_authoritative/`；六正式格产物在 `reports/runs/<run_id>/`，
  每格 5 类齐全（config/scores/forward_audit/metrics/manifest）。
- 总耗时：冒烟 v2 101s + 六正式格 558s = **659s wall**（含每次进程内两模型加载与 mapper 拟合）。

## 2. 显存与采集说明

入口**未采集** GPU 显存峰值，故本报告如实记为「未采集」，不编造数值。RTX 4090 单卡串行，运行中无 OOM、
无时长阻塞，全部格正常完成。

## 3. 冒烟门验收（v2 两格）

| 核验项 | A11_s0_v2 | A00_s0_v2 |
| --- | --- | --- |
| 首 token 回放（self→归档 `D_self`，joint→归档 `D_trans`） | 12 对 max diff **4.768e-07** < 0.02 PASS | 12 对 max diff **2.384e-07** < 0.02 PASS |
| 单 token full=first | 冒烟 6 对候选均 2 token，子集内空检（n=0）；见 §5 正式格非空核验 | 同左 |
| 多 token teacher-forcing 位置 | 76 审计 / 152 forward 全 PASS | 同左 |
| 逐次输入审计 `[Q,1×(m−1)]` | 76/76 `audit_passed` | 同左 |
| zero re-prefill | 76/76 `zero_re_prefill=true` | 同左 |
| 候选缓存独立 | 76 实例号 / 76 互异 | 同左 |
| Self/Identity 锚点 | 18 项 max diff = 0（tol 1e-4） | 同左 |
| A/B 顺序交换按候选身份 | 12 项 max diff = 0（tol 1e-5） | 同左 |
| token 边界不一致 | A=0, B=0 | A=0, B=0 |
| 封存 test 未读 | `sealed_test_read=false` | 同左 |

## 4. 原失败产物与根因（保留、未覆盖）

`reports/_non_authoritative/audit_seq_smoke_A11_s0/`（原 rc=3）五类产物完整保留。根因为入口验证脚本
`_archived_first_token_dself()` 对 joint arm 误取归档 `D_self`（归档每行原生 `D_self` 对所有 arm 相同，
arm 自身迁移 D 在 `D_trans`）；修正后 self arm 6 对 diff=0、joint arm 6 对 diff≤4.768e-07。
另修复 `tokenizer_fingerprint()` 对 `AddedToken` 的序列化回退。两处已 CPU 复验（65 passed）。
原失败产物中的 `tokenizer_fingerprint` 为 `unavailable:TypeError`，v2 与正式格均为可用指纹 `5b99b566…`。

## 5. 正式格产物核验（CPU-only verifier）

- 三读数：每格 120 行 scores 全部含 `first/full/length_normalized`；`scores[side][cand]` 双侧两候选齐全。
- **单 token full=first（非空）**：A11 每格 28 个单 token 候选、A00 每格 112 个，
  整串和 − 首 token logprob 的 max abs diff = **0**（严格相等），三格一致。
- 审计：每格 480 条 / A11 932 次 forward、A00 848 次 forward；`audit_passed` 与
  `zero_re_prefill` 全 true；`branch_cache_id` 480/480 互异。
- config：`git_hash=a05e9b3`、`protocol_version=2.8`、`version_tag`、seed、train/val SHA-256、
  `dtype=bfloat16`、`kernel=sdpa`、teacher/student 路径、tokenizer 指纹、`sealed_test_read=false` 齐全。

## 6. 逐格指标事实（非判读，供 scientist 按 v2.8 §7 归类）

| cell/seed | L(first) | L(full) | L(len-norm) | E_CF_joint(first) | E_CF_joint(full) | coverage_joint(first) |
| --- | --- | --- | --- | --- | --- | --- |
| A11_s0 | 0.383 | 0.433 | 0.450 | 6.90 | 15.95 | 0.867 |
| A00_s0 | 0.017 | 0.000 | 0.000 | 1.97 | 1.82 | 0.800 |
| A11_s1 | 0.617 | 0.400 | 0.450 | 8.16 | 17.30 | 0.883 |
| A00_s1 | −0.067 | −0.050 | −0.050 | 1.93 | 1.69 | 0.817 |
| A11_s2 | 0.400 | 0.467 | 0.550 | 8.54 | 19.00 | 0.883 |
| A00_s2 | 0.033 | 0.033 | 0.033 | 2.12 | 1.85 | 0.800 |

每格 6 个 template_family（`exploratory=true`）；配对 `L_full−L_first` 的簇级 bootstrap CI 见各格
`metrics.json` 的 `reading_diff_L_full_minus_L_first`。首/整串/归一三读数并列报告，`E_CF` 绝对尺度
不跨口径比较。本表仅为产物事实陈述，不构成「跨评分方向一致」或「成功/失败」的判读结论。

## 7. 边界声明

- 未做 A01/A10；未读取封存 test；未改 `configs/prereg/*`、`docs/protocol.md`、方案、论文；
  未改任何既有正式 run（本轮新增正式 run 目录 6 个，均为新 id）；原失败冒烟产物保留未覆盖。
- 本实验为读数稳健性补充：不重算 V2.0 主终点、不恢复贡献(1)(2)(3)、不构成方法贡献；结果触发 P5 重审。
