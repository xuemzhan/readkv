# 完整候选评分（protocol-v2.8）稳健性实验 · 合规审计 note

> 审稿人：reviewer（readkv 独立质量守门人）。日期：2026-11-24。
> 审计对象：8 个 v2.8 新 run（`reports/runs/audit_seq_{A11,A00}_s{0,1,2}/` 六格 +
> `reports/_non_authoritative/audit_seq_smoke_{A11,A00}_s0_v2/` 两冒烟）与原失败产物
> `reports/_non_authoritative/audit_seq_smoke_A11_s0/`。
> 冻结判据：`configs/prereg/full_candidate_scoring_v2.8.yaml`（protocol-v2.8）。
> 审计性质：只读合规审计；未改代码/数据/判据/论文/任何运行产物。
> 本 note 为 v2.8 §8 `review` 与 `reviewer_checks` 的交付，触发 P5 重审；**不代替 PI 签 off**。

---

## 0. 总结与放行判定

| 维度 | 判定 |
| --- | --- |
| 六格技术执行（门控/入口/三读数/审计/哈希） | **PASS**（逐项核验见 §2–§4） |
| 统计口径（簇级 CI/样本加权/exploratory/分母） | **PASS（产物内）/ 未完成（跨格汇总与 pair 敏感性）** |
| 判读三分支归类（v2.8 §7） | **未完成**（scientist 文档缺失，无事后择支证据） |
| 冻结可追溯性 / 合规脚本可复验性 | **主要风险**（见 §5 R1–R3） |
| 第二轮复审定向大修阻塞解除 | **未解除**（见 §6） |

> **P5 重审放行建议：NO-GO。**
> 理由：v2.8 §4 与裁决 `docs/decisions/full_candidate_scoring_ruling.md §4` 明列的重签 off
> 前置条件中，③「第二轮复审定向大修项全部关闭并复核」与 ④「论文按三分支更新、编译与匿名稿达标」
> 均未满足；且本次产物自身缺 §7 判读归类、跨格统计汇总与可复验的 git 冻结锚点。
> 本实验按 v2.8 `invariants` 仅为读数稳健性补充，**不重算主终点、不恢复贡献、不接触封存 test、
> 不是方法贡献，也不解除当前投稿阻塞**。六格 GPU 执行可「有条件接受」为有效测量产物，
> 但须先关闭 R1–R4；P5 须在 R1–R4 与投稿大修项均关闭后**重新签 off**。

---

## 1. 审计方法（实际执行，非 mock）

- 逐文件读取 8 个 run 的 `config.json`/`metrics.json`/`manifest.json`，并流式核验
  `scores.jsonl`/`forward_audit.jsonl`（六格各 120/480 行，两冒烟各 18/76 行）。
- 以脚本对全部产物重算：manifest 四文件 SHA-256 与大小、三读数完整性、单 token `full==first`、
  输入长度序列 `[Q,1×(m−1)]`、位置起点/增量、zero re-prefill、候选分支互异、ABORTED/失败标记。
- 对 12 个 train/val 文件复算 SHA-256，与 6 个 config 声明值逐字比对。
- 首 token 回放：把冒烟新 `D(first)` 与归档 2×2 的 `D_self`(self arm)/`D_trans`(joint arm)
  按 `(sample_id, arm)` 逐对数值比对。
- 依 reviewer 硬约束实际运行 `python -m scripts.bootstrap_ci_report` 与
  `python -m scripts.consistency_check`（输出重定向到 `/tmp/opencode/audit/`，不覆盖仓库报告）。

---

## 2. 先冻后跑 / 门控纪律 / 入口审计

### 2.1 冻结先于 run —— 时间顺序成立，但 git 锚点缺失（见 R1）

- v2.8 配置 mtime `2026-11-23 23:28:40Z`；裁决 `.../full_candidate_scoring_ruling.md`
  `23:29:04Z`；数据审计 `23:32:54Z`；新增评分代码 `gpu_backend.py 23:37:29Z`、
  `sequence_scoring_gpu.py 23:45:55Z`；首个（失败）冒烟 `created_at 23:44:35Z`，
  两 v2 冒烟 `23:48/23:49Z`，六格 `23:50–23:58Z`。
  **判据与代码均早于任何 `audit_seq_*` run**，满足「先写后跑」的字面要求。
- 但 `git log` 中 `a05e9b3`（2026-11-23 23:24:57Z）为最新提交，v2.8 配置、裁决、新入口、
  六个正式 run 目录、两冒烟目录**全部为 untracked**，且 `src/readkv/models/gpu_backend.py`
  为已修改未提交（`M`）。**git 历史中不存在 v2.8**，记录的 `git_hash=a05e9b3` 早于冻结与代码，
  无法从该 commit 重建本次产物 → 见 R1。

### 2.2 门控纪律 —— PASS

- 两 v2 冒烟 `status=SMOKE_GATE_PASSED_NON_AUTHORITATIVE` 且
  `smoke_checks` 全项通过；六格无 `ABORTED`/`FAILED`（`grep` 六格 metrics 均为 0）；
  失败冒烟 `status=SMOKE_GATE_FAILED`（唯一失败项 `first_token_replay`）产物五类齐全、
  mtime `23:44` 早于 v2 冒烟且未被覆盖 → 门控「冒烟先于六格、失败中止」成立。
- 未跑 A01/A10：无 `reports/runs/audit_seq_A01*`/`A10*` 目录；入口 `cell` 仅允许 A00/A11
  （实现说明 §2.1）。
- 未读封存 test：8 个 run config `sealed_test_read=false`；`data/` 下无 test 文件；
  数据审计报告 §1 明示只打开 12 个 train/val 文件。
- 未改冻结判据/数据：`git diff HEAD -- configs/prereg/` 为空；train/val 文件 mtime `16:04`
  （冻结前）；`reports/runs/audit_2x2_*` 旧归档未改（git status 无相关条目）。

### 2.3 入口与 teacher-forcing —— PASS

- `experiments/sequence_scoring_gpu.py` 未 import `P1_gpu`/`run_cf_pipeline`（仅文首声明不复用），
  只读 JSONL；与独立评分模式 `readkv.models.gpu_backend.score_candidate_sequence` 对接。
- `gpu_backend.py` diff 为 **392 行纯新增、0 删除**，新增 `score_candidate_sequence` 与
  `log_softmax_fp32`/`audit_sequence_forwards` 等；贪解码 `inject_and_generate` 语义未改 →
  teacher-forcing 评分与贪解码路径分离成立。
- 首 token 口径：冒烟 `D(first)` 对归档 `D_self`(self)/`D_trans`(joint) 逐对比对，
  A11 max diff **4.77e-07**、A00 **2.384e-07**（tol 0.02，12/12 对），原失败冒烟同口径
  max diff **16.20** 故失败 → 口径 `self→D_self、joint→D_trans` 正确且失败得到解释。
- 样本身份以 `version_tag|sample_hash` 标识；跨六格 359 个唯一 `sample_hash`，
  **出现在 >1 个 cell 的哈希 = 0**；同 pair_id 的 A00_s0 与 A11_s0 120 组 `scores` 全不同 →
  缓存/分数哈希无交叉。

### 2.4 逐次输入审计 —— PASS

六格各 480 条 `forward_audit.jsonl`，逐条核验：`audit_passed=480/480`、
`zero_re_prefill=480/480`、`input_length_sequence==[Q,1×(m−1)]` 480/480、
位置起点=offset 且后续每次 +1 480/480、每 (pair,arm) 4 个候选分支 `branch_cache_id` 互异
120/120、`audit_failures`/`failure` 均空。两 v2 冒烟 76/76 同结论（含 swap 的 joint 为 8/8 互异）。
`metrics.n_audit_forwards=480`、A11 每格文档总 forward 932、A00 848，与记录一致。

> 抽检范围如实：审计覆盖全部 val 前向（六格全量逐次），非仅首对抽检；顶层
> `zero_re_prefill=true` 与逐次一致。符合 v2.8 §5 `evidence_scope`。

---

## 3. 三读数与产物契约 —— PASS

- 六格每格 120 行 scores 全部含 `first/full/length_normalized`，双侧两候选齐全
  （完整性缺失计数 0）；三读数使用同一批 60 对、同一 arm，无混算。
- 单 token `full==first` 非空核验：A11 每格 28 个、A00 每格 112 个单 token 候选，
  max |full−first| = **0**（严格相等），三 seed 一致；冒烟 6 对候选均 2 token，
  `single_token_consistency.n=0` 如实标注为空检（不伪造）。
- 五类产物齐全；四文件（config/scores/forward_audit/metrics）SHA-256 与 size 对 manifest
  逐项吻合（9 个 run 全部 `hash_mismatch=[]`）；config 与 manifest 字段齐全：
  `protocol_version=2.8`、`git_hash`、`version_tag`、`seed`、train/val SHA-256（与实测逐字一致）、
  `dtype=bfloat16`、`kernel=sdpa`、`zero_re_prefill=true`、`teacher/student` 路径、
  tokenizer 指纹 `5b99b566…`（失败冒烟为 `unavailable:TypeError`，v2 与正式格为可用值）、
  `sealed_test_read=false`、`criteria_source` 指向 v2.8。
- 同分规则 `_pred_from_g: g>0→A，g≤0→B`；token 边界不一致 A=0/B=0（与数据审计 §4 一致），
  未触发 v2.8 §4 `sensitivity` 分隔符复算，如实。

---

## 4. 统计口径 —— 产物内 PASS / 跨格汇总未完成

- 主 CI：`reading_diff_L_full_minus_L_first` 用 `readkv.stats.bootstrap.cluster_bootstrap`
  以 `template_family` 为簇、10000 resamples；每次重采样「抽中族样本拼接后取均值」
  = **抽中样本之和 / 抽中样本数**，点估计 = 全样本均值，与 v2.8 §6 `statistic` 一致 ✓。
- 每格 `n_template_families=8`、`exploratory=true`（<24），逐 seed 保留族计数 ✓；
  主分析分母由数据审计独立核对为 **A00 42/42/41、A11 46/46/46**、每格 6 族 ✓
  （L 按 60 对口径「对齐旧表」，沿用 2×2 约定，非主分析 42/46 分母，两者未混写 ✓）。
- `L_self_minus_joint` 三读数并列（如 A11_s0 0.383/0.433/0.450）✓；
  E_CF 各读数内计算，run report §6 明示不跨口径比绝对尺度 ✓；coverage、方向一致率附分母 ✓。
- **缺口**：config §6 要求 `pair_level_sensitivity: "required"` 与三项比较
  （`reading_diff`/`cell_diff`/`reading_of_diff`）。六格 `metrics.json` 仅含格内
  `reading_diff` 的簇级 CI，**无 pair-level 敏感性区间、无 A11−A00 跨版本差、
  无 `reading_of_diff`**；`refine-logs/GPU_SEQUENCE_SCORING_TRACKER.md` 记载
  `audit_seq_summary`（CPU 复算/主表/敏感性表）**未运行** → 见 R4。

---

## 5. 合规脚本与可复验性（reviewer 硬约束实际运行结果）

| 脚本 | 结果 | 证据 |
| --- | --- | --- |
| `python -m scripts.bootstrap_ci_report` | **崩溃**：`TypeError: float() argument ... not 'dict'`（`scripts/bootstrap_ci_report.py:92`，把 `E_CF` 当标量） | 新 run 的 `E_CF` 为 `{first,full,length_normalized}` 字典；标准脚本无法对 v2.8 产物重算 CI。崩溃发生在写盘前，未覆盖 `reports/bootstrap_summary.json`（mtime 仍 13:45） |
| `python -m scripts.consistency_check` | 49/49 `ok=false`；全局新增问题串 `run code paths have uncommitted changes: M src/readkv/models/gpu_backend.py`；六格另报 `protocol_version '2.8' incompatible with frozen V2 prereg` | 输出 `/tmp/opencode/audit/consistency_report.json`；六格 `git_hash=a05e9b3 in_history=true traceable=true`，`model_pair_check.ok=true`（推断 1.7B→0.6B 等深） |

- **R1（主要）**：v2.8 与本次全部新增代码/产物为 untracked，`git_hash=a05e9b3` 早于冻结与实现，
  无法从该 hash 复现本次 run；`consistency_check` 因未提交改动把全部 run 判为失败。
  治理要求「可追溯」在 git 层面未闭合。冻结顺序仅有文件系统 mtime 与裁决/清单文本佐证。
  处置：PI 批准后将 v2.8 配置、裁决、入口/后端改动与新产物**纳入同一冻结基线提交**，
  并让 run config 的 `git_hash` 指向含判据与代码的可重建 commit；或在合规脚本中显式登记
  v2.8 冻结点并以「配置哈希 + 代码哈希」替代早于冻结的 git_hash。
- **R2（主要）**：`consistency_check` 只接受 `protocol_version ∈ {2.0,2.1}`
  （`_check_protocol_compat`），v2.8 新格被判不兼容。须扩展脚本版本白名单/新增版本登记后重跑，
  以只读方式确认 git hash、zero-re-prefill、缓存/分数哈希无交叉。
- **R3（主要）**：`bootstrap_ci_report` 不兼容 v2.8 的字典型 `E_CF`，统计复算无法由标准脚本完成。
  须扩展脚本（按读数拆分 E_CF）并重跑；在修复前，§4 的 CI 仅由入口内 `summarize()` 单点产生，
  缺独立复算交叉验证。
- **R4（主要）**：scientist 的 `docs/audit_seq_statistical_interpretation.md` **不存在**，
  `audit_seq_summary` 未运行；v2.8 §7 三分支（consistent_across_scoring / first_token_sensitive /
  length_norm_changes_reading）**尚未按预承诺规则归类**，pair 敏感性与跨版本比较未产出。
  **正面结论**：目前无产物做任何分支归类或强度措辞，故**无事后择支证据**；分支条件已由
  v2.8 §7 在结果前冻结，scientist 按该规则补归类仍合规，但须在文档注明「按结果前冻结条件对号入座」。
- **R5（次要）**：模型身份仅记录路径 + tokenizer 指纹，未哈希多 GB 权重、`snapshots/master`
  为可变别名；v2.8 §4 允许以首 token 逐对回放确认数值复现（本次 diff ≤4.8e-07）并明示身份范围，
  实现说明 §6.1 已如实披露 → 可接受，但解读应限于「可核验身份 = 首 token 回放确认的数值复现」。

---

## 6. 与第二轮复审的关系（P5 放行前置）

`reports/review/independent_research_and_manuscript_review_2026-11-24.md` 明确：当前投稿因
编译致命错误（长稿第 753 行 `\texttt{mixed_interaction}` 下划线，另有 ~103 pt 溢出；
arXiv 第 792 行裸 `E_CF`、~386 pt 溢出）、匿名 TMLR 稿缺失、2×2 表注第 722–723 行
A01/A10 验证集写反、flip 分母/首 token 代理符号/KD「preserves utility」口径与归因措辞等
**定向大修阻塞**而建议暂缓提交。git log 中 HEAD 之后无任何 writer/编译/匿名稿修复提交，
`papers/` 无改动 → 这些阻塞**仍独立待关闭**。

本实验按裁决 §3/§4 与 v2.8 §8 `does_not_unblock_submission`：**不解除、不推迟、不替代**上述大修；
即使六格全部 PASS，也不构成「可立即提交」许可。P5 重新签 off 的前置（裁决 §4）目前仅
①（8 run 按门控完成）与②（本 note）就绪，③④未就绪，故本轮 **NO-GO**。

---

## 7. 修改清单（按责任角色，供 PI 裁决）

**阻塞（须先关闭）**
1. writer/PI：关闭第二轮复审全部定向大修项（编译两版、生成匿名 PDF 附录、修正 2×2 表注与
   指标/归因措辞、cover letter 同步），并有独立复核记录 → 否则 P5 不得重签。
2. scientist：产出 `docs/audit_seq_statistical_interpretation.md` 与 `audit_seq_summary`，
   按 v2.8 §7 冻结分支对号入座，补 pair-level 敏感性与 `cell_diff`/`reading_of_diff`，
   明示 8 族 exploratory、E_CF 不跨口径比较、无单项因果归因、贡献状态不变。

**主要（须关闭后才可把六格作为可复验证据）**

3. engineer/PI：把 v2.8 配置、裁决、入口与 `gpu_backend.py` 改动、8 个 run 产物纳入冻结基线提交，
   使 `git_hash` 指向含判据与代码的可重建 commit；或登记配置/代码哈希锚点。
4. engineer：扩展 `scripts/consistency_check.py` 版本白名单以识别 v2.8，重跑并归档只读报告。
5. engineer：扩展 `scripts/bootstrap_ci_report.py` 支持字典型 E_CF，重跑并归档独立 CI 复算。

**次要**

6. engineer/doc-engineer：在复现文档披露模型快照身份范围（首 token 回放确认），
   明示显存峰值未采集（不编造），并逐 seed 保留族计数与主分析分母对照。

---

## 8. 证据路径索引

- 判据/裁决/方案：`configs/prereg/full_candidate_scoring_v2.8.yaml`、
  `docs/decisions/full_candidate_scoring_ruling.md`、`refine-logs/GPU_SEQUENCE_SCORING_PLAN.md`、
  `refine-logs/GPU_SEQUENCE_SCORING_TRACKER.md`
- run 产物：`reports/runs/audit_seq_{A11,A00}_s{0,1,2}/{config,scores.jsonl,forward_audit.jsonl,metrics,manifest}`、
  `reports/_non_authoritative/audit_seq_smoke_{A11,A00}_s0_v2/`、原失败 `.../audit_seq_smoke_A11_s0/`
- 数据/实现/运行记录：`reports/data/sequence_scoring_data_audit.md`、
  `reports/review/sequence_scoring_implementation_note.md`、`reports/review/sequence_scoring_run_report.md`
- 归档回放锚点：`reports/runs/audit_2x2_A11_s0/scores.jsonl`（`D_self`/`D_trans`）
- 合规脚本与结果：`scripts/bootstrap_ci_report.py`（崩溃）、`scripts/consistency_check.py`、
  `/tmp/opencode/audit/consistency_report.json`（49/49 ok=false；六格协议版本不兼容）
- 投稿阻塞：`reports/review/independent_research_and_manuscript_review_2026-11-24.md`

> 审计边界重申：本 note 未改任何代码、数据、判据、论文或运行产物；合规脚本输出重定向至
> `/tmp/opencode/audit/`，未覆盖 `reports/consistency_report.json` 或 `reports/bootstrap_summary.json`。
> 交叉核验结果（哈希、回放、审计、口径）均为脚本对实际字节计算所得，无 mock 数字。
