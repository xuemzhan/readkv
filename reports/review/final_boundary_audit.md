# 最终边界研究 · 收尾合规审计（S1–S5 / 统计一致性 / 引用 / AI 数据裁定）

- 角色：审稿人（对抗性审阅 / 统计合规守门），独立质量守门，不改代码/数据/判据/论文/运行产物。
- 日期：2026-11-23。
- 审计对象：`docs/decisions/final_boundary_study_signoff.md` §2 S1–S5、§5；`docs/decisions/p5_final_signoff.md`；`reports/review/meta_review/current_task_meta_review.md`；`reports/review/research_advisor/third_round_online_addendum.md`。
- HEAD 快照：审计开始时 `b7b9f50`；审计进行中被并行提交推进到 `0fa65cc → 4613200`。**本审计以收尾时的 `4613200` 为准**，并显式记录期间发生的两项状态翻转（见 §0.2）。
- 方法：全部只读。统计/一致性脚本以 `--output /tmp/opencode/audit_*.json` 运行，未写回任何 `reports/**` 运行产物；磁盘只读复算用仓库 `.venv`。冻结判据 `sha256sum`、git log/diff 只读核验。`configs/prereg/**`、`reports/runs/**/scores.jsonl`、论文正文均未改。

---

## 0. 结论摘要

### 0.1 P5 决议

> **CONDITIONAL GO（放行至 ready-to-submit，附 3 项投递前收尾门槛）——不给出无条件 GO。**

- S1–S5 全部 **PASS**；kd_clean 簇级 CI 缺口、N1–N9 引用缺口在本审计开始时仍未闭环，但**审计期间已被并行提交修复**（§0.2），当前状态均为 **PASS**。
- 研究结论（情形 C / 失败边界 / 数据泄漏教训；贡献(1)(2) 撤回、贡献(3) withheld；P2/P3/P4 永久取消）在证据上稳定，未被本次审计推翻：簇级 CI 下界全部 >0，方向与 C 判读一致。
- 但提交稿 `main.tex` 仍存在 **1 项主要统计口径风险（阻塞正式投递）** 与 2 项次要收尾项（§6）。在它们关闭前，我**不建议真实 PI 直接向 TMLR 提交**；方向裁决与 PI 的 conditional signoff 不受影响。

### 0.2 审计期间发生的状态翻转（重要，避免读者据旧产物误判）

| 项 | 审计开始时 | 收尾时（HEAD 4613200） | 证据 |
|---|---|---|---|
| kd_clean 三 seed 的 v2.3 `template_family` CI 进 `bootstrap_summary.json` | **缺失**（26 runs，无 kd_clean） | **已补入**（31 runs，含 3 seed 主 CI + pair-level 敏感性） | 提交 `d0f54de` 重写 `reports/bootstrap_summary.json`；本次只读复算复核（§2） |
| N1–N9 最新文献进论文 | **缺失**（bib 仅 kvlingo/cachelink） | **已全部引用**（bib n1–n9b + 正文 §Related Work） | 提交 `d0f54de` 重写 `main.tex`；grep 核验（§4） |
| SQuAD 锚点数值进论文 | 未补 | **已补入**（`tab:anchor` + §External anchor） | `main.tex:621–655` |

> 元审查 `current_task_meta_review.md` §3.1/§3.2 与 addendum 的引用缺口，是针对旧快照的正确告警；在本审计收尾快照中已由工程/写作侧闭环。审稿侧以**收尾快照**为准。

---

## 1. S1–S5 逐项核验

| 项 | 判定 | 证据与理由 |
|---|---|---|
| **S1** clean run 数据哈希绑定 | **PASS** | `reports/data_hash_binding_erratum.json` 以 metadata 勘误把 sha `f910f1f1…a894a` 绑定至 7 个 clean run（E0×1 + P1 affine×3 + kd×3），逐 run 记 commit（efc3ba3 / 6413ba0）。磁盘实测 `sha256sum data/tasks/cf_pairs.jsonl = f910f1f1…a894a`（与 manifest 一致）；勘误文件为 tracked，声明 `scores/config/prereg/data` 均未改。符合 signoff §2 S1“不回改冻结产物”。 |
| **S2** v2.3 sha 回填前后注记 | **PASS** | `data/tasks/manifest.json:12–19` 与 `reports/data/acceptance_checks.json:27–30` 同时记录当前 `e44c6acb…` 与回填前 `5200940c…`，并注明 commit `6413ba0`。磁盘 `sha256sum configs/prereg/stats_convention_v2.3.yaml = e44c6acb…`；`recomputed_value=398` 已在 yaml 中。git log 显示 v2.3 最后提交为 `6413ba0`（首次且唯一提交），未篡改。另有 `reports/data/s2_hash_annotation.md` 完整版本过程说明。 |
| **S3** runs_index / consistency 状态 | **PASS（附次要注记 R4/R5）** | `reports/runs_index.json` 共 **28** 项（19 旧 run `superseded=true`；9 权威 = 7 clean + 2 SQuAD 锚点），全部带 `data_sha256`。7 个 clean run 在 `runs_index` 均 `superseded=false`、`consistency` 均 `ok=true/traceable=true`（对当前 HEAD `4613200` 复跑确认）。锚点 run 亦 `ok=true`。注：signoff §2 S3 与 `p5_final_signoff` 第 16 行仍写“26 run”，为加入 2 锚点前的旧计数（现 28）——文档计数陈旧，非科学问题（R5）。 |
| **S4** 措辞“接近但未超过控制” | **PASS** | `main.tex:62–64`（摘要）“approaches but does **not** exceed the mismatched ($8.38$) and zero-cache ($8.58$) controls”；`:525–526`（§mvp）、`:663–665`（§Adverse）、`:698–699`（结论）一致；info attribution 以“mixed（2 正 1 负）”如实报告（`:528–529`）。无“与控制相当/达到无信息水平”表述。 |
| **S5** 单信号 + exploratory 强度边界 | **PASS** | `main.tex:666–670` 明确 `transfer_broken` 由**单信号**（Joint dual drop ≥0.2）触发；`:671–676` 披露 8 族 <24、单合成等深对、val-only、封存 test 未评测、无跨对/跨模型/真实世界/因果/强显著主张；`:606–613` 分离冻结 verdict `distortion_exists` 与 `transfer_broken`；结论 `:719–726` 复述。符合 signoff §2 S5。 |

---

## 2. kd_clean 三 seed 的 v2.3 簇级 CI（原缺口 → 现已闭环）

- 只读检查：`reports/bootstrap_summary.json` 当前 **31 runs**，含 `runs/p1_kd_clean_mvp_seed{0,1,2}`。每条 `arms.joint` 给出 `cluster_unit=template_family`、`n_clusters=8`、`exploratory=true`，并同时给出 `E_CF_pair_level_sensitivity`。
- 我用仓库脚本的纯函数 `summarize_run`（未写文件）按各 run config 的 `bootstrap_seed`（0/1/2）独立只读复算，与汇总一致：

| run | 主 CI（template_family，汇总/复算一致） | pair-level 敏感性 | n_clusters / exploratory |
|---|---|---|---|
| p1_kd_clean_mvp_seed0 | `6.388 [3.653, 8.814]` | `6.388 [5.340, 7.400]` | 8 / true |
| p1_kd_clean_mvp_seed1 | `6.479 [3.899, 8.798]` | `6.479 [5.431, 7.529]` | 8 / true |
| p1_kd_clean_mvp_seed2 | `7.210 [4.417, 9.799]` | `7.210 [6.074, 8.331]` | 8 / true |

- 判定：**缺口已闭环（PASS）**。三 seed 主 CI 下界均 >0，**支持而推翻不了 PI 的情形 C 判读**；数值与元审查 §3.1 复算的差异仅在 bootstrap seed 取值（元审查用 seed=0 复跑三行；此处按 config 真实 seed 0/1/2），方向一致。
- **但我未改动任何汇总**（不自行补入）：缺失已由工程侧提交 `d0f54de` 修复。若工程侧需要“我曾补入”的留痕，本审计记录为证。

---

## 3. 统计 / 一致性脚本只读审计（不修改运行产物）

- `consistency_check`（`--output /tmp/opencode/audit_consistency2.json`）：`checked=31, failed=22, head_hash=4613200, dirty_run_paths=[]`。22 项 failed 全为**历史 pre-clean / superseded run**因 HEAD 前进而触发 `run code differs vs HEAD`，不影响权威结果；7 个 clean run 与 2 锚点全部 `ok=true / traceable=true / run_code_unchanged_vs_head=true`。**无 zero-re-prefill、git hash、缓存/分数哈希交叉污染迹象**。
- `bootstrap_ci_report`（`--output /tmp/opencode/audit_bootstrap.json`）：`runs=31`，与当前 `reports/bootstrap_summary.json` **逐字节一致**（`diff -q` 通过）。锚点 run 的 `arms={}`、`protocol=v1.0`、`stats_convention=n/a`，确认**锚点未混入合成 E_CF 主终点、未重算冻结 CI**，符合 v2.4 与锚点审计 `anchor_eval_review.md`。
- clean affine 与 kd 的主 CI、flip 分母（398）、τ=1.0 在汇总/manifest/acceptance/论文间一致；锚点（SQuAD `80a5225e…82d8`）在 runs_index / consistency / `anchor_eval_summary.json` / 论文 `tab:anchor` 间数值一致（affine Joint F1 0.0051、kd 0.0014、Self 0.1975，判 `exploratory_disclosure`）。
- 判据完整性：`configs/prereg/` 冻结文件（v2.3–v2.5）未回写；v2.6 为新增文件（最终裁定判 not-activated，§5）。无按测试结果调 τ / Huber δ / 标签平衡迹象（δ 复核按 PI 决定永久取消）。

---

## 4. 最新文献引用核验（N1–N9）

> 原任务要求给“引用缺口清单”。当前快照下 gap 已基本关闭，仅余**全文口径核验**与 **SQuAD 引用**两项（详见 §6 R2/R3）。

| 编号 | addendum 文献 | 论文 bibitem | 正文引用 | 缺口 |
|---|---|---|---|---|
| N1 | DeepSeek-V4-Flash / Functional Cache Divergence (2611.14051) | `\bibitem{n1}` ✓ | `:179` ✓ | 作者名未填；仅摘要级核验 |
| N2 | Close Enough is Nowhere Near (2610.22016) | `n2` ✓ | `:180–181` ✓ | 同上 |
| N3 | Safety Incompatibility / value-reuse bias (2610.15721) | `n3` ✓ | `:182–184` ✓ | 同上 |
| N4 | ACCT (2610.42116) | `n4` ✓ | `:184–185` ✓ | 同上 |
| N5 | Swarm Telepathy (2610.15095) | `n5` ✓ | `:185–186` ✓ | 同上 |
| N6 | RaReCache (2610.11358) | `n6` ✓ | `:186–187` ✓ | 同上 |
| N7 | Latent Communication causal audit (2608.04893) | `n7` ✓ | `:189–191` ✓ | 同上 |
| N8 | CacheFuse (2610.16165) | `n8` ✓ | `:187–188` ✓ | 同上 |
| N9 | Hybrid-attention translation (2611.12062) / BridgeKV (2611.11761) | `n9a` ✓ / `n9b` ✓ | `:188–189` ✓ | 同上 |
| N10 | KV-Lingo / CacheLink / Heo | `kvlingo`,`cachelink`,`heo2026` ✓ | `:164–169` ✓ | 已填作者/arXiv/doi，核验较充分 |

- **引用缺口清单（残余）**：
  1. **全文口径核验未完成**：addendum 头部与 meta-review §3.5 明示 N1–N9 仅核验标题/作者/摘要/日期，未逐篇读全文；`notes.md:134,141,151` 亦标“N1–N9 全文口径待核验、bibitem 以标题+arXiv+年份占位（未填作者名，避免编造）”。当前 bibitem `n1`–`n9b` 确无作者名。协议 §9 要求投递前全文口径核验（`p5_final_signoff` §5.3 亦提示）。
  2. **SQuAD 引用缺失**：`p5_final_signoff` §4.1.5 要求补 Rajpurkar et al. 2016 (D16-1264) 与 Rajpurkar & Jia et al. 2018 (P18-2124)；当前 bibliography **无** SQuAD bibitem。

---

## 5. AI 生成数据集裁定（补充核定点）

- 核验 `docs/decisions/ai_dataset_final_ruling.md`：`ai_generated_dataset_ruling.md` 的“有条件 GO”被撤回；v2.6 冻结但 **not-activated / 无适用对象**；不新增 v2.7；`real=0` 维持。
- 磁盘只读核验：`data/generated/` **不存在**；无 HellaSwag/生成数据文件；无生成 run。裁定第 57 行明确“审稿人无需为生成数据做质量审计（未启动）”。
- 本审计据裁定执行：**未对生成数据做任何质量审计**（无对象）。论文 `main.tex:391–397` 与结论 `:724–726` 已如实披露“提案已评估并撤回、not-activated、无遗留产物”；`reports/data/v2_6_not_activated_note.md` 留档。**结论：合规（PASS），无遗留产物。**

---

## 6. 风险清单（按等级）

| 级别 | 编号 | 风险 | 影响 / 建议 |
|---|---|---|---|
| **主要（投递前必须关闭）** | **R1** | **CI 口径在提交稿中与 v2.3 冻结约定冲突**：`tab:cleanmvp` / `tab:cleankd` 把 **pair-level 敏感性 CI**（如 `6.900 [5.499,8.313]`、`6.388 [5.360,7.400]`）作为唯一“95% CI”呈现，而 `bootstrap_summary.json` 的**主 CI 是 template_family**（`6.900 [3.564,10.100]`、`6.388 [3.653,8.814]`）。v2.3 `forbidden_after_freeze` 明令禁止“只报 pair-level 而不报 template-family”，且“pair-level sensitivity required alongside primary”。表注却写“8 template_family clusters”。元审查 §3.1/§3.2 与 `notes.md:48,152` 已将此项移交 PI/审稿人出口径说明。 | 这是负面/边界研究，统计诚信即卖点；只报较窄 CI 恰是 v2.3 要纠正的退化。**建议**：由 PI/审稿人出口径说明，令表内并列 template-family 主 CI 与 pair-level 敏感性（或表注明示主 CI 并附敏感性），勿只报窄的一套。**不推翻 C 判读**（两套下界均 >0），但为正式投递前门槛，不由写作者私改数字。 |
| **次要** | R2 | N1–N9 bibitem 无作者名、仅摘要级核验（§4） | 按协议 §9 投递前做全文口径核验并补作者名；或按 addendum 原文的“标题+arXiv+年份”占位并在 cover letter 说明，不得把章节级细节当已核实事实。 |
| **次要** | R3 | SQuAD 两条引用未进 bibliography（§4） | 写作者按 `p5_final_signoff` §4.1.5 补 Rajpurkar 2016/2018 两条。 |
| **次要** | R4 | 3 个历史 run 在 `consistency_report.json` 中 `ok=false` 且 `superseded=false`（`delta_lock_v2p1_2p0_par`、`p1_gpu_kdonly_mvp_seed1_par`、`p1_gpu_kdonly_mvp_seed2_fast`），且不在 `runs_index` 中 | 不在权威清单内，不影响结论；建议在 runs_index 显式标 superseded 或在审计脚本对外部/历史 run 标注，避免误读。锚点 `model_pair_check` 静默放行见 `anchor_eval_review.md` D4。 |
| **次要** | R5 | 文档计数陈旧（S3 与 `p5_final_signoff` 写“26 run”，实际 28） | 文档工程师同步为 28（含 2 锚点），纯计数，不影响科学结论。 |

> 无**阻塞级（方向推翻 / 诚信问题 / 判据篡改 / zero-re-prefill 违规）**风险：未发现读封存 test、挑 seed、改判据、mock 当证据、Oracle 信号泄漏进 Joint 推理图等问题。

---

## 7. P5 决议与证据路径

### 7.1 决议

> **CONDITIONAL GO — 放行至 ready-to-submit。** 关闭 R1（主要）及 R2–R5（次要）后，由真实 PI 在 TMLR 正式提交；本审计不代替 PI 的 venue/署名/时机人工决策，也不构成“忽略 CI 口径问题直接投稿”的许可。
>
> 我据 `p5_final_signoff` §5 出具本 compliance note：(1) SQuAD 锚点数值与 `anchor_eval_summary.json` 一致、严格 `exploratory_disclosure`（已核验，§3）；(2) 论文贡献表述与 §3 边界逐条一致，无已撤回贡献恢复、无跨源普适/真实文档验证主张（已核验，§1 S4/S5）；(3) S1–S5、引用、署名、venue、数据修复/real=0 披露无回归（S1–S5 PASS；引用残余见 §4）；(4) v2.1–v2.6 冻结文件未被回写、AI 生成集无遗留产物（§3/§5）。**唯一未清项 R1 为口径门槛，需 PI/审稿人出说明后在提交稿落实。**

### 7.2 关键证据路径

- S1：`reports/data_hash_binding_erratum.json`；`data/tasks/manifest.json`
- S2：`data/tasks/manifest.json:12–19`；`reports/data/acceptance_checks.json:27–30`；`reports/data/s2_hash_annotation.md`；`configs/prereg/stats_convention_v2.3.yaml`
- S3：`reports/runs_index.json`（28 项）；`reports/consistency_report.json`（31 项）；本次只读复跑 `/tmp/opencode/audit_consistency2.json`
- S4/S5：`papers/readkv_v2_draft/main.tex:62–74,525–534,606–613,666–676,719–729`
- kd 簇级 CI：`reports/bootstrap_summary.json`（`runs/p1_kd_clean_mvp_seed*`）；本次只读复算（§2）；`reports/review/meta_review/current_task_meta_review.md` §3.1
- 统计/一致性：`scripts/bootstrap_ci_report.py`、`scripts/consistency_check.py`（本次均以 `--output /tmp/...` 只读运行）；`reports/anchor_eval_summary.json`；`reports/review/anchor_eval_review.md`
- 引用：`papers/readkv_v2_draft/main.tex:159–208,748–812`；`reports/review/research_advisor/third_round_online_addendum.md` §1；`papers/readkv_v2_draft/notes.md:134,141,151`
- AI 数据：`docs/decisions/ai_dataset_final_ruling.md`；`reports/data/v2_6_not_activated_note.md`；`configs/prereg/ai_generated_data_v2.6.yaml`（not-activated）
- 裁决来源：`docs/decisions/final_boundary_study_signoff.md`；`docs/decisions/p5_final_signoff.md`

### 7.3 审计边界声明

- 本审计全程只读：未改 `src/**`、`reports/runs/**/scores.jsonl`、`configs/prereg/**`、论文正文或任何冻结判据；脚本输出重定向至 `/tmp/opencode/`，未写回仓库 `reports/**` 运行产物。
- 不把 mock/smoke（`reports/_non_authoritative/**`、`p3_smoke_*`）当证据；不把局部相关当因果；不因叙事需要放宽门槛。
- 科学结论的可信度仍受“val-only、8 族 exploratory、单合成等深对、封存 test 未评、real=0、SQuAD 锚点仅 exploratory_disclosure”约束；本审计未改变这些边界。

**签署：审稿人（最终边界研究收尾合规审计 · 2026-11-23 · HEAD 4613200）**
