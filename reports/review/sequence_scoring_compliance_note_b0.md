# 完整候选评分 · B0 干净基线重跑合规复核 note（protocol-v2.8）

> 审稿人：reviewer（readkv 独立质量守门人）。日期：2026-11-24。
> 本 note 复核上一份 `reports/review/sequence_scoring_compliance_note.md` 所列 R1–R4 的关闭情况，
> 对象为 B0 基线与 8 个 `_b0` run（`35e78e06917eb16461d6c925c8b0a435e99fd39c`，短 `35e78e0`）。
> 依据：`docs/decisions/sequence_scoring_baseline_ruling.md`（PI 裁决）、`configs/prereg/full_candidate_scoring_v2.8.yaml`。
> 性质：只读复核；未改代码/数据/判据/论文/任何运行产物；两份合规脚本输出重定向到
> `/tmp/opencode/audit_b0/`，未覆盖仓库内任何报告。

---

## 0. 复核判定

| 项 | 上一轮 | 本轮独立核验 |
| --- | --- | --- |
| **R1** git 锚点可重建 | 主要风险 | **CLOSED** |
| **R2** consistency_check 2.8 兼容 | 主要风险 | **CLOSED** |
| **R3** bootstrap dict E_CF | 主要风险 | **CLOSED** |
| **R4** scientist 三分支判读归类 | 未完成 | **仍 OPEN**（scientist 文档缺失；无事后择支证据） |
| 第二轮复审定向大修（编译/匿名稿/指标口径/归因措辞） | 阻塞 | **未由本实验解除**；writer 有未提交修订，未经本次独立复核签为关闭 |

> **P5 重审建议：CONDITIONAL GO（条件放行）。**
> 实验与合规层（R1–R3、门控、三读数、输入审计、旧 id 非权威）已就绪，可启动 P5 重审 evidence 审阅；
> 但**最终 P5 重新签 off / 投稿仍为 NO-GO**，直至：① R4 完成（scientist 按 v2.8 §7 冻结分支归类并出
> `docs/audit_seq_statistical_interpretation.md`）；② 第二轮复审定向大修项经**独立复核/编译验证**
> 关闭并由 PI 新出签 off（不改写旧 `p5_final_resignoff.md`）。v2.8 边界不变：不重算主终点、不恢复贡献、
> 不碰封存 test、不是方法贡献、不解除投稿阻塞。

---

## 1. R1 关闭证据（git 锚点可重建）

- `git rev-parse HEAD` = `35e78e0…39c`（B0 提交，2026-11-24 00:16:08Z），`git cat-file -t` 确认为 commit。
- **冻结后产出代码与判据未变**：`git diff 35e78e0 -- experiments/sequence_scoring_gpu.py
  src/readkv/models/gpu_backend.py scripts/consistency_check.py scripts/bootstrap_ci_report.py
  configs/prereg/` 与 `git diff HEAD -- <同上>` 均为空；本次执行前后产出代码+v2.8 无差异，
  无需 B1。
- 8 个 `_b0` run config 的 `git_hash` 全部为 `35e78e0`、`protocol_version=2.8`、
  `sealed_test_read=false`；权威集与非权威集区分见 §4。
- 我**实际运行** `python -m scripts.consistency_check`：6 个正式 `_b0` run 全部
  `ok=true`、`git_hash_in_history=true`、`traceable=true`、`run_code_unchanged_vs_head=true`、
  `protocol_compat.ok=true`、`protocol_compat.v28_fields.ok=true`、`problems=[]`，全局 `dirty_run_paths=[]`。
  → R1 所述「以未提交工作树跑分」缺口已由「先提交基线、后跑分」真正关闭（非放宽判据）。

## 2. R2 关闭证据（consistency_check 2.8 兼容）

- 提交代码中 `PROTOCOL_WHITELIST=("2.0","2.1","2.7","2.8")`（`scripts/consistency_check.py:215`），
  `_check_v28_fields()`（`:225`）并入 `protocol_compat.v28_fields`，校验 version_tag/对角格/seed/
  train-val SHA-256/zero_re_prefill/sealed_test_read/tokenizer 指纹/三读数声明。
- 实测输出（`/tmp/opencode/audit_b0/consistency_check_b0.json`）：
  `checked=55, failed=49, dirty_run_paths=[]`；6 个正式 `_b0` run 均 `ok=true`（见 §1）。
  49 个 failed 为既有历史 run 的已知问题，与 `_b0` 权威集无关。→ R2 CLOSED。

## 3. R3 关闭证据（bootstrap dict E_CF + 逐 reading CI）

- 提交代码中 `_sequence_readings()`/`_ecf_value()`（`scripts/bootstrap_ci_report.py:31/:45`）
  识别 dict 型 `E_CF`，不再 `float(dict)`；对每个 arm、每个 reading 分别算 template_family 主 CI
  与 pair-level 敏感性 CI，并记 `n_excluded_non_numeric_*`。
- 我**实际运行** `python -m scripts.bootstrap_ci_report`（默认 10000 resamples）：`runs=55`、
  无崩溃。6 个 `_b0` run 均 `sequence_scoring=true`、`sequence_readings=[first,full,length_normalized]`，
  逐 arm 逐 reading 产出：
  - 例 `audit_seq_A11_s0_b0` joint：`first` E_CF 6.900 [3.564,10.100]、pair 敏感性 [5.496,8.321]；
    `full` 15.952 [8.874,22.176]、pair 敏感性 [13.202,18.695]；
    `length_normalized` 8.019 [4.504,11.094]、pair 敏感性 [6.646,9.384]；
    `cluster_unit=template_family`、`n_clusters=8`、`exploratory=true`、**排除数 0**。
  - 顶层 note 明示 `no cross-reading E_CF comparison`，未跨口径比绝对尺度。
  → R3 CLOSED（统计独立复算交叉验证已恢复）。

## 4. R4 状态（仍 OPEN）

- `docs/audit_seq_statistical_interpretation.md` **仍不存在**；全仓检索
  `consistent_across_scoring / first_token_sensitive / length_norm_changes_reading` 仅命中我上一份 note
  （引用冻结分支名），**无任何产物做三分支归类**。
- `reports/review/sequence_scoring_summary_b0.md` 提供逐 seed 主表、`reading_diff` CI、`cell_diff`
  与完整性表，但 §3 自注「判读由 scientist 按 v2.8 §7 完成」，属事实汇总而非判读。
- **正面**：尚无产物归类分支或写强度结论，故**无事后择支证据**；分支条件已在 v2.8 §7 结果前冻结，
  scientist 按该规则补归类仍合规，但须在文档注明「按结果前冻结条件对号入座」，不得跨口径比较 E_CF、
  不作单项因果归因、不恢复贡献。R4 为裁决 §6 明列的新签 off 前置，未闭则不得最终签 off。

---

## 5. 实验层逐项复核（_b0 八格）

- **门控**：两 `_b0` 冒烟 `created_at` 00:18/00:19Z 早于六正式格 00:20–00:24Z；冒烟 `status=
  SMOKE_GATE_PASSED_NON_AUTHORITATIVE`，六格 `status=OK`、无 ABORTED；两冒烟 `smoke_checks`
  全通过（首 token 回放 A11 4.768e-07 / A00 2.384e-07，单 token full=first 空检如实 n=0，
  逐次审计 76/76、zero re-prefill 全 true、缓存 76 互异、Self/Identity max diff=0、A/B 交换 max diff=0、
  未读封存 test）。总 wall 655s（run report §8，与入口内 elapsed 合计 ~616s + 进程开销一致）。
- **三读数同样本 / 输入审计**：六格各 120 行 scores 三读数齐全（缺失 0）、每格 self/joint 各 60；
  单 token 候选 A11 28 / A00 112，max|full−first|=0；每格 480 条 forward audit 全部
  `audit_passed`/`zero_re_prefill`=480/480、输入序列 `[Q,1×(m−1)]`、位置偏移正确、4 分支
  `branch_cache_id` 120/120 互异、`audit_failures`/`failure`=0；manifest 四文件哈希/大小全匹配。
- **旧 id 非权威**：`reports/runs_index.json` 中 9 个旧 id（6 正式 + 3 冒烟 v2/失败）
  全部 `superseded=true, authoritative=false`，reason 为「pre-baseline：git_hash=a05e9b3 早于判据与代码，
  无法从该 hash 重建；已由 `_b0` 干净基线重跑取代」（对应基线裁决 §4.2），文件保留未删未改；
  6 个 `_b0` 正式格 `authoritative=true, superseded=false`。
- **未读封存 test / 未做 A01/A10 / 未改判据**：8 个 `_b0` config `sealed_test_read=false`；
  无 `audit_seq_A01/A10*` 目录；`git diff 35e78e0 -- configs/prereg/` 为空。

## 6. 第二轮复审定向大修 —— 未由本实验解除（明确记录）

`reports/review/independent_research_and_manuscript_review_2026-11-24.md` 列出的投稿阻塞
（长稿第 753 行 `\texttt{mixed_interaction}` 下划线致命错误与 ~103 pt 溢出、arXiv 第 792 行裸 `E_CF`
与 ~386 pt 溢出、匿名 TMLR 稿缺失、flip 分母/首 token 代理符号/KD「preserves utility」口径、
2×2 表注第 722–723 行标签写反、归因措辞强度）为**独立大修项**。本次在 `git status` 观察到 writer
对工作树的未提交修订（`papers/readkv_v2_draft/main.tex`、`cover_letter.md` 的 M，及新增
`papers/readkv_v2_tmlr_anonymous/`），仲裁与复核尚在进行：本机无 tectonic，`main.tex` 中
`mixed_interaction` 致命行与 arXiv `$E_{\mathrm{CF}}$` 的改动**未经本次独立编译/内容复核**，
我不将其签为关闭。按 v2.8 §8 `does_not_unblock_submission` 与裁决 §4：**本实验不解除、不推迟、
不替代这些大修；即使 R1–R3 全闭也不构成「可立即提交」许可。**

---

## 7. 风险清单（残余）与放行条件

- **阻塞（最终签 off 前须闭）**：
  1. R4：scientist 出 `docs/audit_seq_statistical_interpretation.md`，按 v2.8 §7 冻结分支对号入座，
     明示 8 族 exploratory、E_CF 不跨口径、无单项因果、贡献状态不变。
  2. 定向大修：编译验证两版、匿名稿达标、指标口径与归因措辞关闭，并有独立复核记录；由 PI **新出**
     重新签 off（不改写 `p5_final_resignoff.md`）。
- **次要（如实记录，不阻塞）**：作者身份/tokenizer 快照仍以路径+指纹记录（`snapshots/master` 可变别名），
  数值复现范围由首 token 回放确认（≤4.77e-07）；显存峰值未采集不编造。
- **已关闭**：R1 / R2 / R3（§1–§3）。

> **CONDITIONAL GO 的含义**：可启动 P5 重审对 `_b0` 权威集的 evidence 审阅；最终重新签 off/投稿
> 在 §7 两项阻塞关闭前维持 NO-GO。交叉核验（哈希、回放、审计、CI、index 权威位）均为脚本对实际字节
> 计算所得，无 mock 数字。

## 8. 证据路径

- 基线/判据：`docs/decisions/sequence_scoring_baseline_ruling.md`、`configs/prereg/full_candidate_scoring_v2.8.yaml`、
  `docs/decisions/full_candidate_scoring_ruling.md`；B0 = `35e78e0…39c`（HEAD，`git diff` 产出代码为空）
- 权威产物：`reports/runs/audit_seq_{A11,A00}_s{0,1,2}_b0/`、`reports/_non_authoritative/audit_seq_smoke_{A11,A00}_s0_b0/`
- 汇总/脚本修复：`reports/review/sequence_scoring_summary_b0.md`、`reports/review/sequence_scoring_script_fix_note.md`、
  `reports/review/sequence_scoring_run_report.md` §8
- 合规脚本实测：`/tmp/opencode/audit_b0/consistency_check_b0.json`（6 正式 `_b0` ok=true）、
  `/tmp/opencode/audit_b0/bootstrap_ci_b0.json`（55 runs，逐 reading 主 CI+pair 敏感性，排除 0）
- 权威位：`reports/runs_index.json`（9 旧 id superseded/非权威，6 `_b0` 权威）
- 投稿阻塞：`reports/review/independent_research_and_manuscript_review_2026-11-24.md`

> 边界：本 note 未改任何代码、数据、判据、论文或运行产物；合规脚本输出仅在 `/tmp/opencode/audit_b0/`。
