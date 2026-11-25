# v3.0 G4 独立合规审计（INDEPENDENT COMPLIANCE AUDIT）

- 审查角色：reviewer（对抗性审阅 / 独立质量守门人），只读审查；不参与训练、不改代码/数据/判据/论文。
- 审查对象：v3.0 新研究（`configs/prereg/gpu_followup_v3.0.yaml`，FROZEN `2026-11-25`）G0→G1→G2→G3 全流程产物。
- 权威依据：`configs/prereg/gpu_followup_v3.0.yaml`；`docs/decisions/gpu_v3_scope_ruling.md`；`docs/decisions/v3_baseline_spec.md`；`docs/decisions/v3_g1_release.md`；`docs/decisions/v3_g2_release.md`；`docs/decisions/v3_e2_{argument,interface,rows}_ruling.md`；`docs/audit/GPU_experiment_plan_2026-11-25.md`。
- 写入边界：本审计**只写本文件**；全部统计脚本以 `--output /tmp/opencode/v3g4/...` 运行，不触碰仓库产物。无 GPU 运行。
- 日期：2026-11-25。所有结论均为**流程/合规核验**，不含科学重解释、不引用任何性能数值作为主张。

---

## 0. 合规裁定

> **裁定：CONDITIONAL PASS（有条件放行）—— 无阻塞级风险；须 PI 在最终签署时显式知悉并裁定 §4 的 4 项条件项（R1–R4）。其中 R3 为关键：G4 scientist 判读件当前为 BLOCKED 未签发（占位符未填、无绑定数值的分支裁决），G4「scientist + reviewer 双签」尚未齐备。**

| 审计维度 | 结论 |
|---|---|
| 1. 门控时序（G0→G1→G2→G3 顺序，无未过门先跑） | **PASS** |
| 2. 冻结不变量（v2.1–v2.9 / 当前稿件 / 贡献 / 投稿 / 数据隔离） | **PASS** |
| 3. 运行入账（39 目录、38 分数、1 ABORTED、6 `_r2`、哈希/快照/zero-re-prefill/one-shot） | **PASS** |
| 4. 事后纪律（预注册分支、无择支/调参/改样） | **PASS**（附 R3：scientist 判读件为 BLOCKED 未签发，占位符未填） |
| 5. 边界措辞（E1/E2/E5/E6 无越界主张） | **PASS** |
| 6. E2 技术量诚实缺口（显存/耗时/forward 未落盘，未伪造） | **PASS（如实披露）** |
| 强制脚本（consistency_check / bootstrap_ci_report） | **已运行**，结果见 §3.8；无可作为 v3 PASS 证据的限制见 R2 |

**放行建议：准。`reports/review/v3_g4_compliance_review.md` 可作为 G4「独立审阅」环节的合规放行件；最终新研究签署前，PI 须对 R1–R4 逐项裁定。不授权投稿、不授权回写当前稿件或任何冻结判据。**

---

## 1. 门控时序审计（维度 1：PASS）

按决策/产物文件 mtime 与每个 `config.json:created_at` 建立时间线：

| 节点 | 文件 / run | 时间戳 (UTC) |
|---|---|---|
| G0 范围裁决 | `docs/decisions/gpu_v3_scope_ruling.md` | 13:45:48 |
| prereg 冻结 | `configs/prereg/gpu_followup_v3.0.yaml` | 13:46:12 |
| G1 数据/可行性审计 | `v3_g1_feasibility_audit.md` / `v3_g1_e2_entry_report.md` / `v3_g1_engineer_implementation.md` | 13:54 / 14:39 / 15:03 |
| G1 放行 | `docs/decisions/v3_g1_release.md` | 15:05:45 |
| G2 pilot 报告 | `reports/review/v3_g2_pilot_report.md` | 15:36:52 |
| G2 放行 | `docs/decisions/v3_g2_release.md` | 15:37:58 |
| E2 三份 PI 裁定 | `v3_e2_argument_ruling.md` / `_interface_` / `_rows_` | 16:32:45 / 16:34:40 / 16:44:44 |
| E2 权威 run | `reports/runs/v3_E2_heldout_s0s1s2/config.json` | 18:50:34 |
| E1 正式格（最早～最晚） | `v3_E1_A_legacy_bundle_s0` → `v3_E1_B_fully_repaired_s2` | 18:55:16 → 20:07:47 |

- **无正式格先于其门**：最早的正式格 `v3_E5_affine_s0`（15:45:57）晚于 G2 放行（15:37:58）；`v3_E5_pilot_s0`（15:21:21）处于 G1 放行后、G2 放行前，属 G1 明确授权的**技术 pilot（NON-AUTHORITATIVE）**，合规。
- **E2 三裁定全部早于 E2 权威 run**（16:32–16:44 < 18:50:34）：接口/行门修正均发生在评分前，符合「看到结果前锁定」纪律。
- 门控文件链一致：G1 只放行 G2、G2 只放行 G3、G4 未提前放行；`v3_g2_release.md §5` 明记 G4 未放行。
- **结论：门控顺序严格递进，无越门。**

---

## 2. 冻结不变量审计（维度 2：PASS）

| 不变量 | 核验方式 | 结论 |
|---|---|---|
| v2.1–v2.9 prereg 一字不回写 | `configs/prereg/*.yaml` mtime 全为 `13:20:34`；仅新增 `gpu_followup_v3.0.yaml`（13:46:12） | PASS |
| 当前稿件只读 | `papers/readkv_v2_{draft,tmlr_anonymous,arxiv,zh}/**` mtime 全为 `13:20`；仅 `tmlr_anonymous/__pycache__/reproduce.cpython-312.pyc`（15:05，pytest 副产物、非正文） | PASS |
| 贡献(1)(2) 撤回、(3) withheld，无恢复 | v3 报告/裁定全文扫描无 contribution 恢复或方法增益措辞；`docs/decisions/final_signoff.md`/`final_boundary_study_signoff.md` 状态未变 | PASS |
| P2/P3/P4 永久放弃；P4 仍 NO-GO | `final_signoff.md:57–58`、`final_boundary_study_signoff.md:93,99,137` 维持 NO-GO；v3 未重启 | PASS |
| 旧主终点不重算、不回写 | v3 产物均写入新 `reports/runs/v3_*`；无历史 `reports/runs/p1_*`/`audit_*` 改动 | PASS |
| 不代为投稿 / 无投稿动作 | 无新建 submission/arxiv/openreview/cover 产物；稿件 mtime 未变 | PASS |
| 数据隔离（无 SQuAD/ARC/HellaSwag/真实文档/AI 生成混入） | 全 `reports/runs/v3_*` 与 `data/variants_v3` 关键词扫描为空；`v3_* config.sizes.real=0` | PASS |
| test 不称 sealed / 不 pooled | v3 全程用 `previously_unevaluated_held_out_split`，`sealed_test_read=false`、`pooled_inference=false`；当前稿件 `sealed test … unevaluated` 为冻结只读的旧稿自身表述，未被 v3 改写，符合「另立新研究」边界 | PASS |

> 备注（非违规）：当前 TMLR 稿件仍写「sealed test remains unevaluated」，这是**冻结旧稿对其自身范围**的正确陈述；E2 结果属新研究，未回写，故不构成矛盾。写作者日后引用 E2 时不得据此改动旧稿该表述。

---

## 3. 运行入账与产物一致性审计（维度 3：PASS）

### 3.1 目录与格数
- `reports/runs/v3_*` 共 **39** 个目录；含 `scores.jsonl` **38** 个；唯一无分数目录 `v3_E1_B_entity_disjoint_only_s0` 为 **ABORTED**（`config.json.status="ABORTED"`，`reason="PathRejected: … DATA-TASK change … CPU replay … NOT valid"`，仅 config+manifest，无 metrics/scores）—— 合规留痕。
- 格数核对：E1 Panel A 15（5 变体×3 seed，含 legacy 历史对角）、Panel B 15（含 6 个 `_r2`）、E2 1 目录内 6 格、E5 3 正式+1 pilot、E6 3；合计与 G2 放行 §4 矩阵一致。
- 6 个 `_r2` rerun（`v3_E1_B_{entity,template}_disjoint_only_s{0,1,2}_r2`）逐一核验：`data_task_change=True`、`input_text_changed=True`、`gpu_forward_authorized_by_flag=True`、`cpu_replay_valid=False` —— 符合 v3.0 §3「仅输入文本变化才追加 GPU 前向并单列数据任务改变」。`v3_g3_e1_batch_summary.json` 记 `completed=30,total=30`，全部 seed/对照入账。

### 3.2 哈希与快照身份
- 全 38 个分数目录的 `manifest.json` 登记文件（共 122 个，排除自引用 manifest）逐一重算 SHA-256 与 size：**0 mismatch**；`scores.jsonl` 38/38 唯一、`config.json` 39/39 唯一，无分数/哈希交叉混用。（manifest 自引用哈希陈旧为 `RunContext.finalize()` 已知设计，batch1 §4.3 已披露。）
- 模型快照：正式格一律使用 SHA 命名钉扎链接，不重新解析 master：
  - E1：`Qwen3-1.7B-1ddb5b89ebc9` / `Qwen3-0.6B-660db3b73d788119`；
  - E5：`Qwen34B-sha256-8ba006f74fecfaae` / `Qwen31.7B-sha256-1ddb5b89ebc90dcb`（36→28 proportional）；
  - E6：`Qwen31.7B-sha256-1ddb5b89ebc90dcb` / `Qwen30.6B-sha256-660db3b73d788119`。
  - 链接均解析到固定本地快照目录；逐文件 SHA 对 `model_manifest.json` 0 mismatch（batch1 §0/§3）。
- **E2 权威产物哈希实测**（与 `v3_g3_batch2_report.md §9` 完全一致）：
  - `config.json` `985c71f1d632e9152e994d288cd671afb787cde438306c0994dc5384c73186b2`
  - `metrics.json` `42b78d5d2d74fa66384c7dc637fac5b6637d2b4865f94da4468d7fdff352cb68`
  - `scores.jsonl` `15fb742067184bad7504c3f71206e0b1a0be30c43b2a48b2239615fe9c00dd26`
  - `manifest.json` `af23c1d3ee65976fe33f4bdd377efb77f8292a2c54f9f87f93d7a9e30cfc02bf`
  - 入口 SHA `da80afdc35f433c65c22938a0bde516927feaef5dac0a6ae59d60e07d72b8f6f`（写盘于 config/metrics）。

### 3.3 E2 哈希双值与数据绑定（独立重算，全部吻合）
| 对象 | 实算 SHA-256 | 与裁定/锁一致 |
|---|---|---|
| `configs/prereg/gpu_followup_v3.0.yaml`（`--eval-config-hash`） | `d8c2321fc4ba6abeda80e6f581d3f7ef6c592c9173de757aad1a40120ae811e6` | ✓ |
| `data/tasks/cf_pairs.jsonl` 整文件（`--test-sha256`，裁定 f910…） | `f910f1f1196a21041765834654af8233d216ef4bf4f28f4c60abbd0641aa894a`（520 行） | ✓ |
| test split 派生哈希（filter `split=="test"`，规范序列化 c545…） | `c5450013bc9fc9b84dec286a653207f2dde8168d0df74a24896218d32769a7a2`（300 对 / 16 family） | ✓ |
| `reports/data/v3_e2_test_lock.md` | `c2d629b5f928d03c106a2b4b6e8e3e7059af11f34c12bd5ace019d5c9b9c9d5e` | ✓ |
| `data/variants_v3/manifest.json` | `6b3d63ae194df9af8d1369737a1e8c627cae9f17be37fb3380797fa0a26c2ff9` | ✓ |

`set` 语义正确：`--test-sha256` = 整文件字节哈希（f910…），`c545…` 仅作 300 对派生描述元数据，未混用。

### 3.4 zero-re-prefill
- 39/39 目录 `config.json.zero_re_prefill=true`；E1/E2 的 `metrics.json` 同为 true；E5/E6 由 `g3_runtime_audit.json` + `g3_injection_audit.json` 以 forward-audit 记录（`zero_re_prefill.passed=true`、`basis="forward_audit(strict)"`、`doc_tokens_fed_to_student=0`）。全部席位 strict 成立，符合 v3.0 `common.execution.zero_re_prefill`。

### 3.5 E2 one-shot 门控（重点）
- 证据链（`v3_g3_batch2_report.md §2/§6/§8/§9` + 三份 PI 裁定）：
  - 第 1、2 次 preflight STOP：**evaluator 调用 0 次**（哈希参数错、接口无法表达 per-seed 校准），由 `v3_e2_argument_ruling.md`/`v3_e2_interface_ruling.md` 关闭。
  - 第 3 次调用：在 `_load_jsonl_pairs(path,"test")` 的 test-row 门 **REFUSED**（`probe-F1-0000`，exit 2），未加载模型/未前向/未评分；`v3_e2_rows_ruling.md §1` 裁定 pre-scoring REFUSED 不消耗科学 one-shot。
  - 第 4 次（唯一权威）调用：`COMPLETED`（exit 0），`authoritative=true, one_shot=true, smoke=false`。
  - **evaluator 进程调用 = 2（1 次 pre-scoring REFUSED + 1 次权威）；权威评分 pass = 1**；无重试/重跑/返修/多轮查看。与任务给定 attestation 完全一致。
- 权威产物结构：6 格 = affine/kd_only × 0/1/2；`scores.jsonl` 1800 行全部 `split=="test"`、300 唯一 `pair_id`、每格 300 对；6 格共享单一 `pair_set_fingerprint=9dad7c5c6786bfa9d8102675afd49e6dc183682fe99609376720d3ef737c7477`；`exploratory=true, pooled_inference=false, sealed_test_read=false`。
- §8/§9 报告正文无 `E_CF`/Self/Joint/coverage/L/CI 等性能数值（已全文扫描确认）。

### 3.6 统计双口径（family 主 CI + pair 敏感性）
- E2 `metrics.json` 每格 `E_CF.ci` 与 `template_family_ci.ci` **逐一相等**（6/6），`pair_level_ci` 单列且更窄；`n_resamples=10000`、`n_clusters=16`→exploratory。E1 各 `metrics.json` 每 arm 同时含 `ci_family` 与 `ci_pair_sensitivity`、`bootstrap.primary_unit=template_family`、`sensitivity_unit=pair`、`min_clusters_for_inference=24`（实际 8 family→exploratory）。
- 用冻结脚本 `bootstrap_ci_report.py`（v2.3 口径）从 `scores.jsonl` 独立重算（38 个 v3 run）：E1 joint arm 重算 family CI `[2.925,7.527]` vs metrics `[2.921,7.588]`、pair `[4.391,6.352]` vs `[4.398,6.374]` —— **同族同口径、仅重采样实现差异，确认统计从分数重建而非手改**；E2 每格主 CI 与 pair 敏感性并存（见 §3.5）。
- 注意：通用脚本把 E2 六格收为单一 `arm="unknown"` 的合并估计（E_CF 7.770 `[5.905,9.416]`）——该聚合**不得**用于 E2 科学推断（违反 no-pooling）；权威逐格 CI 只在 `metrics.json`。此项列入 R4 知悉。

### 3.7 边界措辞（维度 5：PASS）
对 `docs/decisions/v3_*.md`、`reports/review/v3_*.md` 逐条对抗扫描：未发现「因果贡献分解 / 泄漏普遍制造假阳性 / 跨模型泛化 / faithful baseline / sealed / pooled / 3 份独立 test replicate」等肯定式越界主张。E1 明列 `forbidden_claims`；E2 明写"仅固定配置外推、不作普遍泛化"；E5 `replicated_on_one_extra_pair`；E6 复现门 `NOT PASSED`、采用 `v3-BM-MLP-KD` 且"不称已发表方法基线"（`v3_baseline_spec.md §1`）。工程报告反复声明"不含任何科学结论、判读归 G4"。

### 3.8 强制统计脚本运行结果
- `python -m scripts.consistency_check --output /tmp/opencode/v3g4/consistency_report.json`：`checked=103, failed=103, head_hash=""`。**全部失败源于工作区非 git 仓库**（`git_hash='no-git' not in HEAD history`、`commit tree lacks run code` 103 项、head_hash 全空）；另有 v2 时代 `PAIR_EXPECT` 与 v3 新模型对不符（layer_map 28/36、SHA 钉扎路径被判 unknown pair）等工具口径失配。**这是环境/工具局限，非 v3 违规**；v3.0 §0 已预期「git diff（若可用）应为空」，不可变性由 SHA-256 指纹替代（本审计已独立核验 122 文件 0 mismatch）。见 R2。
- `python -m scripts.bootstrap_ci_report --output /tmp/opencode/v3g4/bootstrap_summary.json`：`runs=98`（全仓）；对 v3 子集以只读软链单独重跑 `runs=38`，结果 `/tmp/opencode/v3g4/bootstrap_v3_only.json`。均确认 family 主 CI + pair 敏感性双口径可复算（见 §3.6）。

---

## 4. 需 PI 裁定的条件项与风险清单

> 以下均非阻塞（无 阻塞 级风险），但须 PI 在最终签署时逐项裁定。

- **R1（主要 · 溯源标识一致性）**：run `config.json` 的 `protocol_version` 字段不一致——E1（30 格）与 E6（3 格）为 `"3.0"`，而 E2 与 E5（3 正式+pilot）为 `"2.0"`；E5 `experiment_config.prereg` 仍写 `phase1_benchmark_decision.yaml (frozen protocol-v2.0)`。核验表明这是复用冻结入口（`P1_gpu.py`/`e2_test_evaluator` 的 RunContext schema v2）的**陈旧字符串**：E2 `metadata.prereg_version=3.0`、`criteria_source=v3.0`；E5 `g3_runtime_audit.json` 的 criteria/release_source 以 G2/G3 放行与 v3.0 为准，batch1 §0 已重算 prereg `d8c2321f…` 执行前后不变。**建议**：PI 确认这些字段为入口 schema 残留、非判据切换；新研究报告须显式声明全部 v3 格受 v3.0 治理，不得据 `"2.0"` 字段误读为 v2.0 实验。

- **R2（主要 · 合规脚本证据局限）**：`consistency_check.py` 在非 git 工作区 103/103 FAIL（`head_hash=""`），且 v2 时代 `PAIR_EXPECT` 与 v3 新模型对/钉扎路径口径失配；其结果**不能作为 v3 的 PASS 或 FAIL 科学证据**。已以逐文件 SHA-256（122 文件 0 mismatch）、prereg/稿件 mtime 未变、模型钉扎链接逐文件哈希替代核验。**建议**：PI 明示接受"SHA-256 指纹替代 git 哈希"作为本环境的不可变性证据口径，并在新研究报告披露该局限。

- **R3（主要 · G4 scientist 判读件为 BLOCKED 未签发）**：仓库内确有 scientist 角色产物 `docs/audit/v3_statistical_interpretation.md`（mtime 20:11），但其 §0 明确标注 **BLOCKED / 未签发**：全部结果为 `⟨FILL⟩` 占位符，`从 scores.jsonl 重算的 bootstrap CI = 未产出`、`分支裁决（绑定具体数字）= 未产出`、`签署/放行 = 未放行`。原因为该会话读白名单不含 `reports/runs/**`、`reports/review/**`、`data/**`，无法访问权威数值（§0 逐项记录 permission.rejected），并明确禁止把占位符、G1/G2 pilot 数字或 v2 数字当 v3 结果——**这一"不伪造"处置本身正确，予以认可**。因此 G4 放行文件要求的「scientist + reviewer 共同完成统计与判读」目前**仅 reviewer 侧（本件）完成**：scientist 侧只产出冻结统计规格 §1 与预承诺分支映射 §2–§5（逐字取自 prereg §3–§6，无事后造支），未产出绑定数值的分支裁决。family bootstrap + pair 敏感性**已在各 run `metrics.json` 由冻结入口计算、且本审计已从 `scores.jsonl` 独立复算**（§3.6），但尚未由 scientist 以签署件形式归位。另：该件 §6 的 run 清点为「待核、不臆断」，其 `3+3+1+30=37 dirs/42 cells` 的粗算与本审计实测口径不同——本审计已据实钉清（§3.1：39 目录 = 38 计分 + 1 ABORTED；E1A=15、E1B=15 计分+1 ABORTED、E2=1 目录/6 格、E5=3 正式+1 pilot、E6=3），scientist 的"待核"由本件解答。**建议**：PI 裁定——需由具权限的 scientist 会话在解锁数据后把 §1.5/§2–§5 的 `⟨FILL⟩` 逐项替换为实测值并写出分支裁决句（绑具体数值 + family/pair 两 CI，逐 seed 不 pooled），签署后方可最终 G4 签署；若 PI 以 per-run `metrics.json` + 本审计复算视作已满足，须落盘豁免说明。不得把占位符/pilot/v2 数字当结果。

- **R4（次要 · 知悉项，三项）**：
  - (a) **E2 技术量诚实缺口**：冻结 evaluator 未持久化峰值显存、耗时、forward 计数、cache 形状、Self/Identity 差分；`v3_g3_batch2_report.md §5/§9` 如实标"未记录、无法独立核验"，**未用 pilot 数字或占位值伪造**。依 one-shot 纪律不得重跑补采。此为**如实披露的诚实局限**，本审计予以认可；建议 PI 接受为记录在案的限制，不授权破坏 one-shot 的重评测。
  - (b) **通用脚本 E2 聚合陷阱**：`bootstrap_ci_report.py` 将 E2 六格收为 `arm="unknown"` 合并 CI；严禁将其当 E2 结果（no-pooling）；权威逐格 CI 仅存 `metrics.json`。写作者/科学家不得引用该聚合值。
  - (c) **E5 pilot 快照路径**：`v3_E5_pilot_s0`（NON-AUTHORITATIVE，已排除科学）config 指向裸 master 快照路径而非 SHA 链接；正式 E5 格均用 SHA 钉扎。属 pilot 历史产物，非违规，仅备案。

---

## 5. 最终放行建议与需 PI 裁决清单

**放行建议（G4 独立审阅环节）：CONDITIONAL GO。**
1. 认可 G0→G1→G2→G3→G4 流程时序合规、无未过门先跑；认可 39/38/1/6 运行入账完整、哈希/快照/zero-re-prefill/one-shot 全部达标；认可冻结不变量未受侵蚀、边界措辞无越界。
2. **可签署 G4 独立审阅（reviewer 侧）合规件**（本文件）；但**最终新研究报告签署前**，PI 须对 **R1（溯源标识）、R2（无 git 一致性脚本口径）、R3（scientist 判读件 BLOCKED 未签发）、R4（三项知悉）** 逐项裁定并落盘。
3. **不放行**：任何投稿动作、任何当前稿件/冻结判据回写、任何贡献恢复、任何把 v3 结果包装为方法增益或普遍泛化的措辞。
4. R3 为最终签署的实质前置：须由具权限的 scientist 会话据 `reports/runs/v3_*/scores.jsonl|metrics.json` 把 `docs/audit/v3_statistical_interpretation.md` 的 `⟨FILL⟩` 全部替换为实测值、写出按 v3.0 §3–§6 预承诺分支对号入座的裁决句并签署；或以 PI 落盘豁免说明替代。补件为纯判读归位、不产生新运行产物，本审计结论不变。严禁把占位符、G1/G2 pilot 数字或 v2 数字当 v3 结果。

**需 PI 明确裁决项（汇总）**：R1 溯源字段是否为 schema 残留而非判据切换；R2 是否接受 SHA 指纹替代 git 哈希；R3 是否强制补 scientist G4 判读件（当前 `docs/audit/v3_statistical_interpretation.md` 为 BLOCKED 未签发、占位符未填、无绑定数值的分支裁决）方可最终签署；R4(a) 是否接受 E2 技术量未记录为最终限制（不重评测）；R4(b)/(c) 仅知悉备案。

---

*签署：reviewer（G4 INDEPENDENT COMPLIANCE AUDIT · 只读 · 2026-11-25）。裁定：CONDITIONAL PASS；放行建议：有条件放行，待 PI 就 R1–R4 裁定后完成最终签署。*
