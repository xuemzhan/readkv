# 2×2 GPU 补充实验 · 独立审计入口 + seed0 冒烟门报告（task 2）

> 日期：2026-11-23。依据：`docs/gpu_task_schedule.md` §1 task2 / §2 重试协议、`docs/decisions/gpu_supplement_ruling.md` §2 task3、`configs/prereg/gpu_followup_v2.7.yaml`（frozen）、`refine-logs/EXPERIMENT_PLAN.md` §1/§3。
> 本轮**只做 task 2**，未跑任何正式格；冒烟产物标 non-authoritative（`reports/_non_authoritative/`），不作证据。

## 1. 入口实现

- **路径**：`experiments/audit_2x2_gpu.py`（--cell/--seed/--cal-version/--val-version/四份显式 JSONL 路径）。
- **独立性**：显式接收 `train-old/train-fixed/val-old/val-fixed` 四份路径，只从这些文件读 CFPair 记录；**绝不调用 P1_gpu.py / run_cf_pipeline 的自动重建数据与质量门**。
- **固定口径**：bfloat16/sdpa、等深 28→28 identity layer map、逐层逐头 K/V affine、ridge λ=0.001、首 token 评分、严格 zero re-prefill。
- **记录**：输入四份 JSONL 的 sha256、样本指纹（sample_hash/sample_id/version_tag）、逐对各臂分数（self/identity/joint/k_only/v_only/control:random/zero/mismatch）、旧版缺陷告警、缓存恒等性/Joint 输入审计、耗时。
- **审计告警**：legacy 格登记 `degenerate_must_flip`（冒烟 6 子集内 6 条）、`dup_context_A=0`（6 子集内无逐字重复；全量重复由数据准备报告 §诊断登记）。

## 2. 新 commit（纳入跑分代码，避免 R1）

| 事件 | commit（短） | push |
|---|---|---|
| 入口实现 | `8aeb282` | ✅（远程同步） |
| 重试1修复（legacy→old 路径映射） | `c1a161a` | ✅（rebase 后 push，远程同步） |
| 重试2修复（补 import stack_caches/combine） | `03c9f50` | ✅（远程同步） |

## 3. 失败与重试记录（严格 3 次上限，日志留痕）

| 尝试 | 日志 | 根因分类 | 根因 | 可识别修复（纳入新 commit） | 结果 |
|---|---|---|---|---|---|
| 1 | `/tmp/opencode/audit_smoke_attempt1.log` | 实现 | `paths` 键为 train-old，cal_v=legacy，`KeyError: train-legacy`（legacy→old 映射缺失） | 加 `path_key()` 版本映射（legacy→old）——commit `c1a161a` | 失败 |
| 2 | `/tmp/opencode/audit_smoke_attempt2.log` | 实现 | `NameError: stack_caches not defined`（入口顶部漏 import） | 顶部补 `from readkv.evaluate.pipeline import combine, stack_caches`——commit `03c9f50` | 失败 |
| 3 | `/tmp/opencode/audit_smoke_attempt3.log` | — | — | — | **成功**（A00 冒烟产物生成，EXIT=0） |

- 未无改动重试；两次修复各对应一处可识别实现缺陷；均在 3 次上限内闭环。
- 补跑 A10（同一 legacy val、fixed train mapper）作“同一 val 两 mapper 一致性”对照，attempt 1 即成功（`/tmp/opencode/audit_smoke_A10_attempt1.log`）。

## 4. 冒烟门检查项与结果

| 检查项 | 结果 |
|---|---|
| 缓存恒等性（同文档两次 prefill K/V bit-identical） | ✅ A00/A10 均 True |
| Joint 输入审计（zero re-prefill） | ✅ A00/A10 均 True |
| 同一 val（legacy seed0）两 mapper 的样本指纹一致 | ✅ 8 臂 pair_id→sample_hash 全一致 |
| 同一 val 的控制臂一致（self/identity/control:zero 的 E_CF 逐对相同，不依赖 mapper） | ✅ |
| 样本指纹匹配源 JSONL（legacy val_seed0） | ✅ self 臂 pair→sample_hash 与源文件 EXACT |
| 各臂分数 + 指纹 + 告警 + 耗时落盘 | ✅ 每格 48 行 scores（6 对 × 8 臂） |
| provenance（git_hash/协议/数据哈希/seed/dtype/kernel/zero_re_prefill） | ✅ config 齐全，git_hash=03c9f50 |

**冒烟门结论：PASS（Go）**。可进入正式格（task 3–5），但仍需真实 PI 按 §1 每格 commit+push 的节奏逐格执行；本轮不启动任何正式格。

## 5. 资源与下一步

- 冒烟单格耗时：A00 94.5 s、A10 73.4 s（含模型加载），小规模 6 对；正式格 60 对预计约 150–440 s/格（方案 §3 归档 172–440 s），12 格串行约 35–90 min + 每格 commit/push 开销，预留 1–2 GPU 小时。
- 建议下一步：按 seed0 `A00→A11→A01→A10` 顺序启动正式格，每格完成即 commit+push（config/manifest/metrics/scores/ledger/日志摘要 + 索引），push 成功后再跑下一格；对角格 A00/A11 与历史逐对核对。
