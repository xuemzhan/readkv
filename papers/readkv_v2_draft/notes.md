# 写作者笔记 —— readkv_v2_draft（仅内部，不投递）

> 状态：论文配套笔记。所有数值只读自 `reports/runs/**`、`reports/anchor_eval_summary.json` 与 `reports/data/**` 冻结产物；本笔记未重新计算任何统计量。
> 最新定性（2026-11-23，PI 收口）：论文定位 = **跨模型 KV 迁移失败边界 + 数据泄漏如何制造虚假科学发现**的负面 / 实证 / 数据审计研究。贡献(1) 撤回、贡献(2) 撤回 withheld、贡献(3) withheld；P2/P3/P4 正式且永久取消；`real=0`；投稿暂缓。

---

## 0. 本轮重写范围

- `papers/readkv_v2_draft/main.tex`：重写摘要 / 引言 / 贡献段 / 结果段 / 讨论·限制·结论；新增相关工作（正面引用并区分 CacheLink、KV-Lingo、Heo、Does Accuracy Equal Evidence、Contrast Sets、Kaushik、Kapoor-Narayanan 及 addendum N1–N9）；修正 S4/S5；更新表格（干净 affine 三 seed、kd 三 seed、前后对照、数据修复、SQuAD 锚点）；删除机制热图与方法消融图。
- `papers/readkv_v2_draft/notes.md`（本文件）：权威数值清单、投稿暂缓、venue、署名、引用核验状态、v2.6 处置。

**未写 / 未改**：任何代码、`reports/runs/**`、`configs/prereg/**`、冻结判据；未重算统计。

---

## 0.1 紧急纠正：v2.6 AI 数据全部撤回（已修正）

- `docs/decisions/ai_dataset_final_ruling.md`（最终裁定）：撤回原「有条件 GO」；v2.6 冻结但 **not activated**；**不创建 `data/generated/`**；不写任何 human-seeded / model-generated 数据集及其结果。
- **本稿已修正**：删除原「v2.6 AI 数据作为额外探针」的预留结果表与表述；外部效度只写 `real=0` 受阻披露 + SQuAD（必要时 ARC）锚点的有限外部效度。
- 论文仅在 §「Data correctness…」与 data-availability 语境如实写一句「AI 生成数据集提案已评估并撤回（not activated），无遗留产物」；**不含任何生成数据结果**。notes.md 图表清单中的 v2.6 结果位同步删除。

---

## 1. 权威数值清单（逐字转抄冻结产物，禁止重算）

### 1.1 干净 affine 三 seed（`p1_clean_mvp_seed{0,1,2}/metrics.json`，commit `efc3ba3`，val 60 对）

| seed | Joint E_CF [95% CI] | Self dual | Joint dual | flip | cov. | transfer_broken |
|---|---|---|---|---|---|---|
| 0 | 6.900 [5.499, 8.313] | 0.817 | 0.417 | 0.750 | 0.867 | true |
| 1 | 8.159 [6.647, 9.702] | 0.900 | 0.283 | 0.736 | 0.883 | true |
| 2 | 8.540 [7.057, 10.062] | 0.783 | 0.383 | 0.755 | 0.883 | true |

- seed0 控制组：mismatch 8.383、zero 8.584、random 6.765；info_attribution mismatch +1.483 / zero +1.684 / random −0.135；joint dual drop 0.4（≥0.2 阈值）；`joint_ecf_ge_control` 两个 false。
- **S4**：E_CF 大幅升高、**接近但未超过**错配 / 零缓存控制；禁写「达到 / 相当于无信息水平」。broken 定性由 dual 坍塌（单信号）支撑。
- E0 干净复验：`e0_clean_mvp_seed0`，cosine 1.0、KL 0、EM 0.975、round-trip bit-identical、zero_re_prefill、误差上限 2.2e-16。

### 1.2 干净 kd_only 三 seed（`p1_kd_clean_mvp_seed{0,1,2}/metrics.json`，commit `6413ba0`，val 60 对）

| seed | Joint E_CF [95% CI] | joint dual (drop) | flip | cov. | transfer_broken |
|---|---|---|---|---|---|
| 0 | 6.388 [5.360, 7.400] | 0.700 (0.117) | 0.942 | 0.867 | false |
| 1 | 6.479 [5.419, 7.539] | 0.733 (0.167) | 0.906 | 0.883 | false |
| 2 | 7.211 [6.078, 8.322] | 0.767 (0.017) | 0.925 | 0.883 | false |

- 情形 C：kd 不 broken、dual 0.70–0.77、**稳定非零 exploratory gap**；按 PI 终裁 **仅作探索性观察**，不恢复贡献(1)，不写「reproducible gap」。
- 注意口径：上表 CI 直接转抄 `metrics.json`（pair-level bootstrap）。元审查 `current_task_meta_review.md` §3.1 指出 v2.3 主口径应为 `template_family` 簇级 CI（只读复算 seed0 6.388 [3.653, 8.814]、seed1 6.479 [3.883, 8.773]、seed2 7.210 [4.362, 9.757]，8 族、exploratory=true）；该口径统一由 PI / 审稿人出说明，**写作者不私下改表、不重算**。

### 1.3 修复前后方向翻转（Table `tab:reversal`）

| 量 | 旧 v2.0（superseded） | 干净 v2.1（权威） |
|---|---|---|
| Joint E_CF | 1.93–2.12 | 6.90–8.54 |
| Joint dual | 0.617–0.667 | 0.283–0.417 |
| Self dual | 0.600–0.683 | 0.783–0.900 |
| flip consistency | 0.898–0.958 | 0.736–0.755 |
| transfer_broken | false | true (all seeds) |

### 1.4 数据质量修复（`data_fix_report.md` / `acceptance_checks.json`）

- 退化对 18（其中 test 7）→ 0；跨 split 逐字重叠 ≥15 组 → 0；实体重叠 8 姓名共享 → 0；基础结构 / 族 8 / 40 → 24 / 56；真正未见 后缀-only → 32 族 / 16 结构；train/test 骨架 100% 重合 → ∅；flip 分母 394（含 18 退化）→ 398；bootstrap 簇 300 pair-level → template-family。
- 数据 SHA-256：旧 `6058fd6d…d1887`；新 `f910f1f1…a894a`；验收 11/11、53 单测通过；v2.3 主簇 `template_family` + pair-level 敏感性，族数<24 标 exploratory。

### 1.5 SQuAD v2.0 dev 外部锚点（`reports/anchor_eval_summary.json`，seed0，240 answerable）

- 数据：官方 `dev-v2.0.json`，sha `80a5225e…82d8`，CC BY-SA 4.0，仅评测不发布衍生语料；eval commit `938f3a0`，run HEAD `b7b9f50`，跑分路径 `git diff` 空。
- Self EM/F1 = 0.000 / 0.1975（两臂同）；Joint EM = 0.000（两臂）。
- `anchor_squad_affine_seed0`：Joint F1 = 0.0051（Joint/Self = 2.6%，drop 0.1924）。
- `anchor_squad_kd_seed0`：Joint F1 = 0.0014（Joint/Self = 0.7%，drop 0.1961）。
- v2.4 三情形判读：`exploratory_disclosure`（affine 失败方向复现，但 kd 保持 utility 的对照未复现、EM 全臂触底因 base 0.6B 未微调、仅 seed0/240 例）。**不**强化外部效度、**不**反转叙事、**不**恢复贡献；不与合成 test 混算、不重算冻结 CI；仅为探索性外部锚点观察，无跨数据源普适性主张。
- **锚点数值待补事项已清零**：SQuAD 锚点数值已全部补入正文 §「External anchor」与表 `tab:anchor`；ARC/HellaSwag 为顺位增强项（未跑、非本稿待补项）。venue 已由真实 PI 指定为 **TMLR**（见决策记录）。
- 引用要求（`anchor_confirmation.md` §3）：Rajpurkar et al., EMNLP 2016（doi:10.18653/v1/D16-1264）与 Rajpurkar, Jia et al., ACL 2018（doi:10.18653/v1/P18-2124）。**待投递前加入 bibliography**（当前 main.tex 锚点表已注明数据来源，但未列这两条 bibitem）。

---

## 2. 贡献措辞门槛（§10，全部撤回 / withheld）

- **贡献(1) 撤回**：禁 "reproducible gap / utility-preserving distortion / We identify a gap" 作正式贡献。S4：全文「接近但未超过控制 + dual 坍塌」。
- **贡献(2) 撤回 withheld**：禁机制定位（"localize the gap / V-consumption cause / causal / sole cause"）；旧 P2 证据建于污染数据，P2 未重跑。
- **贡献(3) withheld**：CF-RCT 未训练、主终点未评估、P3 永久取消；禁 "method reduces the gap / improves over kd_only / without-target-re-prefill at inference"。
- **不声称**：一般 utility/fidelity 区分首创（N1/N2 已公开）、机制层首创（N3/CacheLink 已公开）、一般泄漏教训（Kapoor-Narayanan 已确立）、新审计方法、跨模型 / 真实世界 / 强显著性 / 跨对泛化。
- 新颖性严格限定：**具体预注册翻转案例 + 成对反事实 E_CF 审计轨迹**。
- 不把 `P>0.05` 写成等效；主终点未评估前无 endpoint gain 声明；mock 非证据；封存 test 未评测。

---

## 3. S4/S5 收尾核对（写作者强制项）

- **S4**：joint E_CF 大幅升高、接近但未超过错配 / 零控制（seed0 6.90 vs 8.38 / 8.58），伴 dual 坍塌 0.4；info 归因 2 正 1 负；已写入摘要 / §Results / §Adverse / §Conclusion。
- **S5**：`transfer_broken` 由 dual-drop **单信号**触发；`exploratory=true`（8 族<24、CI 宽、下界>0 但非强推断）；**单一 MVP 等深对**；**合成域**；**封存 test 未评测**；机器 verdict `distortion_exists` 与 `transfer_broken=true` 口径分离披露。已写入 §Adverse 与 §Conclusion。

---

## 4. 图表清单（只读冻结产物生成，不重算统计）

| 编号 | 内容 | 数据来源 | 当前状态 |
|---|---|---|---|
| 图 1 | 两条既有研究线 → 数据审计案例关系图 | 设计性示意 | 文字占位；叙事已改为数据审计翻转 |
| 图 2 | 严格 zero re-prefill 流程与四臂分界 | `algorithm_spec.md §3.4/§6.1` | 文字占位 |
| 图 3 | 反事实成对文档构造与正/负控制 | `protocol.md §3.2` | 文字占位 |
| 图 4（原生 vs 迁移响应差散点） | — | — | **不画**（机制/正向结果撤回） |
| 图 5（机制热图 / Oracle 修复） | — | 旧 `p2_gpu_mvp_seed*`（撤回） | **已删除** |
| 图 6（方法消融） | — | E3 未跑 | **已删除** |
| 图 7（泛化 / 成本—Pareto） | — | E4/E5/E6 取消 | **不画** |
| Table `tab:datafix` | 数据缺陷前后对照 | `data_fix_report.md`、`acceptance_checks.json` | 正文已呈现 |
| Table `tab:cleanmvp` | 干净 affine 三 seed | `p1_clean_mvp_seed{0,1,2}/metrics.json`（`efc3ba3`） | 正文已填 |
| Table `tab:reversal` | 修复前后方向翻转 | 旧 repro run + 干净 clean run | 正文已呈现 |
| Table `tab:cleankd` | 干净 kd 三 seed | `p1_kd_clean_mvp_seed{0,1,2}/metrics.json`（`6413ba0`） | 正文已填（exploratory） |
| Table `tab:anchor` | SQuAD v2.0 dev 锚点 | `reports/anchor_eval_summary.json`（seed0） | 正文已填（exploratory_disclosure） |
| — | v2.6 AI 数据结果 | 无（not activated） | **删除，不设结果位** |

注：所有正文数值表从冻结产物转抄；旧 P1/P2 数值仅出现在翻转对照历史侧；不得用 mock 或旧 run 作最终结论。

---

## 5. 引用核验状态（协议 §9）

### 5.1 已核验（一手 arXiv abs / ACL，访问 2026-11-23）

- **KV-Lingo** — Castin, Sakamoto, Filippova, Monteiro, Cuturi, Ablin, *arXiv:2609.32610* [cs.CL], 2026（v1 2026-09-26，doi:10.48550/arXiv.2609.32610）。逐层线性 K/V 映射 + 行为蒸馏。
- **CacheLink** — Qiu, Tang, Song, Han, Qiao, Zhang, *arXiv:2610.15509* [cs.LG], 2026（v1 2026-10-11，doi:10.48550/arXiv.2610.15509）。功能监督；重构保真≠接收端效用；四臂 K/V swap 诊断（章节级细节仅摘要级核验）。
- **Heo et al.** — Heo, Shafipour, Zhao, Golub, Kamani, Borkar, Chandran, Zardoshti, Rouhani, *arXiv:2608.03893*, 2026-08-04。闭式 per-head ridge，6 对中 4 对保 73–98%、2 对急剧退化。
- **Does Accuracy Equal Evidence?** — Ai, He, Guo, *arXiv:2608.01631*, 2026（v2 2026-10-24），EMNLP 2026 Findings。KV 压缩下 answer–evidence gap。
- **Contrast Sets** — Gardner et al., *Findings of EMNLP 2020*, arXiv:2004.02709。最小编辑 + contrast consistency。
- **Kaushik et al.** — Kaushik, Hovy, Lipton, *ICLR 2020*, arXiv:1909.12434。反事实增强。
- **Kapoor & Narayanan** — *Patterns* 2023, arXiv:2207.07048。泄漏与可复现性危机的一般教训（17 领域 294 篇）。

### 5.2 addendum N1–N9（`third_round_online_addendum.md`，标题/作者/摘要/日期已核，**未逐篇读全文**）

- N1 `2611.14051` DeepSeek-V4-Flash 跨版本 KV 复用 + Functional Cache Divergence（utility vs fidelity）；
- N2 `2610.22016` Fidelity-Consumability Decoupling（八种 substitute-cache 停在无信息 baseline）；
- N3 `2610.15721` 跨模型 KV safety 不兼容，value 偏差>key 偏差 + per-layer/head affine；
- N4 `2610.42116` ACCT；N5 `2610.15095` Swarm Telepathy；N6 `2610.11358` RaReCache；N7 `2608.04893` 因果审计 + mismatched/zero/random + TOST；N8 `2610.16165` CacheFuse；N9 `2611.12062` hybrid-attention 翻译 + `2611.11761` BridgeKV。
- 状态：标题 / arXiv 号 / 日期真实；**章节级细节未核实**，引用进正式稿前须由真实 PI / 审稿人按 §9 做全文口径核验。N1–N9 的 bibliography 条目当前以标题 + arXiv 号 + 年份占位（未填作者名，避免编造）。
- SQuAD 引用（Rajpurkar 2016 / Rajpurkar-Jia 2018）**待补入 bibliography**（见 §1.5）。

---

## 6. 投稿状态 / venue / 署名

- **投稿暂缓（Submission deferred）**：核心贡献被推翻、S4/S5 措辞刚修正、引用（N1–N9 全文口径、SQuAD 两条）待核验、kd 的 v2.3 簇级口径说明待 PI/审稿人出；P5 重开前不得投递、不得沿用旧 run 作最终结论。
- **venue：TMLR（真实 PI 已指定，2026-11-23）**。`docs/decisions/venue_recommendation.md` 首选 TMLR（次选 EASE 2027 RENE、ACL 2027 ARR）；理由：接受 modest contribution、对单模型对 / exploratory / 无方法贡献的证据强度最友好、Reproducibility Certification 契合。P5 已获附条件最终签off（docs/decisions/p5_final_signoff.md），进入 ready-to-submit。
- **署名（真实 PI 决策 6，已定）**：作者统一为 **Zhang Xuein \<zxm0813@gmail.com\>**；论文 `\author{}`、cover letter 与投稿元数据须一致。单作者原创，非会议扩写。
- **格式待办（不属科学结论，投递前处理）**：当前摘要约 270–290 词，超过 TMLR 的 ≤200 词上限；定稿时须压缩（保留「接近但未超过控制 + dual 坍塌」「kd exploratory」「贡献撤回」「test 未评」等强制边界措辞）。图 1–3 仍为文字占位，TMLR 投稿时可说明、接受后补齐。
- **cover letter（草稿要点）**：① 主题为负面 / 实证 / 数据审计研究，不宣称正向贡献；② 数据质量决定性影响——修复缺陷后「显著」发现完全翻转；③ 干净数据上 affine 在 MVP 等深对的迁移失败边界；④ 诚实披露贡献(1)(2) 撤回、(3) withheld、主终点未评估、封存 test 未评测、real=0、单模型对、exploratory；⑤ 复现：固定 SHA `f910f1f1…a894a`、commit 链、v2.1–v2.5 预注册、bf16/sdpa/zero re-prefill、mock 非证据、P>0.05 不作等效；⑥ 审稿人可重算 `bootstrap_ci_report` / `consistency_check`。无独立 cover letter 文件，本要点即草稿。

---

## 7. 下一步（触发条件）

- **引用核验**：N1–N9 全文口径 + SQuAD 两条 bibitem，投递前按 §9 完成；替换任何未核实细节。
- **kd v2.3 口径说明**：由 PI / 审稿人统一 pair-level vs template-family 口径，写作者不改表、不重算。
- **S1–S5 闭环**：S1 数据哈希绑定勘误、S2 manifest sha 同步、S3 runs_index 已闭环；S4/S5 本稿已写入；收尾后由审稿人出 P5 合规意见。
- **投稿状态**：引用已实际核验、口径与审稿复核（含锚点合规）均已完成、venue=TMLR 已指定、P5 已签off → **ready-to-submit**；由真实 PI 本人通过 OpenReview 提交（agent 不代为提交）。
- **不变量**：P2/P3/P4 永久放弃、不另立「修复 broken transfer」新课题；v2.6 not activated、`data/generated/` 不创建；封存 test 不碰；不恢复任何已撤回贡献。
