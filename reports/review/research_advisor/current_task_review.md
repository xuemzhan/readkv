# readkv 当前任务独立审查报告（研究问题顾问 · 联网对抗性评估）

- 审查角色：research-advisor（独立于主链路，只读仓库 + 联网取证；不改代码/数据/判据/运行产物/论文）
- 审查日期：2026-11-23
- 审查范围：方向 + 方案 + 实验 + 结果（全量）
- 工作目录：/root/readkv
- 联网状态：**可用**。已用 websearch/webfetch 抓取 arXiv 一手原文（KV-Lingo / CacheLink / Heo et al. / Does Accuracy Equal Evidence / Contrast Sets / Kaushik / Qwen3 技术报告 / 簇 bootstrap / Holm / HellaSwag 官方）。所有外部论断均记录 URL + 访问日期 + 一手/二手标注。
- 唯一写入路径：本文件（`reports/review/research_advisor/current_task_review.md`）。未执行 shell、未重算统计、未触碰任何冻结产物。
- 证据效力声明：本报告只**转抄** `reports/runs/**/metrics.json`、`reports/**` 审计结论、`docs/decisions/**` 与联网一手来源；不重算任何统计。`reports/_non_authoritative/**`、`reports/p3_smoke_report.md` 一律视为**未定稿/非权威**，不作科学证据。

> ## ⚠ 二轮修订横幅（2026-11-23，11:01 后新证据）
> 本报告已做**增量修订**。**修订后的一句话结论：PIVOT**（原"效用保持型反事实失真 gap + 机制定位"主线已被 PI `clean_data_reversal_ruling.md` 裁定翻转、本顾问独立复核后**同意并确认**；新定位"迁移失败边界 + 数据泄漏教训"负面/实证研究为 **CONDITIONAL GO**，待 clean kd_only 三 seed 择支与溯源收尾）。
> **§8（修订记录与增补）为二轮权威结论，与正文 §0–§7 冲突处以 §8 为准**；§0–§7 保留一轮原文供审计追溯，其中关键过期表述已就地标注"[二轮修订]"。
> 触发修订的新证据（均已自行读取核实，非凭转述）：①`p1_clean_mvp_seed{1,2}` 落盘 → **affine 三 seed 坍塌确证**（非一轮所述"仅 seed0"）；②PI `clean_data_reversal_ruling.md`（贡献1降级/贡献2撤回/P2P3取消）；③`clean_data_reversal_emergency_review.md`（翻转可信·高·非实现 bug）；④**`p1_kd_clean_mvp_seed0/metrics.json` 在本轮读取时已完整落盘**（晚于用户"尚未写出"的转述）——`transfer_broken=false`、dual 0.70、E_CF 6.388 大 gap，**seed1/2 仍未产出、该 run 未审计**，为决定性择支证据的**部分到位**，不推测终值。详见 §8。

---

## 0. 执行摘要（供主会话转述）

**一句话结论：[二轮修订] PIVOT（原主线已由 PI 裁决翻转，本顾问同意并确认；新定位"失败边界 + 数据泄漏教训"为 CONDITIONAL GO）。** 一轮原文（CONDITIONAL GO）见 §8 修订前后对照。

[二轮修订] 放行"按 PI `clean_data_reversal_ruling.md` 重定位为负面/实证结果论文 + 完成 clean kd_only 三 seed 择支 + 溯源收尾 S1–S3"；**不放行投稿、不放行任何原正向贡献(1)/(2) 主张（已撤回）、不放行方法增益主张**。原"继续修复+重跑以重建正向 gap"的路径已被新证据超越：affine 三 seed 坍塌确证，正向证据基础塌陷。

核心判断：
1. **研究问题成立且重要**，但**新颖性窄、且被 2026 年公开文献部分 anticipate**。CacheLink（arXiv 2610.15509）已发表"重构保真≠接收端效用 + K/V 的 query 依赖功能重要性 + 四臂 K/V swap 诊断 + routing/consumption 角色 + CE+KL 功能监督"；Heo et al.（2608.03893）已发表闭式 ridge 跨模型映射且部分对急剧退化；"Does Accuracy Equal Evidence?"（2608.01631, EMNLP 2026 Findings）已在 KV 压缩 setting 提出"准确率≠证据保真"。本课题**真正未被占据的缝隙**是：把**成对反事实文档编辑响应保真 `E_CF=|D_trans−D_self|`** 作为跨模型 KV 迁移（严格 zero re-prefill）的**主终点**，配 F1–F6 切片 + F5 负控 + 联合报告纪律 + 预注册决策树。这是真实但窄的**评价层**贡献；机制层与方法层的新颖性被严重挤压。
2. **方案纪律优秀**（先写后跑、版本化冻结判据、联合报告防退化、Oracle 隔离、簇级 paired bootstrap + Holm + ≥3 seed、决策树、§10 贡献门槛），但**执行存在实质缺口**：强基线只跑了 affine + kd_only（consumer/score/ridge/CE/contrastive/CacheLink 均未实现，违反 E1/§7 自身要求）；v2.3 要求 ≥24 簇才可推断，而重建后 **test 仅 16 个模板族、val 仅 8 个** → 当前所有 CI 只能算**探索性**，主终点"CI 上界<0"的确认性门槛按现设计无法达成。
3. **[二轮修订] 实验：affine 失败边界证据已确证并审计，kd_only 择支证据部分到位。** 所有 pre-fix 权威 run 因数据正确性缺陷（18 退化对、≥15 组跨 split 逐字泄漏含 train↔test 整对、实体全共享、模板骨架 100% 重合、簇退化为逐对 i.i.d.）已 superseded；**干净重跑 affine 三 seed 齐全**（`p1_clean_mvp_seed{0,1,2}`，git efc3ba3，已入 v2.3 bootstrap_summary/consistency_report，ok=true、exploratory 8 簇、template-family CI 下界均>0），**全部 transfer_broken=true**；E0 干净复验 PASS。**clean kd_only seed0 已落盘**（`p1_kd_clean_mvp_seed0`，git 6413ba0，transfer_broken=false、dual 0.70、E_CF 6.388 大 gap），**seed1/2 未产出、该 run 未入审计**；P2/P3 已被 PI 取消（不再重跑）；封存 test 从未评测（纪律保住）。一轮"clean 仅 E0+P1 seed0、kd/P2 均缺"的表述已过期。
4. **[二轮修订] 结果：原正向贡献已确证为数据假象并由 PI 撤回；新负面结果（affine 失败边界 + 方向性翻转）已确证。** affine 三 seed joint E_CF 6.900/8.159/8.540、dual 0.417/0.283/0.383（Self 0.817/0.900/0.783）、全部 transfer_broken=true，与 pre-fix"效用保持型失真"（dual 0.617–0.667、E_CF 1.93–2.12、broken=false）**方向性翻转**；紧急复核判**翻转可信（高）、非实现 bug**（跑分代码 458de18..efc3ba3 逐字未变，旧数据退化对/泄漏直接证实，Self 锚点反而更健康，K-only/V-only 近 Self 仅 Joint 坍塌）。**PI 已裁定贡献(1) 冻结降级、贡献(2) 立即撤回 withheld（不等 P2）**，本顾问同意。**决定性 clean kd_only 择支待决**：seed0 呈"not broken + 大 E_CF gap"（最接近 PI 预承诺情形 C 但 gap 不"小"），seed1/2 未出、未审计，最终 A/B/C 择支属 PI（§3.3 预承诺），本结论不覆盖 PI 裁决。
5. **[二轮修订] 文档一致性：main.tex/notes.md 已按裁决重写（贡献1/2 withdrawn、Table cleanmvp/reversal、kd_only PENDING、机制图不画）；但 README/engineer_status/runs_index 仍过期**（README 仍 22 run、无翻转/撤回；runs_index 未纳入 clean run，紧急复核 S3）。须同步。

**给 PI 的底线建议 [二轮修订]**：**同意并确认 PI `clean_data_reversal_ruling.md`**——贡献(1) 冻结降级、贡献(2) 撤回 withheld、P2/P3 取消、论文重定位为"迁移失败边界 + 数据泄漏如何制造虚假科学发现"的负面/实证结果、投稿继续暂缓。剩余动作：①完成 clean kd_only 三 seed 并按 §3.3 预承诺 A/B/C 择支（seed0 已落盘 not broken+大 gap，seed1/2 待出、未审计）；②闭环紧急复核 S1（数据哈希入 run 产物）/S2（v2.3 未跟踪+sha 不一致 e44c6acb≠5200940c，须 PI 澄清回填过程）/S3（runs_index 更新+旧 run superseded 标注）；③同步 README/engineer_status；④相关工作正面引用并区分 CacheLink/Heo/"Does Accuracy Equal Evidence?"/Contrast Sets/Kapoor-Narayanan（W14，泄漏教训已确立，新定位新颖性须限定为"具体预注册翻转案例 + E_CF 框架"）。**本结论不覆盖 PI 裁决**；若 PI 欲把 kd seed0"not broken+大 gap"单独处理（超出 §3.3 情形 C"小 gap"字面），须 PI 新增版本澄清预承诺口径，非本顾问可定。

---

## 1. 一句话结论

> **[二轮修订] PIVOT**：原"效用保持型反事实失真 gap（贡献1）+ V-消费机制定位（贡献2）"主线在干净数据上**不成立**——affine 三 seed `transfer_broken=true` 已确证（紧急复核高可信、非实现 bug），旧正向信号系数据缺陷假象；**PI 已裁定贡献(1) 降级、贡献(2) 撤回、P2/P3 取消、重定位为负面/实证结果论文，本顾问独立复核后同意并确认，本结论不覆盖 PI 裁决**。新定位"跨模型 KV 迁移失败边界 + 数据泄漏教训"为 **CONDITIONAL GO**：待 clean kd_only 三 seed 按 PI §3.3 预承诺 A/B/C 择支（seed0 已落盘 not broken+大 gap、seed1/2 待出未审计）+ 溯源收尾 S1–S3 + 论文重写经复核 + 投稿暂缓。**一轮原结论 CONDITIONAL GO 及其"kd_only 三 seed 仍 broken 才 PIVOT"的触发条件已被新证据超越，见 §8。**

---

## 2. 四维度评估表

| 维度 | 评级 | 关键理由 | 证据编号 |
|---|---|---|---|
| **方向（研究问题）** | **合理** [二轮：原正向假设被证伪，重定位后问题仍成立] | 原问题（KV 迁移的反事实保真）清晰/可证伪/重要；但"utility-preserving gap 存在"这一正向假设对 affine 已被干净数据证伪。**重定位后的问题（失败边界 + 数据泄漏如何制造虚假发现）成立且可发表为负面/实证结果**。新颖性须限定：泄漏教训本身已确立（Kapoor-Narayanan W14）、迁移失败已知（Heo W3）、成对反事实评测已知（Contrast Sets W5）；真正空白 = 具体预注册翻转案例 + 成对反事实 `E_CF` 框架 × 跨模型 zero re-prefill。 | L2,L8,L41,L47,L48；W1,W2,W3,W4,W5,W6,W7,W13,**W14** |
| **方案（协议/设计）** | **存疑** [二轮：纪律优秀且已成功纠错，设计缺口仍在] | **纪律 proven effective**：先写后跑/版本化冻结/联合报告/正交 transfer_broken 字段/预承诺择支规则成功检出并纠正了一个"显著"假阳性——这是方案的最大优点。缺口仍在：①v2.3 min_clusters=24 但 test=16/val=8 → 推断探索性（对大效应负面结果阻塞性较低，但限制确认性/泛化主张）；②强基线族不全（仅 affine+kd_only，consumer/score/CacheLink 未跑）；③合成域窄（每 split 8 实体、real=0）；④少簇百分位 bootstrap 覆盖存疑（W9）；⑤self_threshold 元数据误标 0.001；⑥pipeline metrics CI 仍 pair-level（v2.3 CI 仅审计脚本产出）。 | L2,L3,L5,L6,L7,L19,L20,L37,L38,L39,L40,L42,L44,L47,L48；W2,W3,W9,W10 |
| **实验（执行/证据链）** | **存疑** [二轮：affine 失败边界已确证并审计；kd_only 择支进行中/未审计] | **已确证**：affine 三 seed 干净重跑齐全、入 v2.3 审计（ok=true、exploratory、template CI 下界>0）、E0 干净 PASS、紧急复核排除实现 bug。**待决/缺口**：①clean kd_only 仅 seed0 落盘（未审计），seed1/2 未产出 → A/B/C 择支未定；②runs_index 未更新、README/engineer_status 过期（S3）；③S1 数据哈希未入 run 产物、S2 v2.3 未跟踪+sha 不一致；④P2/P3 已取消（PI 裁定，不再补）；⑤consumer/score/CacheLink 基线从未跑；⑥封存 test 从未评测（纪律保住）。一轮"clean 仅 seed0、未审计"已过期。 | L14,L16,L17,L29,L30,**L45,L46,L47,L48,L49,L50,L51,L53**；W2,W3 |
| **结果（主张—证据一致性）** | **合理** [二轮：就新负面定位而言证据已确证；原正向主张已撤回] | **新负面结果已确证**：affine 三 seed 方向性翻转（旧 E_CF 1.93–2.12/broken=false ↔ 新 6.90–8.54/broken=true）、紧急复核高可信非 bug、旧数据退化对/泄漏直接证实、Self 锚点更健康、K/V-only 近 Self 仅 Joint 坍塌 → "数据泄漏制造虚假 gap + affine 失败边界"主张证据充分。**原正向贡献(1)/(2) 已确证为数据假象并由 PI 撤回**（不再声称）。**待决**：kd_only seed0 not broken+大 gap（最接近情形 C 但 gap 不"小"），seed1/2 未出 → 最终叙事 A/B/C 待 PI 择支，但不影响 affine 失败边界的确证。措辞精度：joint E_CF 仍**低于**错配/零控制（非"相当"，S4）；broken 由 dual-drop 单信号触发、exploratory（S5）。无 mock 进入主张、主终点从未声称。 | L1,L11,L13,L14,L16,L22,L23,L25,L30,**L45,L46,L47,L48,L49,L50,L52**；W2,W3,W4,**W14** |

> 评级说明 [二轮修订]：四维均非"不合理"——未发现伪造/mock 冒充/挑 seed/事后改判据/泄漏隐瞒；相反，项目主动揭露并修复严重数据缺陷、**在干净数据翻转后立即撤回正向贡献、取消无前提的 P2/P3、预承诺择支规则防事后择支**，是 exemplary 的科研诚信与自我纠错。**结果维度由一轮"存疑"升为"合理"**：一轮的正向主张证据不足，二轮 PI 已撤回正向主张、重定位为负面结果，而负面结果（affine 失败边界 + 翻转）已三 seed 确证并审计。**方向/方案/实验仍附保留**：原正向假设被证伪（方向重定位）、设计缺口仍在（方案存疑）、kd_only 择支与溯源收尾未完成（实验存疑）。总体结论 **PIVOT**（原主线），新定位 CONDITIONAL GO。

---

## 3. 证据清单

### 3.1 本地证据（L#：文件:行 / 产物名；只转抄，不重算）

| 编号 | 来源（文件:行 / 产物） | 关键事实（转抄） |
|---|---|---|
| L1 | `README.md`:7,22–25,151–165,169–173,175–184,213–222 | 实现状态/关键结果表/贡献定位/阶段状态/约束。**仍把 pre-fix `*_repro_*` 当主证据、贡献(2) 强形式、P5 条件 GO；未标 data-fix superseded/暂缓投递**（与 L14/L34/L35 不一致）。 |
| L2 | `docs/protocol.md` §1,§3.2,§4.1,§4.5,§5,§6,§7,§8,§9,§10 | RQ1–3/H1–H4；F1–F6（F5 负控不入翻转分母）；E_CF 定义+联合报告；簇级 paired bootstrap/Holm/≥3 seed/P>0.05≠等效；routing/consumption 局部恒等式（非全模型因果）；CF-RCT 与公平基线；E0–E7；决策树；预注册；§10 贡献门槛。 |
| L3 | `configs/protocol.yaml`:12–34,36–50 | primary_endpoint=paired_E_CF_difference；tau=1.0；self_threshold=0.1；cluster_paired/10000/95%/min_seeds=3/Holm；flip_denominator_excludes=[F5]（与代码 [F5,F6] 冲突，由 v2.3 裁定）；data_sizes probe40/train120/val60/test300/real0。 |
| L4 | `configs/prereg/phase1_benchmark_decision.yaml`:5–17 | distortion_present∧quality_pass→distortion_exists；no_distortion→boundary_study；forbidden_after_run（改 τ/删控制/挑 seed）。 |
| L5 | `configs/prereg/phase3_loss_config_v2.1.yaml`:37–128 | δ 标称 1.0、网格{0.5,1.0,2.0}、选择优先级（E_CF 最小→dual/flip 不劣于 kd_only→普通 QA 不退化）；E0 误差≤效应 1/3；E2 三判据（repair CI 下界>0、方向>0.5、残差≈0）；E6 deferred。 |
| L6 | `configs/prereg/phase3_loss_config_v2.2.yaml`:26–86,112–126 | δ=0.5 锁定（硬护栏，无容差）；网格 val E_CF 2.7496/1.5968/2.7625 **全部>kd_only 0.735**；预算 60对/3ep vs kd 120对/8ep；δ=0.5 压线非劣；p3_status=NO_GO。 |
| L7 | `configs/prereg/stats_convention_v2.3.yaml`:10–37 | 主聚类单元=template_family；**min_clusters_for_inference=24**，<24→exploratory 不得强显著；必报 pair-level 敏感性；flip excludes=[F5,F6]；recomputed_value=398。 |
| L8 | `docs/decisions/p0_direction.md`:11–35,88–137,178–197 | 方向 GO/证据条件 GO；主终点定义；冻结参数；mock 非证据；v2.1 冻结记录。 |
| L9 | `docs/decisions/p1_go_no_go.md`:27–84,109–122 | R1–R8；kd_only 进 P2 前必须；quality_pass=数据门 only；transfer_broken 正交注释；broken transfer 不计 H1 正向；决策树未定分支。 |
| L10 | `docs/decisions/huber_delta_lock.md`:9–52 | δ=0.5 硬护栏裁决；三 δ 均不优于 kd_only（不利事实如实记录）；预算/压线/git caveat。 |
| L11 | `docs/decisions/final_signoff.md`:50–84 | P0/P1 GO；P2 条件 GO；P3/P4 NO-GO；P5 条件 GO（boundary study）；当时仅贡献(1) 达标、(2)(3) withheld。 |
| L12 | `docs/decisions/contribution2_ruling.md`:24–62 | F1（复算缺口，投递硬门槛）/F2（单 seed，强度门槛）/F4/F6（解释边界）；限定形式可用、强形式 withheld 至 F1/F2 闭环；禁用词表。 |
| L13 | `docs/decisions/contribution2_final_form.md`:24–88 | F1/F2 闭环后**解禁贡献(2) 强形式**，附 4 强制条件（MVP 等深对限定、禁 causal/sole cause/across pairs、强制披露 F4/F6+第5单元漂移、贡献(3) withheld）；定位仍 boundary study。 |
| L14 | `docs/decisions/data_readiness_ruling.md`:9–59,83–110 | **数据正确性缺陷必须先修**（18 退化对、≥15 跨 split 泄漏含 train↔test 整对、实体全共享、簇退化、flip 394vs457）；**暂停 P3 正式 test run**；**暂缓投递**；P1/P2 干净重跑；M1–M9；外部效度缺口可披露。 |
| L15 | `docs/decisions/p3_task_plan.md`:12–31,87–128,159–165 | 分阶段门控（烟测→kd vs cf_lite 2×3seed→门控决定 cf_mech）；接受 no_method_gain；主终点=封存 test vs kd_only 成对 E_CF CI 上界<0；串行；60min 熔断；判据变更禁令。 |
| L16 | `reports/data/data_readiness_audit.md`:76–153,159–184 | 独立审计：§2.2 train/test 模板骨架 100% 重合（"未见模板"仅后缀）；§2.3 实体全共享 + train↔test 整对泄漏；§2.4 18 退化对（test7）；§3.1 簇退化（300 唯一簇/仅 8 结构）→CI 偏窄；§4 22 run 无一在 test 评测；§5 投稿前不达标。 |
| L17 | `reports/data/data_fix_report.md`:8–19,60–110 | M1/M2/M3/M5/M7′ 完成；退化 18→0、泄漏≥15→0、实体重叠→0、结构 8→24/族 40→56、真正未见 32族/16结构、train/test 骨架∅、flip 398；验收 11/11；新 sha f910f1f1；M4 仅计划；**旧 run 溯源过期须重跑**；§5.4 称"族数达24可脱离exploratory"（**与 test=16 族矛盾，见风险 M-2**）。 |
| L18 | `reports/data/acceptance_checks.json`:1–30 | 11 项独立验收全过：cross_split_overlap=0、degenerate=0、skeleton_disjoint、flip 398、deterministic_rebuild、v2.3 sha 一致。**未检查 test 簇数≥24**。 |
| L19 | `data/tasks/manifest.json`:2–34,97–104,168–175 | cf_pairs_v2.1；CC0/synthetic/real=0；**template_family_count_by_split: probe16/train16/val8/test16**；structural_template_count=24；total_families=56；limitations（合成、real=0、F5 长度分层、未见仅 test/probe）。 |
| L20 | `docs/data/data_card.md`:34–35,55–84 | 8 已见 S-*（train/val）+16 未见 U-*（test/probe）；实体池按 split 不相交（每 split 8 个）；length_mismatch 61 全 F5；flip 398；限制：合成域、real=0、每 split 8 实体、旧 run 溯源过期、旧数据每 run 仅 8 族→exploratory。 |
| L21 | `reports/runs/e0_gpu_mvp_repro_seed0`（via L28/L31 §2.1） | E0 PASS：cosine1.0/KL0/EM1.0(80/80)/round-trip bit-identical/zero-re-prefill80/80；误差上限 2.2e-16≪效应/3=6.95；commit 458de18。**pre-fix 数据**。 |
| L22 | `reports/runs/p1_gpu_mvp_repro_seed{0,1,2}/metrics.json`（via L26/L28/L31 §2.2） | joint E_CF **1.968/1.934/2.123**，CI 下界>0；dual 0.667/0.650/0.617；flip 0.938/0.898/0.958；coverage 0.80/0.817/0.80；transfer_broken=false；info_attribution(seed0) mismatch+4.134/random+2.249/zero+4.191。**pre-fix，已 superseded**。 |
| L23 | `reports/runs/p1_gpu_kdonly_mvp_seed{0,1_par,2_fast}`（via L26/L31 §3.2/§8） | kd_only E_CF **0.735/1.034/1.539**，CI 下界 0.552/0.766/1.148>0；dual 0.700/0.633/0.683；flip 1.0/1.0/0.979；transfer_broken=false；相对 affine 缩小 22–63% 但未消除；跨 seed 幅度不稳定。**pre-fix，已 superseded**。 |
| L24 | `reports/runs/delta_lock_v2p1_{0p5,1p0_par,2p0_par}`（via L6/L26/L31 §9） | val joint E_CF 2.7496/1.5968/2.7625；dual 0.70/0.65/0.533；flip 1.0/1.0/0.958；三 δ 均>kd 0.735；60对/3ep。**pre-fix**。 |
| L25 | `reports/runs/p2_gpu_mvp_seed{0_delta_rand_audit,1,2}`（via L26/L31 §10–11/L32） | 四臂 Self0/K-only0.582/V-only1.626/Joint1.777（仅 Joint deployable）；分解 17920 单元残差 2.96e-13；repair 0.275/0.275/0.350，CI[0.150,0.425]/[0.125,0.425]/[0.200,0.500] 下界>0；命中 0.725/0.725/0.750；4/5 核心单元(12,5,V/both)(25,4,V/both)跨3seed重合、第5漂移；mechanism_predictive；commit 6784780。**pre-fix，已 superseded**。 |
| L26 | `reports/bootstrap_summary.json`（全文） | 从 scores.jsonl 重算 CI 与 metrics 一致；**所有 P1 run primary_endpoint point=0/ci[0,0]/improved=false**（自比基线，正确）；P2 repair_vs_random 0.275/0.275/0.35 CI 下界>0。**pre-v2.3 格式：无 pair-level 敏感性、无 exploratory 标记、不含 clean run**。 |
| L27 | `reports/consistency_report.json`（全文） | 权威 run ok=true（code_tracked/git in history/run_code unchanged/model_pair ok）；8 superseded fail；head=**6784780**。**不含 e0_clean/p1_clean（git efc3ba3）**。 |
| L28 | `reports/runs_index.json` + `runs_index_errata.json` | 22 run；superseded 标记；model_pair_corrected=qwen3-4b-to-1.7b（teacher 路径+36→28 layer_map）。**不含 clean run**。 |
| L29 | `reports/runs/e0_clean_mvp_seed0/metrics.json`:1–23,117–139 | **干净数据 E0 PASS**：min_logit_cosine1.0/KL0/round_trip ok/误差上限 2.22e-16/效应 23.88/容差 7.96；em_agreement0.975；one_shot_min_cosine0.9991（sdpa 路径差异）；zero_re_prefill_all=true；release_to_P1=true。git efc3ba3（见 config）。 |
| L30 | `reports/runs/p1_clean_mvp_seed0/metrics.json`:134–419 + `config.json`:1–57 | **干净数据 P1 seed0（affine，val60）**：joint E_CF **6.8996 [5.4985,8.3134]**；dual **0.4167** vs Self **0.8167**；flip **0.75**；coverage0.8667；info_attribution mismatch+1.483/**random−0.135**/zero+1.684；**transfer_broken=true**（joint_dual_drop_vs_self=0.4≥0.2）；verdict_note="failure boundary, NOT positive evidence of utility-preserving distortion"；冻结 verdict 仍 distortion_exists（正交注释不改）；detail.evaluable_threshold=**0.001**（元数据误标，实际逐对用 0.1，见 L37）；CI 为 pair-level（cluster 逐对唯一，见 L38/L39）；git_hash=**efc3ba3**；eval_splits=["val"]；created 2026-11-23T10:36。**[二轮更新] 本行"仅 seed0、未审计/索引"已过期：seed0 已入 v2.3 审计（ok=true、exploratory、template CI [3.564,10.100]）；affine 三 seed 齐全见 L45/L46。** |
| L31 | `reports/engineer_status.md` §2,§3,§9,§10,§11,§12 | R1 闭环 458de18；repro/kd/δ/P2 数值；F1/F2/F5 闭环；**§12 P3 暂停**（数据缺陷，无任何正式 P3 test run，唯一 P3 产物为 _non_authoritative smoke）；实现 P3_gpu.py+可微 readout commit 885a36a→ee74382。 |
| L32 | `reports/review/p2_f1f2_closure_review.md`:21–92,122–142 | F1 独立逐对重算 point0.275 CI[0.150,0.425] 下界>0（命中率差，非连续量）；F2 三 seed 复算一致、4/5 核心单元、第5漂移如实；F5 smoke 移出；prereg v2.1/v2.2 git diff 空。**基于 pre-fix 数据**。 |
| L33 | `reports/review/stage_p1_review.md` + `stage_p1_review_round2.md`（via L9/L11） | 第1轮 R1 阻塞+R2/R3/R4 主要+R5–R8 次要；第2轮 R1 闭环、7 权威 run ok；PI 直裁。 |
| L34 | `papers/readkv_v2_draft/main.tex`:14–35,430–502,600–607,739–744,981–988,1007–1014 | 内部注记+§4.2 datafix 表+§5 superseded/under re-run 通知+§5.3 P2 superseded+投稿暂缓声明；贡献(1)+(2) 强形式（MVP 限定）、(3) withheld；**bibliography 仅 KV-Lingo/CacheLink 两个 [PLACEHOLDER]**，未引 Heo/CacheBridge/"Does Accuracy Equal Evidence?"/Contrast Sets/FaithEval。 |
| L35 | `papers/readkv_v2_draft/notes.md`:17–33,37–52 | 数据修复披露轮：所有 pre-fix 数值标 superseded/under re-run；v2.3 冻结；重跑进行中；M4 仅计划；投递暂缓；贡献(2) 强形式在新证据到位前**条件性成立**；主终点未评估。 |
| L36 | `reports/p3_smoke_report.md`:20–45 + `reports/_non_authoritative/p3_smoke_cflite_seed0/` | 烟测 PASS（梯度 448/448、学生梯度0、loss1.2254→0 属8对过拟合非证据、test=0 不读封存标签、non_authoritative=true）。**非权威，不作证据**。 |
| L37 | `src/readkv/evaluate/counterfactual.py`:134,147,212,223,243 | PairCFRecord.self_threshold 默认 1e-3，但 cf_pipeline 传 cfg.self_threshold=0.1 → 逐对 evaluable 用 0.1；summarize_cf 默认 self_threshold=1e-3，用 r.get("evaluable")（存在→沿用0.1子集），但 detail.evaluable_threshold 报告默认 1e-3（**误标**）；若记录缺 evaluable 键则静默用 1e-3。 |
| L38 | `src/readkv/evaluate/cf_pipeline.py`:203,245,261–265 | summarize_cf 调用**未传 self_threshold**（用默认1e-3做detail标签）；CI 用 record 的 "cluster" 字段。 |
| L39 | `src/readkv/data/build_cf_pairs.py`:457 | `cluster = f"{split}-{template.family}-{pair_id[-3:]}"` → **逐对唯一**（修复后仍如此）；故 pipeline metrics.json 的簇 bootstrap 实为 pair-level。 |
| L40 | `scripts/bootstrap_ci_report.py`:7–9,29–73,167–168 | v2.3 改造：主 CI 按 template_family + pair-level 敏感性 + n_clusters<24 标 exploratory；旧产物无 template_family 时标 cluster-fallback。**只有此脚本产出 v2.3 合规 CI**；reports/bootstrap_summary.json 仍是改造前旧输出。 |
| L41 | `docs/algorithm_spec.md`:9–17,39–111 | CF-RCT 设计（L_KD/L_CF/L_local/L_reg）；Oracle 隔离；容量逐级；L_CF 仅 Self 有效子集；mech>lite 且>最强基线才可写机制创新。**设计待验证**。 |
| L42 | `docs/experiment_design_E0_E7.md`:25–31,47–56,72–90 | E0–E7 矩阵；公平比较要求同预算/参数/Forward；基线清单 affine/consumer/kd_only/score/ridge + KV-Lingo/CacheLink；E1 要求强基线族；E3 主终点封存 test。 |
| L43 | `reports/environment.json`:1–14 | Python3.13.11/torch2.15.0+cu132/transformers5.24.0/CUDA13.2/RTX4090/bf16/sdpa；Qwen3-0.6B/1.7B 本地路径。 |
| L44 | `configs/eval.yaml`:5–20 | tau1.0/self_threshold0.1；primary_baseline=kd_only；mapper_baselines affine/consumer/kd_only/score；model_pairs mvp/main/stress。 |

> **[二轮证据状态更新]** 一轮 L26/L27/L28/L30/L34/L35 的部分状态已被新产物超越，以 §8.2 新增证据 **L45–L53** 为准：`bootstrap_summary.json` 已重生成 v2.3（26 run，含 e0_clean+p1_clean×3，template-family CI+pair 敏感性+exploratory；**不含 p1_kd_clean**）；`consistency_report.json` 已重生成（head efc3ba3，clean run ok=true，旧 repro 458de18 因 HEAD 前进转 ok=false）；`main.tex`/`notes.md` 已按翻转裁决重写（贡献1/2 withdrawn）；`README`/`engineer_status`/`runs_index` 仍过期（S3）。`p1_clean_mvp_seed{1,2}` 与 `p1_kd_clean_mvp_seed0` 见 L45/L46/L49。

### 3.2 网络证据（W#：标题 / URL / 访问日期 / 关键论断 / 一手·二手）

> 访问日期均为 **2026-11-23**。一手 = 论文原文/arXiv/官方 proceedings/官方数据集仓库；二手 = 博客/解读/社交媒体（仅作线索，不作论断依据）。

| 编号 | 标题 / 作者 / 年份 | URL | 关键论断（对本课题的意义） | 一手/二手 |
|---|---|---|---|---|
| W1 | KV-Lingo: Learning KV-Cache Translators with Distillation / Castin, Sakamoto, Filippova, Monteiro, Cuturi, Ablin（Apple）/ 2026-09-26 | https://arxiv.org/abs/2609.32610 | 逐层线性映射，用蒸馏最小化"目标模型原生缓存预测 vs 翻译缓存预测"的散度；双模型冻结；zero re-prefill；Qwen 对；TTFT 降 9.6×（64token）–29×（32k）。**= 本课题 kd_only 基线的公开原型；确认 kd_only 是真实强基线，但只是 KV-Lingo 式行为蒸馏的简化实例。** | 一手（arXiv abs） |
| W2 | CacheLink: Functional KV Transport for Zero-Prefill Cross-Model Context Handoff / Qiu, Tang, Song, Han, Qiao, Zhang（HIT Shenzhen / Great Bay / ZJU）/ 2026-10-11 | https://arxiv.org/abs/2610.15509 ；全文 https://arxiv.org/html/2610.15509v1 | **§4 "重构保真不决定接收端效用"**：Obs1 更低 K/V 重构误差不意味更高效用；Obs2 功能变化与平方误差移动解耦；Obs3 K/V 共享 latent origin 须联合校正。**§4.3 四臂 source-swap RR/NR/RN/NN 诊断**（= 本课题 Self/K-only/V-only/Joint 四臂的公开先例），"只换 K 或只换 V 不一致改善"。**§3.1 K 路由概率质量 / V 决定沿路由返回的信息**（= routing/consumption 概念先例）。**§5 功能监督 = continuation CE + forward KL 经冻结接收端，无重构损失**（= L_KD；接近 CF-RCT-mech 的功能目标）。4 对（Qwen3-14B→32B/8B→14B、Ministral-3-8B→14B、Yi-1.5-9B→34B）×7 真实面板（SciQ/MMLU-Pro/MMLU-Pro-Plus/OpenBookQA/Oolong-Synth32K/LongBench-v2/BABILong32K）；胜 Ridge 26/28；7.27× 延迟。**未做成对反事实文档编辑 E_CF 主终点**。**→ 严重 anticipate 本课题机制层(贡献2)与功能目标；本课题须正面引用并区分"成对反事实响应保真"vs"单上下文功能/效用"。** | 一手（arXiv abs + HTML 全文） |
| W3 | Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse / Heo, Shafipour, Zhao, Golub, Kamani, Borkar, Chandran, Zardoshti, Rouhani / 2026-08-04（被引20） | https://arxiv.org/abs/2608.03893 | 闭式 per-head ridge + top-k 源层 + de-RoPE + 500×1024 FineWeb-Edu 校准；6 对中 4 对保留 73–98% 独立 prefill 准确率，**2 对急剧退化**；非线性 MLP 在失败对恢复 +37pp HellaSwag；2.7–25× 加速。**= 本课题 affine/ridge 基线的公开原型；"部分对迁移失败"是已知现象（与本课题 clean MVP 坍塌、main 对 broken transfer 一致）；用真实基准（HellaSwag/FineWeb-Edu），本课题 real=0 无外部锚点处劣势。** | 一手（arXiv abs） |
| W4 | Does Accuracy Equal Evidence? Reasoning Faithfulness under KV Cache Compression / Ai, He, Guo / 2026-08-03（v2 2026-10-24），EMNLP 2026 Findings（被引5） | https://arxiv.org/abs/2608.01631 | KV **压缩**下"答案-证据 gap"：token-eviction 可保持最终准确率却大幅降低 chain support / perturbation faithfulness；fixed-trace replay 协议；10 eviction+1 quantization×3 模型。**→ 本课题 H1 前提（高常规分≠反事实保真）在压缩 setting 已被公开提出；本课题须引用并区分"跨模型迁移 + 成对反事实 E_CF"vs"压缩 + 推理链保真"。** | 一手（arXiv abs） |
| W5 | Evaluating Models' Local Decision Boundaries via Contrast Sets / Gardner et al. / Findings EMNLP 2020 | https://arxiv.org/abs/2004.02709 ；https://aclanthology.org/2020.findings-emnlp.117/ | 专家最小编辑改变 gold label，构造 contrast set 评 contrast consistency；10 数据集；模型在 contrast set 上最多降 25%。**= 本课题成对反事实文档（F1–F4 翻转、F5 不翻转负控）的方法学先例；E_CF 是 contrast consistency 的连续 logit 差版本在迁移 setting 的适配。评价设计本身非原创。** | 一手（arXiv + ACL proceedings） |
| W6 | Learning the Difference that Makes a Difference with Counterfactually-Augmented Data / Kaushik, Hovy, Lipton / ICLR 2020 | https://arxiv.org/abs/1909.12434 ；https://github.com/acmi-lab/counterfactually-augmented-data | 反事实增强降低伪模式依赖。**反事实评测/构造的第二独立来源（与 W5 交叉验证"成对反事实评测已确立"）。** | 一手（arXiv + 官方仓库） |
| W7 | FaithEval: Can Your Language Model Stay Faithful to Context, Even If "The Moon is Made of Marshmallows" / Ming et al.（Salesforce）/ 2024 | https://github.com/SalesforceAIResearch/FaithEval | 反事实上下文（违背常识/世界知识）下评模型是否忠于上下文。**反事实上下文保真评测的先例（within-model，非迁移）；与本课题"学生是否跟随被编辑文档"相关但 setting 不同。** | 一手（官方仓库） |
| W8 | Qwen3 Technical Report / Qwen Team / 2025；Qwen3-1.7B 模型卡 | https://arxiv.org/abs/2505.09388 ；https://huggingface.co/Qwen/Qwen3-1.7B | 0.6B：28层/16Q/8KV/head_dim128/tied emb/32K；1.7B：28层/16Q/8KV；4B：36层/32Q/8KV/128K；QK-norm。**核实本课题 MVP 28→28 等深、main 36→28 非等深、GQA 8 KV 头、QK-Norm 的模型配置主张属实。** | 一手（arXiv + 官方模型卡） |
| W9 | Bootstrap-Based Improvements for Inference with Clustered Errors / Cameron, Gelbach, Miller / REStat 2008（NBER t0344，被引7099）；Canay 2021 wild bootstrap；MacKinnon & Webb few treated clusters | https://www.nber.org/system/files/working_papers/t0344/t0344.pdf ；https://home.uchicago.edu/amshaikh/webfiles/wild.pdf ；http://qed.econ.queensu.ca/pub/faculty/mackinnon/working-papers/qed_wp_1364.pdf | 少簇（可少至6）下 wild cluster bootstrap-t 优于普通簇 bootstrap/CRSE；百分位簇 bootstrap 在少簇时可能过度拒绝。**→ 本课题 val8/test16 模板族属少簇，v2.3 百分位簇 bootstrap 覆盖存疑；建议补 wild cluster bootstrap-t 敏感性（若改冻结口径需 PI 新增版本）。** | 一手（期刊/工作论文原文） |
| W10 | A Simple Sequentially Rejective Multiple Test Procedure / Holm / Scand J Statist 1979;6:65–70 | https://www.jstor.org/stable/4615733 | 逐步拒绝 Bonferroni，控制 FWER。**核实本课题 Holm 多重比较为标准正确做法。** | 一手（期刊原文/权威索引） |
| W11 | HellaSwag / Zellers et al. ACL 2019（官方页 + EleutherAI lm-eval-harness）；ARC / Clark et al. 2018；SQuAD / Rajpurkar et al. 2016/2018 | https://rowanzellers.com/hellaswag/ ；https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/tasks/hellaswag/README.md | HellaSwag 官方 acc/acc_norm；lm-eval-harness 标准评测。**M4 外部锚点候选；Heo(W3)/CacheLink(W2) 已用真实基准。注：本次仅直接抓取 HellaSwag 官方页/harness；ARC/SQuAD 为通用标准引用，未逐一抓取官方页（标注：未核实官方页细节）。** | 一手（HellaSwag 官方/harness）；ARC/SQuAD 二手常识（未逐一抓取） |
| W12 | CacheBridge / Qu et al. 2026（arXiv 2609.00891）；KVPort（NeurIPS 2026）；Prefill-Free Cross-Family KV Cache Transfer（arXiv 2609.32259）；LatentAlign / Dery et al.（arXiv 2601.06123）；Cache-to-Cache / Fu et al.（ICLR 2026） | 经 W1/W2 参考文献与搜索结果确认：https://arxiv.org/abs/2609.00891 ；https://neurips.cc/virtual/2026/171250 ；https://huggingface.co/papers/2609.32259 | 跨模型 KV 迁移是 2026 活跃研究线（闭式/功能/共享latent/跨tokenizer/缓存融合多路线）。**交叉验证"跨模型 KV 迁移已确立"（≥2 独立来源：W1+W2+W3+W12）。注：W12 各条经一手文献 bibliography 确认存在，未逐一抓取全文（标注：存在性一手交叉确认，细节未核实）。** | 一手交叉确认（bibliography）；细节二手 |
| W13 | 检索 "Cache Translation Across Model Scale" / "Beyond Representation Fidelity" | websearch（无公开结果） | **未找到公开版本** → 本课题两篇基础论文为内部/未公开 PDF（docs/raw）；公开对应物为 Heo(W3)/CacheLink(W2)。"第三篇系列论文"定位依赖未公开前作。**不确定性：可能以不同标题/venue 存在；阴性检索结果不等于不存在。** | 阴性检索（不确定） |

---

## 4. 风险排序与可执行建议

> 标注 **[需 PI 新增版本]** 者涉及冻结判据/口径，不得自行修改，须 PI 走新增版本流程。其余为执行/文档/设计建议，不改判据。
>
> **[二轮修订指针]** B-1/B-2/B-3/M-4 已就地更新；**M-1/M-2/M-3/M-5 与 m-1..m-5 的二轮状态、以及紧急复核新增风险 S1/S2/S3，见 §8.4 逐条修订对照表**（P3 取消后 M-1/M-2/M-3 对当前负面定位阻塞性降低；S2 v2.3 哈希不一致为新增主要级溯源风险）。

### 4.1 阻塞级（Blocking）——不解决则不得投稿/不得写正向贡献主张

- **B-1｜[二轮修订：已部分闭环并升级为 PIVOT 依据] 干净数据 affine 失败边界已确证；原正向贡献已由 PI 撤回；kd_only 择支待决。**
  - 事实（更新）：affine 三 seed 干净重跑齐全（L45/L46/L30），**全部 transfer_broken=true**（joint E_CF 6.900/8.159/8.540、dual 0.417/0.283/0.383 vs Self 0.817/0.900/0.783），已入 v2.3 审计（L50/L51，ok=true、exploratory、template CI 下界均>0）；紧急复核（L48）判**翻转可信·高·非实现 bug**。**PI 已裁定（L47）贡献(1) 冻结降级、贡献(2) 立即撤回 withheld（不等 P2）、P2/P3 取消**。一轮"clean 仅 seed0、kd/P2 均缺、贡献尚未成立"已被超越：正向证据基础**已塌陷并撤回**，不再是"待重建"。
  - 剩余动作：完成 **clean kd_only 三 seed**（seed0 已落盘 L49：not broken、dual 0.70、E_CF 6.388 大 gap；seed1/2 未产出、未审计），按 PI §3.3 预承诺 A/B/C 择支；闭环 S1–S3 溯源。**不再补 P2/P3**（PI 取消）。
  - 判据：不改冻结判据；机器 verdict 仍 distortion_exists，科学定性以正交 transfer_broken 为准（L47 §3.1）。**PIVOT 已由 PI 裁定、本顾问同意**；kd_only 最终择支属 PI，本结论不覆盖。

- **B-2｜[二轮修订：affine clean 已审计；kd_clean 未审计；索引仍缺] 审计/索引部分闭环。**
  - 事实（更新）：`bootstrap_summary.json` 已重生成 v2.3（L50，26 run，含 e0_clean+p1_clean×3，template-family 主 CI+pair 敏感性+exploratory=true 8 簇）；`consistency_report.json` 已重生成（L51，head efc3ba3，clean run ok=true）。**但 `p1_kd_clean_mvp_seed0`（git 6413ba0，11:01 落盘）尚未入 bootstrap_summary/consistency_report/runs_index**；`runs_index.json`/errata 仍未纳入任何 clean run、旧 repro 未标 superseded（紧急复核 S3）。pipeline metrics.json CI 仍 pair-level（L38/L39），v2.3 主 CI 以审计脚本输出为准。
  - 建议：审稿人对 **kd_clean seed0（及后续 seed1/2）** 重跑 bootstrap_ci_report+consistency_check（git 6413ba0 ancestry/跑分代码一致）；工程师更新 runs_index/errata（纳入 clean run、旧 run 标 superseded）；闭环 S1（数据哈希 f910f1f1 入 run 产物 metadata）。**下游不得把 metrics.json pair-level CI 当 v2.3 主 CI**。
  - 判据：不改判据；属审计/索引补全。

- **B-3｜[二轮修订：正向措辞已撤回；引用核验/engage 仍为投稿前必做] 相关工作与新颖性限定。**
  - 事实（更新）：main.tex 已按 PI 裁决重写（L52），**贡献(1)/(2) 正向措辞已 withdrawn**（"We identify a reproducible gap…"/"We localize…V-consumption…" 已删除），一轮"de novo 机制定位过宽"风险已消除。但 bibliography 仍须核验：KV-Lingo(W1)/CacheLink(W2) 正式版本/日期/口径（protocol §9），并补引 Heo(W3)/"Does Accuracy Equal Evidence?"(W4)/Contrast Sets(W5)/Kaushik(W6)/FaithEval(W7)/CacheBridge(W12)/**Kapoor-Narayanan(W14)**。
  - 建议：新定位（失败边界 + 数据泄漏教训）的新颖性须**正面限定**：①泄漏制造虚假发现的一般教训已确立（W14，17 领域 294 篇），本课题贡献是**具体预注册翻转案例 + 完整审计轨迹 + E_CF 成对反事实框架**，非一般教训本身；②affine 迁移失败与 Heo(W3)"2/6 对急剧退化"一致，须区分"已知失败现象"vs"本课题在受控反事实基准上的量化 + 泄漏归因"；③E_CF 评价框架须区分于 CacheLink(W2) 单上下文功能/效用（W2 未做 E_CF）与 W4 压缩 answer-evidence gap。
  - 判据：不改判据；属 §9 引用核验 + §10 措辞门槛（现为负面结果措辞）。**任何残留正向机制/方法/gap 措辞一律删除（PI 裁决 L47 §4.1）。**

### 4.2 主要级（Major）——显著削弱证据强度/可发表性，须修复或诚实降级

- **M-1｜test 簇数 16 < v2.3 min_clusters 24，主终点确认性门槛按现设计不可达。**
  - 事实：v2.3 min_clusters_for_inference=24（L7）；manifest test template_family=16、val=8（L19）；protocol §3.3 建议封存 test ≥24 独立簇。bootstrap 在 test 上重采样 16 个族 → n_clusters=16<24 → **exploratory=true**，不得强显著。`data_fix_report §5.4`（L17）称"族数达24可脱离exploratory"**混淆了 corpus-wide structural_template_count=24 与 per-split test 簇数=16**，属错误/过度乐观。acceptance_checks（L18）未检查 test 簇数≥24。
  - 建议：**[需 PI 新增版本]** 由 PI 澄清 min_clusters 的适用口径（按评测 split 的实际簇数），并二选一：（a）扩充 test 至 ≥24 个结构不同模板族（数据重建 + manifest 重冻结 + 重跑），或（b）接受主终点 exploratory 定位并相应降级贡献(3) 措辞（贡献(3) 已 withheld，影响可控）。同时修正 data_fix_report §5.4 的错误表述（报告层，不碰冻结产物）。
  - 影响：即便 B-1 补齐，主终点"CI 上界<0"的**确认性**主张在 16 簇下仍只能探索性；少簇百分位 bootstrap 覆盖存疑（W9）。

- **M-2｜少簇（val8/test16）下百分位簇 bootstrap 覆盖存疑。**
  - 事实：v2.3 用 template_family 簇级 paired bootstrap（百分位）；W9（Cameron-Gelbach-Miller 2008 / Canay 2021 / MacKinnon-Webb）表明少簇下 wild cluster bootstrap-t 更稳健，百分位法可能过度拒绝。pre-fix 每 run 仅 8 族，clean val 仍 8 族。
  - 建议：**[需 PI 新增版本]** 若纳入正式推断口径，补 wild cluster bootstrap-t 作为敏感性（与 v2.3 pair-level 敏感性并列）；不改 v2.3 主口径，仅新增版本登记附加敏感性。当前先按 exploratory 措辞。

- **M-3｜强基线族不完整，"最强行为基线"主张证据不足。**
  - 事实：E1/§7（L42）要求 affine/consumer/kd_only/score/ridge + CE/contrastive/receiver-only + KV-Lingo/CacheLink；实际只跑 affine（P1）+ kd_only（P1）。consumer/score/ridge/CE/contrastive/receiver-only **从未跑**；CacheLink(W2) 是已发表的更强功能基线，未实现未比较。kd_only 只是 KV-Lingo(W1) 式简化。
  - 建议：科学家补设计——至少补 consumer/score/ridge（协议已列）；**若重启 P3，把 CacheLink(W2) 列为方法层更强公共基线**（其 CE+KL 功能监督 + 耦合 K/V 残差接近 CF-RCT-mech，是 CF-RCT 新颖性的直接对照）。贡献(1)"gap 未被强基线消除"须限定为"已测 affine/kd_only 范围"（main.tex 已如此限定，保持）。
  - 判据：补基线属实验设计扩展，不改冻结判据；若改变 `primary_baseline` 或比较清单口径 → **[需 PI 新增版本]**。

- **M-4｜[二轮修订] 文档一致性：main.tex/notes.md 已重写，README/engineer_status/runs_index 仍过期。**
  - 事实（更新）：main.tex/notes.md 已按 PI 翻转裁决**整体重写**（L52：贡献1/2 withdrawn、Table cleanmvp/reversal、kd_only PENDING、机制图不画、负面定位）。**但 README（L1/L53）仍 22 run、无翻转/撤回/暂缓；engineer_status（L53）无翻转章节；runs_index（L53/S3）未纳入 clean run、旧 repro 未标 superseded**。
  - 建议：doc-engineer 同步 README/engineer_status 至 PI 翻转裁决状态（贡献1/2 撤回、affine 三 seed 失败边界、kd_only 择支待决、P2/P3 取消、投稿暂缓）；工程师更新 runs_index/errata（S3）。**不改判据/产物**，仅文档/索引同步。

- **M-5｜合成域窄 + real=0 + 无外部锚点，外部效度不足。**
  - 事实：每 split 仅 8 实体（L20）、24 基础结构、real=0（L19）；Heo(W3)/CacheLink(W2) 均用真实基准（HellaSwag/FineWeb-Edu/SciQ/MMLU-Pro/LongBench-v2/BABILong）。clean MVP affine 坍塌可能部分反映"闭式 ridge 在未见实体上难泛化"的合成域特性，而非普适迁移失败（见 §5 反面证据）。
  - 建议：M4 真实文档（80–150 对，许可预评估）尽早启动（需人工/PI 决策）；或至少接入 HellaSwag/ARC/SQuAD 合规子集作外部锚点（W11），把 E_CF 成对构造适配到真实文档。当前作为 limitation 诚实披露（main.tex 已披露）。

### 4.3 次要级（Minor）——不阻塞，但须修正/披露

- **m-1｜self_threshold 元数据误标 + summarize_cf 默认值不一致。**
  - 事实：clean metrics.json detail.evaluable_threshold=**0.001**（L30），但逐对 evaluable 实际用 cfg.self_threshold=**0.1**（L37/L38）；summarize_cf 默认 1e-3，若记录缺 evaluable 键会静默用错阈值。当前子集计算正确（用逐对 evaluable），但**元数据标签误导审计**。
  - 建议：工程师把 summarize_cf 的 detail.evaluable_threshold 改为实际传入阈值（或显式传 cfg.self_threshold），并加断言/测试防止缺键时静默用 1e-3。不改冻结 self_threshold=0.1。属实现一致性修正。

- **m-2｜data_card §6 称 v2.3 recomputed_value "当前为 null"，实际已回填 398。**
  - 事实：data_card（L20）§6 待 PI 回填 null；但 stats_convention_v2.3.yaml:31 已 recomputed_value=398（L7）。文档轻微过期。
  - 建议：doc-engineer 同步 data_card。不碰冻结文件。

- **m-3｜E0 效应尺度与主终点尺度不同 + one-shot kernel 残差。**
  - 事实：E0 效应用多 token logprob（clean 23.88，L29）vs 主终点 2 维 logit；one_shot_min_cosine 0.9991（sdpa 路径差异，非实现误差）；误差上限 2.2e-16 极小不影响判定。已披露（L34/main.tex）。
  - 建议：保持披露；无需改判据。

- **m-4｜δ 网格 git hash 为启动时 HEAD（ff578b5/a04990d），按 ancestry+代码一致口径审计。**
  - 事实：L6/L10/L31 §9 已披露；consistency_check ok=true（L27）。属 R1 口径，已闭环。
  - 建议：clean 重跑务必避免 R1 重演（git_hash 指向含全部跑分代码且 clean 的 commit）；clean run git efc3ba3 须按同口径审计（B-2）。

- **m-5｜smoke / _non_authoritative 产物可能被后台 agent 继续写入。**
  - 事实：任务提示 reports/_non_authoritative/**、p3_smoke_report.md 可能仍在写。L36 smoke 已标 non_authoritative、test=0。
  - 建议：始终视为未定稿/非权威，不纳入任何结论；正式 P3 须待数据修复+审计后按 p3_task_plan 门控重启。

---

## 5. 不确定性与失效条件

### 5.1 当前证据无法回答的问题 [二轮修订]
1. **kd_only 最终择支（A/B/C）未定。** 决定性证据 = clean kd_only 三 seed。**seed0 已落盘**（L49：transfer_broken=false、dual 0.70 vs Self 0.817、E_CF 6.388 [5.360,7.400] 大 gap、info 全正）——**既非纯 A（kd 也 broken）亦非纯 B（kd not broken 且 E_CF 小且近 Self）**，最接近 PI 预承诺情形 C（not broken 但仍有 gap），**但 gap 不"小"**（6.39，normalized 0.585，远大于 0）。**seed1/2 未产出、seed0 未审计**，最终 A/B/C 属 PI（须三 seed+审计；若 PI 欲把"not broken+大 gap"单独处理须新增版本澄清 §3.3 字面）。**不推测 seed1/2 结果。**
2. **affine 失败边界是普适还是合成域/闭式 ridge 特例？** 已确证 affine 三 seed 在干净合成域坍塌；Heo(W3) 闭式 ridge 在真实域 4/6 对成功 → 坍塌未必普适，可能反映"120 对校准+未见实体+窄合成域"下闭式 ridge 难泛化。kd seed0 not broken（dual 0.70）部分支持"训练型基线比闭式 affine 更能泛化"，但需三 seed+真实锚点（M-5）确认。
3. **贡献(2) 机制定位：已由 PI 撤回，不再重跑 P2。** 一轮"clean P2 三 seed 待补"已被 PI 取消（L47 §2：机制对象"干净失真"不存在，旧 P2 建立在污染数据上不可信）。**不再追问 clean P2 复现**；机制主张永久撤回（除非日后重新构造出干净失真数据另立问题）。
4. **主终点确认性：P3 已取消，主终点不再评估。** test 16 簇<24（M-1）的口径张力对当前负面定位阻塞性降低（不再追求方法增益确认性），但若日后重启方法层仍须解决。
5. **两篇基础论文是否公开？** W13 阴性检索，公开对应物为 W2/W3；"系列第三篇"定位依赖未公开前作（不确定）。
6. **[新增] kd seed0"not broken+大 E_CF gap"是否构成 kd_only 自身的效用-保真解离信号？** 科学上值得注意（dual/flip 近 Self 但 E_CF 6.39≫0），但单 seed、未审计、exploratory，且 PI 预承诺情形 C 明确"仍不足以支撑贡献(1)"。**是否据此调整叙事属 PI，本顾问不擅自升格为 H1 复活。**

### 5.2 推翻/调整本次结论（PIVOT）的前提变化 [二轮修订]
- **[已发生，非未来触发] affine 三 seed 坍塌 + PI 裁决 → 原主线 PIVOT 已成立。** 一轮预设的触发条件"clean kd_only 三 seed 仍 broken 才 PIVOT"**过窄且已被超越**：实际 PIVOT 路径是 affine 臂三 seed 确证坍塌 + PI 科学判定"原 utility-preserving gap 框架失去证据基础"，**不依赖 kd_only 也 broken**。kd seed0 反而 not broken，但原贡献(1)（围绕 affine/ridge gap）仍不成立。
- **kd_only 三 seed 择支（待决，属 PI §3.3 预承诺）**：A（kd 也 broken）→ 纯失败边界；B（kd not broken 且 E_CF 小近 Self）→"泄漏制造虚假 gap"方法学负面结果；C（kd not broken 但仍有 gap）→ 边界研究，贡献(1) 仍不复活。**seed0 呈 not broken+大 gap（C 类但 gap 不"小"）**，最终归类待三 seed+审计+PI（必要时新增版本澄清"小 gap"字面）。**无论 A/B/C，贡献(3)/方法层均不成立（PI 预承诺）。**
- **若紧急复核被推翻（判定为实现 bug）** → PI 裁决 §5 规定立即停冻结、工程修复后重跑；当前复核判**非 bug（高可信）**，故 PIVOT 维持。
- **若发现 clean run 读了封存 test / 挑 seed / 改判据** → 升级 NO-GO（学术诚信）。当前**未见**（clean config eval_splits=["val"]，L30/L49；冻结判据 git diff 空，L48；v2.3 sha 不一致属 S2 溯源待澄清，非按测试改判据证据）。
- **若 PI 扩 test ≥24 簇 / 纳入 wild bootstrap-t / 变更基线清单** → 须新增版本；对当前负面定位非阻塞，仅影响日后方法层重启。

### 5.3 对本结论不利的证据（强制披露，不 cherry-pick）[二轮修订]
- **支持"原主线或可挽救"的证据（须披露）**：①**kd_only clean seed0 not broken**（dual 0.70、flip 0.942、info 全正 +1.8~+2.4）——训练型行为基线在干净数据上**保持了效用**，与 affine 坍塌不同；②其 E_CF 6.388 仍≫0（CI 下界 5.36>0），呈"效用保持但反事实响应大幅失真"的**解离模式**，恰是 H1 -type 现象——**若三 seed 复现，说明"反事实保真 gap"对 kd_only 在干净数据上可能真实存在**（只是原贡献(1) 围绕 affine 的框架已塌、且 PI 预承诺 C 类不复活贡献1）；③E0 干净 PASS、Self 锚点更健康、跑分代码逐字未变 → 翻转非实现假象，数据修复本身可信；④成对反事实 E_CF 框架确与 CacheLink(W2) 单上下文效用不同（W2 未做 E_CF），评价框架缝隙真实。
- **为何仍取 PIVOT 而非 GO**：原贡献(1)/(2) 的**正向主张已被 PI 撤回且 affine 证据确证坍塌**；kd seed0 的解离信号**单 seed、未审计、exploratory**，且 PI 预承诺即便 C 类也不复活贡献(1)。**本顾问不擅自把 kd seed0 升格为"H1 复活/贡献1 重建"**——那会覆盖 PI 裁决。是否据 kd 三 seed 调整叙事属 PI。
- **对本结论不利的另一面**：若 kd_only 三 seed 确证"not broken+稳健大 gap"，则本报告的"PIVOT/原主线不成立"对 **kd_only 臂**可能偏保守（gap 现象对 kd 或真实存在）；但原贡献(1) 的 affine 框架与贡献(2) 机制定位仍不成立，PIVOT（重定位为负面/边界 + 数据教训）依然正确，只是叙事可能纳入"kd_only 残留 gap"的有限观察（属 PI 择支）。这是基于当前单 seed 未审计证据的诚实暂定。

---

## 6. 给 PI 的明确建议

1. **阶段放行 [二轮修订：同意 PI 紧急裁决]**：
   - **P0/E0 GO**（clean E0 PASS，L29/L48）；
   - **P1：affine 失败边界已确证（三 seed 审计）**；原"utility-preserving gap"正向状态**撤回**；kd_only 择支待三 seed；
   - **P2 取消**（PI L47 §2：机制前提塌陷，不等重跑，旧 P2 证据撤回）——一轮"补 clean P2 三 seed"建议**作废**；
   - **P3 实质取消**（PI L47 §2：方法层"减少 gap"失去目标）；**P4 NO-GO**；**P5 投稿继续暂缓**（PI L47 §4.2，原因更强：核心贡献已推翻，须重写+择支+复核）。
2. **是否补实验 [二轮修订]**：**最高优先 = 完成 clean kd_only 三 seed**（seed0 已落盘 L49，seed1/2 待出），按 PI §3.3 预承诺 A/B/C 择支；**不再补 P2/P3/δ 复核**（PI 取消）。其次闭环 S1–S3 溯源（数据哈希入产物、v2.3 sha 澄清、runs_index 更新）。consumer/score/CacheLink 基线、M4 真实文档/外部锚点属日后另行问题（若重新构造干净失真数据再议），当前负面定位不强制。
3. **是否补文献 [二轮修订]**：**是**（B-3）。核实 KV-Lingo(W1)/CacheLink(W2)；补引 Heo(W3)/W4/Contrast Sets(W5)/Kaushik(W6)/FaithEval(W7)/CacheBridge(W12)/**Kapoor-Narayanan(W14)**；新定位新颖性限定为"具体预注册翻转案例 + E_CF 框架 + 完整审计轨迹"，区分于 W14 一般泄漏教训、W3 已知迁移失败、W2 单上下文功能、W4 压缩 answer-evidence gap。
4. **是否重写贡献表述 [二轮修订：PI 已裁定撤回，本顾问同意]**：
   - 贡献(1)：**撤回**原"reproducible utility-preserving gap"；可主张的负面结果 = "干净数据上 affine mapper 在 MVP 等深对的迁移失败边界" + "数据泄漏如何制造虚假科学发现的前后对照方法学教训"（PI L47 §4.3）；
   - 贡献(2)：**撤回 withheld**（删除所有 V-消费机制定位措辞）；
   - 贡献(3)：**维持 withheld**（主终点未评估、方法层无意义）；
   - 定位：**负面/实证结果论文**（失败边界 + 数据教训），仍 empirical/boundary study 但内涵已变；措辞精度按紧急复核 S4（joint E_CF **低于**非"相当"于控制）、S5（broken 单信号触发、exploratory、单对、合成域边界）。
5. **需 PI 新增版本的判据/口径事项 [二轮修订]**：
   - **[需 PI 新增版本]** 若把 kd seed0"not broken+大 gap"单独归类（超出 §3.3 情形 C"小 gap"字面）→ 澄清预承诺判读口径；
   - **[需 PI 新增版本]** S2 v2.3 文件哈希不一致（e44c6acb≠5200940c）+ 未跟踪 → 澄清回填过程、重算哈希、纳入 git 跟踪（排除"冻结后被改"疑虑；紧急复核判内容与实现一致、无按测试改判据证据）；
   - **[需 PI 新增版本]** 日后若重启方法层：min_clusters 口径/test 扩簇（M-1）、wild bootstrap-t（M-2）、基线清单（M-3）；
   - 其余（kd_clean 审计、runs_index/README/engineer_status 同步、S1 数据哈希入产物、self_threshold 元数据修正、补文献、负面措辞重写）**不改冻结判据**，按角色权限执行。
6. **与 PI 裁决的一致/冲突 [二轮修订]**：本顾问**同意并确认** PI `clean_data_reversal_ruling.md` 全部裁定（贡献1降级/贡献2撤回/P2P3取消/负面重定位/投稿暂缓/预承诺择支），紧急复核（L48）亦复核通过。**无实质冲突**。一轮报告（基于 seed0-only）建议"provisional/withheld + 继续重跑 + 预设 kd 坍塌才 PIVOT"，已被三 seed 确证 + PI 更强裁决超越；本二轮修订据此更新为 PIVOT。**唯一需 PI 注意的精度点**：§3.3 情形 C 字面"小 gap"与 kd seed0 实测"大 gap（6.39）"不完全吻合，最终归类待三 seed+PI（必要时新增版本澄清）。**本结论不覆盖 PI 裁决，不自行修改任何仓库状态。**

---

## 7. 审查方法与合规声明

- 已读取：README、docs/protocol、architecture、agent_team、algorithm_spec、experiment_design_E0_E7、data_card；configs/protocol.yaml、eval.yaml、prereg 全部 7 文件（含 v2.1/v2.2/v2.3）；docs/decisions 全部 8 文件；reports/runs 关键 metrics.json/config.json（含 clean run）、bootstrap_summary、consistency_report、runs_index/errata、engineer_status、review 全部、data 审计/修复/验收、p3_smoke_report、_non_authoritative 目录；papers/main.tex+notes.md；data/tasks/manifest.json；src 关键实现（counterfactual/cf_pipeline/build_cf_pairs/bootstrap_ci_report）；environment.json。
- 联网：websearch + webfetch 抓取 arXiv 一手原文（W1–W10）与官方仓库/ proceedings（W5/W6/W7/W11）；W12 经一手 bibliography 交叉确认存在；W13 阴性检索如实标注不确定。重要新颖性/对比判断（跨模型 KV 迁移已确立、成对反事实评测已确立、机制层被 CacheLink anticipate）均有 ≥2 独立一手来源交叉验证（W1+W2+W3+W12；W5+W6；W2 全文+W4）。
- 未做：未执行 shell、未重跑实验、未重算统计、未修改数据/代码/configs/prereg/docs/protocol/docs/decisions/reports/runs/论文源文件。所有数字均转抄自冻结产物或一手来源。
- mock / smoke / _non_authoritative 一律非证据；P1/P2 E_CF 为 Self 锚点非主终点；F5 负控不入翻转分母；主终点（封存 test vs kd_only 成对 E_CF CI 上界<0）未评估，不作改善声明；P>0.05 不作等效。
- 本报告仅写入 `reports/review/research_advisor/current_task_review.md`。

---

## 8. 修订记录与增补（二轮 · 2026-11-23 · 11:01 后新证据）

> 本章为二轮权威结论。触发：用户指出报告（10:59 落盘）被更新证据超越，要求增量修订。本顾问**自行读取核实**全部新证据（不凭转述），据此修订。**本结论不覆盖 PI 裁决。**

### 8.1 新证据读取核实记录（含一处与用户转述不符的如实更正）

| 核实项 | 读取结果（自行核实） |
|---|---|
| `p1_clean_mvp_seed1/metrics.json`+config | 存在且完整：joint E_CF 8.159、dual 0.283、Self 0.900、transfer_broken=true、git efc3ba3、created 10:39:37。**affine seed1 确证坍塌**。 |
| `p1_clean_mvp_seed2/metrics.json`+config | 存在且完整：joint E_CF 8.540、dual 0.383、Self 0.783、transfer_broken=true、git efc3ba3、created 10:42:58。**affine seed2 确证坍塌**。 |
| `clean_data_reversal_ruling.md` | 存在（PI 紧急裁决）：贡献(1) 冻结降级、贡献(2) 立即撤回 withheld（不等 P2）、kd_only 继续作失败边界择支、δ 复核停、P2 不启、P3 实质取消、论文重写负面/实证、投稿暂缓、§3.3 预承诺 A/B/C、§5 触发紧急复核、§6 不改冻结判据。 |
| `clean_data_reversal_emergency_review.md` | 存在（reviewer）：**翻转可信·高·非实现 bug**；跑分代码 458de18..efc3ba3 逐字未变；旧数据退化对/泄漏直接证实；Self 更健康；K/V-only 近 Self 仅 Joint 坍塌；v2.3 正确实现（exploratory）；S1–S5 收尾项；PI 裁定复核通过。 |
| **`p1_kd_clean_mvp_seed0/`** | **与用户转述不符的如实更正**：用户称"metrics.json 尚未写出"，但**本顾问读取时 metrics.json 已完整落盘**（config created_at **11:01:28**、git **6413ba0**、elapsed_sec 1060.1、train_sec 935、含完整 arms/decision/training 字段）。据实记录其指标（L49），**不推测 seed1/2**（runs 目录确认仅 seed0，无 seed1/2）。该 run **未入** bootstrap_summary/consistency_report/runs_index（审计 head efc3ba3 早于 6413ba0）。 |
| `bootstrap_summary.json`/`consistency_report.json` | 已重生成（v2.3 / head efc3ba3，26 run，含 affine clean×3，**不含 kd_clean**）。 |
| `main.tex`/`notes.md` | 已按裁决重写（贡献1/2 withdrawn、tab:cleanmvp/tab:reversal、kd PENDING、机制图不画）。 |
| `README`/`engineer_status`/`runs_index` | 仍过期（README 22 run 无翻转；engineer_status 无翻转章节；runs_index 未更新）。 |
| `stats_convention_v2.3.yaml` | 内容仍为 template_family/min24/excludes[F5,F6]/recomputed 398；**sha 不一致问题见 S2**（本顾问无 shell 不能算 sha，转抄紧急复核实测 e44c6acb≠5200940c）。 |

### 8.2 新增证据清单（L45–L53 本地；W14 网络）

| 编号 | 来源 | 关键事实（转抄，不重算） |
|---|---|---|
| L45 | `reports/runs/p1_clean_mvp_seed1/metrics.json`:134–423 + config:4–5 | affine seed1（val60，git efc3ba3，10:39:37）：joint E_CF **8.1590 [6.6467,9.7016]**（pair）；dual **0.2833** vs Self **0.9000**；flip 0.7358；cov 0.8833；**transfer_broken=true**（drop 0.6167）；info mismatch+0.887/random+0.111/zero+0.906；joint_ecf_ge_control=false；机器 verdict distortion_exists。已审计 ok。 |
| L46 | `reports/runs/p1_clean_mvp_seed2/metrics.json`:134–423 + config:4–5 | affine seed2（git efc3ba3，10:42:58）：joint E_CF **8.5402 [7.0565,10.0620]**（pair）；dual **0.3833** vs Self **0.7833**；flip 0.7547；cov 0.8833；**transfer_broken=true**（drop 0.4）；info +0.892/+1.314/+1.144；joint_ecf_ge_control=false。已审计 ok。 |
| L47 | `docs/decisions/clean_data_reversal_ruling.md`:9–153 | PI 紧急裁决：§0 三 seed 翻转属实；§1.1 贡献(1) 冻结降级（utility-preserving 前提塌陷）；§1.2 贡献(2) 立即撤回 withheld（不等 P2，机制对象不存在+旧 P2 污染不可信）；§2 kd_only 继续（失败边界确认）/δ 复核停/P2 不启/P3 实质取消；§3.1 机器 verdict 与 transfer_broken 分离；§3.3 预承诺 A/B/C；§4 论文重写负面/实证+投稿暂缓；§5 紧急复核；§6 不改冻结判据。 |
| L48 | `reports/review/clean_data_reversal_emergency_review.md`:10–135 | 翻转可信（高）非 bug：§3.1 跑分路径 458de18..efc3ba3 逐字未变（仅数据生成器 M1–M3 + P1 不调用的 P3 新方法）；§3.2 旧 scores 直接见 ('王五','王五') 等退化对、val 9 族全 -C 后缀、8 姓名共享；§3.3 Self dual 0.783–0.900（旧 0.683）更健康、K/V-only dual≈0.80 flip≈0.94–0.98 近 Self 仅 Joint 坍塌；§3.4 v2.3 exploratory 正确、template CI 宽于 pair 但下界>0；§4 混合信号（broken 仅 dual-drop 单信号触发、joint E_CF 仍低于控制、info seed0 2正1负）→ S4 措辞精度；§5 S1–S5；§6 PI 裁定复核通过。 |
| L49 | `reports/runs/p1_kd_clean_mvp_seed0/metrics.json`:134–430 + config:4–5,49–57 | **clean kd_only seed0**（git **6413ba0**，created **11:01:28**，elapsed 1060.1，train kd/8ep/lr1e-3/120对/7340032参数/train_sec935）：joint E_CF **6.3880 [5.3603,7.4001]**（pair-level，**未审计**）；dual **0.7000** vs Self **0.8167**（drop **0.1167<0.2**）→ **transfer_broken=FALSE**；flip **0.9423**；cov 0.8667；info mismatch**+2.396**/random**+1.811**/zero**+2.196**（全正）；joint E_CF 低于控制（mismatch 8.7845/zero 8.584）；机器 verdict distortion_exists。**未入 bootstrap_summary/consistency/runs_index；seed1/2 未产出。不推测终值。** |
| L50 | `reports/bootstrap_summary.json`:1–17,453–786 | 已重生成 **v2.3**（26 run）：含 e0_clean+p1_clean×3，template_family 主 CI+pair 敏感性+exploratory=true（8 簇）。affine joint template CI：seed0 **6.900 [3.564,10.100]**、seed1 **8.159 [4.357,11.584]**、seed2 **8.540 [5.326,11.610]**，下界均>0。**不含 p1_kd_clean**。 |
| L51 | `reports/consistency_report.json`:101–204 | 已重生成 head **efc3ba3**（26 checked/22 failed）：clean run ok=true/traceable=true；旧 repro 458de18 转 **ok=false**（"run code differs vs HEAD"，因 gpu_backend 增 torch_candidate_logits，S3 正常连带）；8 旧 superseded 仍 fail。**不含 kd_clean 6413ba0**。 |
| L52 | `papers/readkv_v2_draft/main.tex`:16,58,84,448,472–513 + `notes.md`:4,10,17–37,61–70 | 已按裁决**整体重写**：摘要报失败边界+方法学教训；贡献(1)(2) **withdrawn**；Table tab:cleanmvp（干净三 seed）/tab:reversal（前后对照）；kd_only **PENDING**；机制图5 **不画**；负面/实证定位；投稿暂缓。 |
| L53 | `README.md`:22 + `reports/engineer_status.md`（无翻转章节）+ `reports/runs_index.json`（未更新） | **仍过期**：README 22 run、无翻转/撤回/暂缓；engineer_status 止于 §12 P3 暂停、无翻转章节；runs_index 未纳入 clean run、旧 repro 未标 superseded（S3）。 |
| W14 | Kapoor & Narayanan, *Leakage and the reproducibility crisis in machine-learning-based science*, Patterns 2023 / arXiv 2207.07048（被引2755） | https://arxiv.org/abs/2207.07048 ；https://www.sciencedirect.com/science/article/pii/S2666389923001599 （访问 2026-11-23） | 数据泄漏广泛（17 领域 294 篇）致过度乐观/不可复现结论。**→"泄漏制造虚假发现"的一般教训已确立；本课题重定位的新颖性须限定为"具体预注册翻转案例 + 完整审计轨迹 + E_CF 成对反事实框架"，非一般教训本身。** 一手（期刊/arXiv）。 |

### 8.3 修订后总体结论：PIVOT（原主线），新定位 CONDITIONAL GO

**一句话：PIVOT。** 原"utility-preserving 反事实失真 gap（贡献1）+ V-消费机制定位（贡献2）"主线在干净数据上不成立，**PI 已裁定翻转/撤回，本顾问独立复核后同意并确认**；新定位"跨模型 KV 迁移失败边界 + 数据泄漏如何制造虚假科学发现"负面/实证研究为 **CONDITIONAL GO**（待 kd_only 三 seed 择支 + S1–S3 收尾 + 论文重写经复核 + 投稿暂缓）。

**理由**：①affine 三 seed 干净数据 transfer_broken=true 已确证并经 v2.3 审计 + 紧急复核（高可信、非 bug）；②旧正向信号被直接证实为数据缺陷假象（退化对+泄漏）；③PI 据此撤回贡献(1)/(2)、取消 P2/P3、重定位负面结果——本顾问一轮"provisional/继续重跑"建议基于 seed0-only，现被三 seed 确证超越，**同意 PI 更强裁决**；④新负面主张（失败边界+翻转教训）证据充分，但新颖性须对 W14/W3/W2/W4 限定。

**已确证（confirmed）**：
- affine 臂干净数据效用坍塌：三 seed joint E_CF 6.900/8.159/8.540、dual 0.417/0.283/0.383（Self 0.817/0.900/0.783）、transfer_broken=true×3；v2.3 template CI 下界均>0（exploratory 8 簇）；consistency ok。
- 翻转非实现 bug：跑分代码逐字未变、E0 干净 PASS、Self 锚点更健康、K/V-only 近 Self 仅 Joint 坍塌、旧数据缺陷直接观测。
- 原贡献(1)/(2) 正向证据基础塌陷 → PI 撤回（本顾问同意）。
- main.tex/notes.md 已重写为负面定位。

**待决（pending，不推测）**：
- **clean kd_only 三 seed 最终 A/B/C 择支**：seed0 已落盘（**not broken**、dual 0.70、E_CF 6.388 **大 gap**、info 全正），**既非纯 A 亦非纯 B，最接近预承诺情形 C 但 gap 不"小"**；seed1/2 未产出、seed0 未审计。最终归类属 PI（§3.3 预承诺；若"not broken+大 gap"需单独处理须 PI 新增版本澄清字面）。
- S1（数据哈希入 run 产物）/S2（v2.3 sha 不一致+未跟踪）/S3（runs_index 更新+旧 run superseded）溯源收尾。
- README/engineer_status 同步；论文重写经审稿复核；投稿暂缓解除条件。

### 8.4 逐条修订对照表（修订前 → 修订后）

| 条目 | 一轮（修订前） | 二轮（修订后） |
|---|---|---|
| **总体结论** | CONDITIONAL GO（放行修复+重跑，预设 kd 三 seed 仍 broken 才 PIVOT） | **PIVOT**（原主线已由 PI 裁定翻转、本顾问同意）；新定位 CONDITIONAL GO。触发条件修正：PIVOT 实际由 affine 三 seed 坍塌+PI 判定驱动，**不依赖 kd 也 broken**（kd seed0 反而 not broken）。 |
| **方向** | 合理（新颖性窄） | 合理（**原正向假设被证伪、重定位后问题成立**；新颖性须对 W14 泄漏教训/W3 已知失败/W2 单上下文/W4 压缩 gap 限定为"具体翻转案例+E_CF 框架"）。 |
| **方案** | 存疑（纪律优秀、执行缺口） | 存疑（**纪律 proven effective：成功检出并纠正假阳性**；缺口仍在：test16<24 簇、基线不全、合成域窄、少簇覆盖、self_threshold 误标、pipeline CI pair-level）。 |
| **实验** | 存疑（clean 仅 E0+P1 seed0、kd/P2 缺、未审计） | 存疑（**affine 三 seed 已确证并审计**；**kd_only seed0 落盘未审计、seed1/2 待出**；P2/P3 已取消；S1–S3 溯源+索引未闭环）。 |
| **结果** | 存疑（pre-fix 失效、clean 首跑坍塌、正向不成立、kd 缺） | **合理**（就新负面定位：affine 失败边界+翻转已三 seed 确证审计、非 bug；原正向主张已撤回；kd_only A/B/C 待决不影响 affine 确证；措辞按 S4/S5 精确）。 |
| **B-1** | 干净正向证据未重建、H1 存亡未定、kd/P2 缺、建议补 clean P1/kd/P2 | **affine 失败边界确证、PI 撤回贡献1/2、P2/P3 取消**；剩余=完成 kd_only 三 seed 择支+S1–S3；**不再补 P2/P3**。 |
| **B-2** | clean run 未审计/索引、bootstrap_summary 不含 clean | **affine clean 已入 v2.3 审计（L50/L51）**；**kd_clean seed0 未审计**、runs_index 仍未更新（S3）；建议对 kd_clean 补审计+更新索引+S1 数据哈希。 |
| **B-3** | 相关工作未 engage、贡献2 de novo 过宽 | **正向措辞已撤回（main.tex 重写 L52）**；引用核验/engage 仍投稿前必做；新定位新颖性对 W14/W3/W2/W4 限定。 |
| **M-1**（test16<24 簇） | 主终点确认性不可达、需 PI 新增版本 | **P3 取消→对当前负面定位阻塞性降低**（不再追求方法增益确认性）；affine 失败边界为大效应、template CI 下界>0 方向稳健（exploratory 诚实标注）；日后重启方法层仍须解决 [需 PI 新增版本]。 |
| **M-2**（少簇覆盖） | 宜补 wild bootstrap-t | 维持建议；当前负面结果效应大、方向稳健，少簇覆盖问题对定性结论阻塞性低；正式推断口径若纳入 wild bootstrap-t 须 [需 PI 新增版本]。 |
| **M-3**（强基线不全） | 补 consumer/score/CacheLink、若重启 P3 加 CacheLink | **P3 取消→方法层基线对照不再当前必需**；失败边界主张限定"已测 affine（+kd seed0）"；consumer/score/CacheLink 属日后另行问题；"所有 mapper 都失败"须待 kd 三 seed（A 类）方可主张。 |
| **M-4**（文档不一致） | README 过期、notes/main.tex 已更新为 superseded/重跑中 | **main.tex/notes 已重写为 withdrawn/负面定位（L52）**；**README/engineer_status/runs_index 仍过期（L53/S3）**，须同步。 |
| **M-5**（合成域窄/real=0） | 外部效度不足、建议 M4/外部锚点 | 维持（负面定位仍受合成域/单对限制，须披露）；M4/外部锚点属日后增强，当前不强制；affine 坍塌未必普适（Heo W3 真实域 4/6 成功）。 |
| **m-1**（self_threshold 误标） | detail 0.001 vs 实际 0.1 | 维持（clean/kd_clean metrics detail 仍标 0.001，L45/L46/L49）；工程师修正元数据，不改冻结 0.1。 |
| **m-2**（data_card null→398） | data_card 称 null、实际 398 | 维持文档同步建议；**另见 S2：v2.3 文件 sha 不一致+未跟踪（新增主要级）**。 |
| **m-3/m-4/m-5** | E0 尺度/δ git hash/smoke 非权威 | 维持（E0 干净 PASS 已披露；δ 复核已取消；smoke/_non_authoritative 仍非证据）。 |
| **§5 失效条件** | kd 三 seed 仍 broken→PIVOT；kd 恢复+gap→H1 存活贡献1 可重建 | **PIVOT 已发生（affine+PI）**；kd 三 seed A/B/C 择支待决（seed0 not broken+大 gap≈C 但 gap 不"小"）；**无论 A/B/C 贡献3/方法层不成立（PI 预承诺）**；不擅自把 kd seed0 升格为 H1 复活。 |
| **§6 给 PI 建议** | 补 clean P1/kd/P2、provisional 贡献、预设 PIVOT | **同意 PI 裁决**：贡献1/2 撤回、P2/P3 取消、负面重定位、投稿暂缓；剩余=kd 三 seed 择支+S1–S3+文档同步+引用核验；kd"not broken+大 gap"归类若超 §3.3 字面须 [需 PI 新增版本]。 |

### 8.5 新增风险（来自紧急复核 L48 §5，纳入排序）

- **S2｜主要级（溯源/冻结一致性）｜v2.3 文件哈希不一致 + 未纳入 git 跟踪。** 紧急复核实测 `stats_convention_v2.3.yaml` 当前 sha256=`e44c6acb…` ≠ manifest/验收记录 `5200940c…`；recomputed_value null→398 回填后未更新两处哈希，且 null→398 之外的差异使哈希无法用单一回填解释。**复核判内容与实现一致、无按测试改判据证据**，但须 **PI 澄清回填过程 + 重算哈希 + 纳入 git 跟踪**，排除"冻结后被改"疑虑。**[需 PI 处理/新增版本]**。本顾问无 shell 不能独立算 sha，转抄复核实测并标注。
- **S1｜次要级｜clean run 产物未记录数据哈希 `f910f1f1…a894a`。** run→数据无法从 run 产物单独绑定，削弱可复现溯源。建议工程师补 metadata 勘误（不改 scores）。
- **S3｜次要级｜runs_index/errata 未更新 + 旧 run consistency 连带失败。** clean run 未入索引、旧 repro 未标 superseded；consistency failed=22 中 14 个旧 run 因 HEAD 前进（gpu_backend 增方法）触发"run code differs vs HEAD"（正常连带，非数据修复 bug）。须更新索引避免下游误用旧数。
- **S4｜次要级（披露精度）｜"E_CF 与控制相当"措辞略强。** 实测 joint E_CF（6.9–8.5）**仍低于**错配/零控制（8.4–9.7），joint_ecf_ge_control=false，info seed0 2正1负；broken 由 dual-drop 单信号触发。论文须精确为"E_CF 大幅升高、接近但尚未超过控制，伴 dual 坍塌"，不得夸大为"达到/超过无信息控制"。
- **S5｜次要级（强度）｜transfer_broken 单信号触发 + exploratory（8 族<24）。** 不得作强显著性/跨对泛化主张；负面结论限定"已测 affine、MVP 等深对、受控合成域、exploratory"。

### 8.6 与 PI 裁决一致/冲突核对

- **一致（同意并确认）**：贡献(1) 冻结降级、贡献(2) 立即撤回 withheld（不等 P2）、P2/P3 取消、kd_only 继续作失败边界择支、论文重写负面/实证、投稿暂缓、§3.3 预承诺 A/B/C、不改冻结判据。紧急复核（L48）亦复核通过。本顾问二轮结论与 PI 裁决**无实质冲突**。
- **一轮→二轮的自我修正**：一轮基于 seed0-only 建议"provisional/withheld + 继续重跑 P1/P2 + 预设 kd 坍塌才 PIVOT"；三 seed 确证 + PI 更强裁决后，**作废"补 clean P2"建议**（PI 取消 P2），**更新总体结论为 PIVOT**。这是新证据驱动的合法自我修正，非推翻 PI。
- **唯一需 PI 注意的精度点（非冲突）**：§3.3 情形 C 字面"稳定**小** gap"与 kd seed0 实测"**大** gap（E_CF 6.39，normalized 0.585）"不完全吻合；最终归类待三 seed+审计+PI（必要时新增版本澄清预承诺字面）。**本顾问不擅自归类、不覆盖 PI 裁决。**
- **措辞精度**：采纳紧急复核 S4，PI 裁决 §1.1"E_CF 与控制相当"宜精确为"接近但尚未超过"（不影响 broken 定性）。

### 8.7 修订后失效条件

- **若紧急复核被推翻（判实现 bug）** → 停冻结、修复重跑（PI §5）；当前判非 bug（高），PIVOT 维持。
- **若 kd_only 三 seed 确证 A（也 broken）** → 纯失败边界，强化 PIVOT。
- **若 kd_only 三 seed 确证 B（not broken 且 E_CF 小近 Self）** → "泄漏制造虚假 gap"方法学负面结果，PIVOT 维持、叙事偏 B。
- **若 kd_only 三 seed 确证 C（not broken 但稳健 gap）** → 边界研究；**若 gap 大（如 seed0）且 PI 认为构成 kd_only 自身效用-保真解离的有限正面观察**，叙事可纳入该观察，但**原贡献(1) affine 框架/贡献(2) 机制定位仍不成立**，PIVOT（重定位）依然正确；是否升格任何正面措辞属 PI（预承诺 C 不复活贡献1）。
- **若发现 clean/kd_clean run 读封存 test/挑 seed/改判据** → NO-GO（诚信）；当前未见（eval_splits=val、冻结判据 git diff 空）。

### 8.8 仍待决的决定性实验（明确）

> **clean kd_only 三 seed（`p1_kd_clean_mvp_seed{0,1,2}`）= 唯一决定性择支实验。**
> - seed0 **已落盘**（L49，not broken+大 gap，未审计）；**seed1/2 未产出**（runs 目录确认）。
> - 须：①seed1/2 跑完；②三 seed 经 v2.3 bootstrap_ci_report+consistency_check 审计（git 6413ba0）；③PI 按 §3.3 预承诺 A/B/C 择支（seed0 大 gap 与 C 字面"小 gap"的吻合度由 PI 裁定，必要时新增版本澄清）。
> - **本顾问不推测 seed1/2 结果、不擅自归类 seed0、不覆盖 PI 择支。** 在该实验闭环前，总体结论维持 **PIVOT（原主线）+ 新定位 CONDITIONAL GO（待择支）**。

---

## 9. 二轮合规声明

- 本轮新增读取：`p1_clean_mvp_seed{1,2}/metrics.json+config.json`、`p1_kd_clean_mvp_seed0/metrics.json+config.json`、`clean_data_reversal_ruling.md`、`clean_data_reversal_emergency_review.md`、重生成后的 `bootstrap_summary.json`/`consistency_report.json`、重写后的 `main.tex`/`notes.md`、`stats_convention_v2.3.yaml`（复核内容）、runs/decisions 目录清单、README/engineer_status/runs_index 过期状态。
- 本轮新增联网：W14（Kapoor-Narayanan 2023，arXiv 2207.07048 / Patterns，访问 2026-11-23，一手）。其余 W1–W13 沿用一轮（访问 2026-11-23）。
- 未做：未执行 shell、未重跑实验、未重算统计、未修改数据/代码/configs/prereg/docs/protocol/docs/decisions/reports/runs/论文源文件。所有数字转抄自冻结产物或一手来源；v2.3 sha 不一致（S2）转抄紧急复核实测（本顾问无 shell 不能独立算 sha，已标注）。
- 与用户转述不符处已如实更正：`p1_kd_clean_mvp_seed0/metrics.json` 在本轮读取时**已完整落盘**（非"尚未写出"），据实记录指标、不推测 seed1/2。
- mock/smoke/_non_authoritative 非证据；P1/P2 E_CF 为 Self 锚点非主终点；F5 负控不入翻转分母；主终点未评估、不作改善声明；P>0.05 不作等效；**本结论不覆盖 PI 裁决**。
- 本报告仅写入 `reports/review/research_advisor/current_task_review.md`（一轮原文保留供审计，关键过期表述就地标注"[二轮修订]"，§8 为二轮权威结论）。

**签署：research-advisor（联网独立对抗性评估 · 一轮 2026-11-23 10:59；二轮增量修订 2026-11-23 11:01 后）**
