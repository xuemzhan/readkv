# 写作者笔记 —— readkv_v2_draft（仅内部，不投递）

> 状态：论文配套笔记。所有数值只读自 `reports/runs/**`、`reports/anchor_eval_summary.json` 与 `reports/data/**` 冻结产物；本笔记未重新计算任何统计量。
> 最新定性（2026-11-23，PI 收口）：论文定位 = **跨模型 KV 迁移失败边界 + 数据泄漏如何制造虚假科学发现**的负面 / 实证 / 数据审计研究。贡献(1) 撤回、贡献(2) 撤回 withheld、贡献(3) withheld；P2/P3/P4 正式且永久取消；`real=0`；投稿暂缓。

---

## 0. 本轮重写范围

- `papers/readkv_v2_draft/main.tex`：重写摘要 / 引言 / 贡献段 / 结果段 / 讨论·限制·结论；新增相关工作（正面引用并区分 CacheLink、KV-Lingo、Heo、Does Accuracy Equal Evidence、Contrast Sets、Kaushik、Kapoor-Narayanan 及 addendum N1–N9）；修正 S4/S5；更新表格（干净 affine 三 seed、kd 三 seed、前后对照、数据修复、SQuAD 锚点）；删除机制热图与方法消融图。
- `papers/readkv_v2_draft/notes.md`（本文件）：权威数值清单、投稿暂缓、venue、署名、引用核验状态、v2.6 处置、R2 cover letter 声明状态。
- `papers/readkv_v2_draft/cover_letter.md`：TMLR cover letter（R2 路线），署名 Zhang Xuein \<zxm0813@gmail.com\>，含 N1–N9 标题/arXiv/年份级核验声明与全部限制披露。

**未写 / 未改**：任何代码、`reports/runs/**`、`configs/prereg/**`、冻结判据；未重算统计。

---

## 0.1 紧急纠正：v2.6 AI 数据全部撤回（已修正）

- `docs/decisions/ai_dataset_final_ruling.md`（最终裁定）：撤回原「有条件 GO」；v2.6 冻结但 **not activated**；**不创建 `data/generated/`**；不写任何 human-seeded / model-generated 数据集及其结果。
- **本稿已修正**：删除原「v2.6 AI 数据作为额外探针」的预留结果表与表述；外部效度只写 `real=0` 受阻披露 + SQuAD（必要时 ARC）锚点的有限外部效度。
- 论文仅在 §「Data correctness…」与 data-availability 语境如实写一句「AI 生成数据集提案已评估并撤回（not activated），无遗留产物」；**不含任何生成数据结果**。notes.md 图表清单中的 v2.6 结果位同步删除。

---

## 0.2 P5 终审 CONDITIONAL GO 三项修复（本轮已完成）

> 依据：审稿人最终审计（P5 CONDITIONAL GO）。只改 `main.tex` 与 `notes.md`；未改代码 / 数据 / 判据 / 运行产物，未重算统计。

1. **R1（阻塞项）CI 口径并列 — 已修复**：`tab:cleanmvp` / `tab:cleankd` 现并列两套 95% CI，均逐字转抄自 **`reports/bootstrap_summary.json`（当前权威值）**：
   - 主 CI = `template_family` 簇级（`n_clusters=8`、`exploratory=true`、更宽）；敏感性 = pair-level（较窄）；表注明确「v2.3 下 template_family 为主 CI，pair-level 并列报告、绝不单独使用」。两套下界均 >0，**不推翻情形 C**，仅修统计口径。
   - affine joint：seed0 6.900 主 [3.564,10.100] / 敏 [5.496,8.321]；seed1 8.159 主 [4.357,11.584] / 敏 [6.648,9.701]；seed2 8.540 主 [5.326,11.610] / 敏 [7.046,10.051]。
   - kd joint：seed0 6.388 主 [3.653,8.814] / 敏 [5.340,7.400]；seed1 6.479 主 [3.899,8.798] / 敏 [5.431,7.529]；seed2 7.210 主 [4.417,9.799] / 敏 [6.074,8.331]。
   - **口径选择说明**：审稿人消息中援引的 kd seed1/seed2 主 CI（3.883/8.773、4.362/9.757）与其复算的略异版本，均非当前权威值；按指令以 `reports/bootstrap_summary.json` 为准，取 3.899/8.798、4.417/9.799。pair-level 列亦取自该文件的 `E_CF_pair_level_sensitivity`，与旧 `metrics.json` 的窄 CI 数值略有舍入差异。
   - dual / flip / cov. / transfer_broken 等联合报告指标均保留在两表中；§Results 的 kd 叙述同步改为双 CI。
2. **摘要压缩至 ≤200 词 — 已修复**：当前摘要 191 个渲染 token（<200，TMLR 合规），保留全部强制边界措辞：approaches but *not* exceeding controls、single-signal dual-drop、8 `template_family` clusters ($<24$) exploratory、single synthetic MVP pair、synthetic、sealed test never evaluated、contributions (1)(2) withdrawn / (3) withheld、primary endpoint unevaluated、no improvement。
3. **补齐可核验 bibitems — 已修复**：N1–N9 作者按主会话 arXiv API 核验结果补全（N1 Zhikun Tao / Fangyong Jin / Junping Zhao；N2 Adam Deng / Shicheng Liu / Yada Zhu；N3 Zhiwei Lin / Jiahao Liu / Yan Liu / Chengpeng Wang；N4 Yuzhe Liu / Haolin Tian / Tonghan Wang；N5 Abdulrahman Alabdulkareem 等 6 人；N6 Sreetama Sarkar 等 5 人；N7 Jiaming Cheng / Subhransu Das / Rajiv Ramnath；N8 Rishi Khare；N9a Povilas Kvedaras / Tomas Rasymas），bib 区块加注来源「verified by the main session via the arXiv API」；N9b（BridgeKV `2611.11761`）作者未独立核验，仍以 arXiv preprint 占位并注明。新增 SQuAD 两条 bibitem `squad16`（Rajpurkar et al., EMNLP 2016, doi:10.18653/v1/D16-1264）与 `squad18`（Rajpurkar, Jia et al., ACL 2018, doi:10.18653/v1/P18-2124），并在 §External anchor 正文 `\cite{squad16,squad18}`。N1–N9 均只写 arXiv preprint + 年份，未编造会议 / 期刊出处。

---

## 0.3 第二轮审稿（B 主要项 + A M1/M2/M4）修复（本轮已完成）

> 只改 `main.tex` 与 `notes.md`；未改代码 / 数据 / 判据 / 运行产物 / 数字。

1. **审稿 B 主要项（预算不对等，必须）— 已修复**：原 §Baselines 声称各臂 matched 含「trainable parameter count / training steps / tuning budget」，不成立。已改为「aligned on pairs / dtype/kernel / forward budget」，并**显式披露不对等**：affine = $0$ 参数、闭式 ridge、无梯度训练；kd_only = $7.34$M 参数、$8$ epochs（转抄 `p1_kd_clean_mvp_seed{0,1,2}/metrics.json` 的 `training.trainable_params=7340032` / `epochs=8`）。明确写「not a parameter- or step-matched ablation」，并在 §Conclusion 限制段同句披露。不再声称参数 / 步数 / 调参预算 matched。（摘要「matched kd_only baseline」为软性「对应基线」措辞，非预算对齐主张，保留以维持 191 词。）
2. **审稿 A M1（投稿状态）— 已修复**：header 注释、`\date{}`、引言末、结论末四处「submission deferred」改为与冻结签 off 一致：`Ready-to-submit (TMLR); P5 conditionally signed off`（`p5_final_signoff.md`；venue=TMLR 见 human_decisions 决策 5）；均保留「最终提交由真实 PI 本人完成、agent 不代为提交」的人工边界。
3. **审稿 A M2（章节级引用细节）— 已修复**：相关工作三处改为摘要级措辞——CacheLink/Heo 段改为「their reported abstracts state… / verified at abstract level only / make no claim about section-level diagnostic detail」，删除「four-arm K/V source-swap diagnostic」等章节级确证细节；N1–N9 段加「As reported in their abstracts」。保留全部引用键。未全文核验处一律保守。
4. **审稿 A M4（族数口径桥接 + 字数记账）— 已修复**：§datafix 新增一段桥接 56（corpus-wide `template_family` 数 = 24 基础结构 + 后缀变体；probe16/train16/val8/test16）与 8（单一评测 split=validation 的 `template_family` 簇数，即 v2.3 bootstrap 主聚类单元；$8<24$ → exploratory），说明同 taxonomy 不同 scope、非矛盾。摘要字数记账维持 **191 词**（全库无「171」残留）。

---

## 1. 权威数值清单（逐字转抄冻结产物，禁止重算）

### 1.1 干净 affine 三 seed（`p1_clean_mvp_seed{0,1,2}/metrics.json`，commit `efc3ba3`，val 60 对）

主 CI = `template_family`（n_clusters=8, exploratory, 更宽）；敏感性 = pair-level（较窄）；数值来自 `reports/bootstrap_summary.json`（见 §0.2）。

| seed | Joint E_CF | 主 CI (template_family) | 敏感性 CI (pair-level) | Self dual | Joint dual | flip | cov. | transfer_broken |
|---|---|---|---|---|---|---|---|---|
| 0 | 6.900 | [3.564, 10.100] | [5.496, 8.321] | 0.817 | 0.417 | 0.750 | 0.867 | true |
| 1 | 8.159 | [4.357, 11.584] | [6.648, 9.701] | 0.900 | 0.283 | 0.736 | 0.883 | true |
| 2 | 8.540 | [5.326, 11.610] | [7.046, 10.051] | 0.783 | 0.383 | 0.755 | 0.883 | true |

- seed0 控制组：mismatch 8.383、zero 8.584、random 6.765；info_attribution mismatch +1.483 / zero +1.684 / random −0.135；joint dual drop 0.4（≥0.2 阈值）；`joint_ecf_ge_control` 两个 false。
- **S4**：E_CF 大幅升高、**接近但未超过**错配 / 零缓存控制；禁写「达到 / 相当于无信息水平」。broken 定性由 dual 坍塌（单信号）支撑。
- E0 干净复验：`e0_clean_mvp_seed0`，cosine 1.0、KL 0、EM 0.975、round-trip bit-identical、zero_re_prefill、误差上限 2.2e-16。

### 1.2 干净 kd_only 三 seed（`p1_kd_clean_mvp_seed{0,1,2}/metrics.json`，commit `6413ba0`，val 60 对）

主 CI = `template_family`（n_clusters=8, exploratory, 更宽）；敏感性 = pair-level（较窄）；数值来自 `reports/bootstrap_summary.json`（见 §0.2）。

| seed | Joint E_CF | 主 CI (template_family) | 敏感性 CI (pair-level) | joint dual (drop) | flip | cov. | transfer_broken |
|---|---|---|---|---|---|---|---|
| 0 | 6.388 | [3.653, 8.814] | [5.340, 7.400] | 0.700 (0.117) | 0.942 | 0.867 | false |
| 1 | 6.479 | [3.899, 8.798] | [5.431, 7.529] | 0.733 (0.167) | 0.906 | 0.883 | false |
| 2 | 7.210 | [4.417, 9.799] | [6.074, 8.331] | 0.767 (0.017) | 0.925 | 0.883 | false |

- 情形 C：kd 不 broken、dual 0.70–0.77、**稳定非零 exploratory gap**；按 PI 终裁 **仅作探索性观察**，不恢复贡献(1)，不写「reproducible gap」。两套 CI 下界均 >0，**不推翻情形 C**。
- 口径已并列修复（P5 R1）：现主 CI 为 `template_family` 簇级、pair-level 作并列敏感性，取自 `reports/bootstrap_summary.json` 当前权威值；不再只用 pair-level，也不把 pair-level 当主 CI。元审查 §3.1 提示的旧复算值（3.883/8.773、4.362/9.757）为略异版本，以权威文件为准（见 §0.2）。

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
- 引用要求（`anchor_confirmation.md` §3）：Rajpurkar et al., EMNLP 2016（doi:10.18653/v1/D16-1264）与 Rajpurkar, Jia et al., ACL 2018（doi:10.18653/v1/P18-2124）。**已补入 bibliography**（`bibitem{squad16}` / `bibitem{squad18}`），并在 §External anchor 正文 `\cite{squad16,squad18}`。

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
- 状态：标题 / arXiv 号 / 日期真实；**章节级细节未核实**，引用进正式稿前须由真实 PI / 审稿人按 §9 做全文口径核验。
- **作者已补全（P5 R3）**：N1–N9 作者按主会话 arXiv API 核验结果填入 bibliography（详见 §0.2 第 3 项）；来源为「已由主会话 arXiv API 核验」，未独立读全文；N9b（BridgeKV `2611.11761`）作者未核，仍占位并注明。所有 N1–N9 只写 arXiv preprint + 年份，无编造的会议 / 期刊出处。
- SQuAD 引用（Rajpurkar 2016 / Rajpurkar-Jia 2018）**已补入 bibliography**（`squad16` / `squad18`，见 §1.5）。

---

## 6. 投稿状态 / venue / 署名

- **投稿状态（P5 CONDITIONAL GO → ready-to-submit）**：审稿人终审给出 CONDITIONAL GO，先后两轮修复全部完成——第一轮三项（CI 口径并列 / 摘要 ≤200 词 / 可核验 bibitems，见 §0.2）；第二轮 B 主要项（预算不对等显式披露）+ A M1（投稿状态）/ M2（章节级引用降为摘要级）/ M4（族数口径桥接 + 191 词记账，见 §0.3）。所有已知修复项均已消解；剩余仅为章节级引用细节的 §9 全文口径复核（不阻塞）。论文 header/`\date{}`/引言/结论均标注 `Ready-to-submit (TMLR); P5 conditionally signed off`；最终提交由真实 PI 本人通过 OpenReview 完成，agent 不代为投递。
- **venue：TMLR（真实 PI 已指定，2026-11-23）**。`docs/decisions/venue_recommendation.md` 首选 TMLR（次选 EASE 2027 RENE、ACL 2027 ARR）；理由：接受 modest contribution、对单模型对 / exploratory / 无方法贡献的证据强度最友好、Reproducibility Certification 契合。P5 已获附条件最终签off（docs/decisions/p5_final_signoff.md），进入 ready-to-submit。
- **署名（真实 PI 决策 6，已定）**：作者统一为 **Zhang Xuein \<zxm0813@gmail.com\>**；论文 `\author{}`、cover letter 与投稿元数据须一致。单作者原创，非会议扩写。
- **格式状态（P5 R2 已修复）**：摘要已压缩至 191 个渲染 token（<200，TMLR 合规），保留全部强制边界措辞（见 §0.2 第 2 项）。图 1–3 仍为文字占位，TMLR 投稿时可说明、接受后补齐。
- **cover letter（已成型文件）**：`papers/readkv_v2_draft/cover_letter.md`（TMLR，署名 Zhang Xuein \<zxm0813@gmail.com\>，venue=TMLR）。内容：① 负面 / 实证 / 数据审计定位，不宣称正向贡献；② 数据质量决定性影响（修复后「显著」发现翻转）+ 对通用读者的可复现审计方法论价值（避免 audience-too-narrow）；③ 干净数据上 affine 在 MVP 等深对的失败边界；④ 诚实披露全部限制——贡献(1)(2) 撤回、(3) withheld、主终点未评估、封存 test 未评测、real=0/M4 受阻、单合成等深对、8 簇<24 exploratory、锚点仅 exploratory_disclosure、无跨源/真实文档验证；⑤ 原创性声明（单作者原创、非会议扩写、不主张一般 utility/fidelity 区分或机制首创）；⑥ Reproducibility Certification 适用性（数据 SHA `f910f1f1…a894a`、commit 链 `efc3ba3`/`6413ba0`/`b7b9f50`、bf16/sdpa/zero re-prefill、脚本可重算；是否授予由编辑决定、不保证）；⑦ 最终提交由真实 PI 经 OpenReview 完成，agent 不代为投递。
- **R2 声明状态（最终落实计划 `final_implementation_plan.md` §2 R2，已落 cover letter）**：cover letter 含声明 "Related-work citations N1–N9 are identified by title/arXiv/version/date from public metadata; full-text reading was not completed at submission."；N1–N9 仅作存在性 / 标题 / 摘要级引用，未写章节级细节为已核实事实；KV-Lingo/CacheLink/SQuAD 仅元数据级核验。明确该核验级别限制**不影响本文核心贡献**（数据审计方法论 + 失败边界）。审稿人合规复核时确认正文无「章节级细节当已核实」表述。

---

## 7. 下一步（触发条件）

- **引用核验（P5 R3 已完成主体）**：N1–N9 作者已填、SQuAD 两条 bibitem 已补入并引用；**剩余**：章节级细节的 §9 全文口径复核（审稿人 / PI），不阻塞投递。
- **kd / affine v2.3 口径（P5 R1 已完成）**：两张表已并列 template_family 主 CI + pair-level 敏感性，取自 `reports/bootstrap_summary.json` 权威值；写作者未重算、未改数值。两套下界 >0，不推翻情形 C。
- **S1–S5 闭环**：S1 数据哈希绑定勘误、S2 manifest sha 同步、S3 runs_index 已闭环；S4/S5 本稿已写入；收尾后由审稿人出 P5 合规意见。
- **投稿状态**：引用已实际核验、口径与审稿复核（含锚点合规）均已完成、venue=TMLR 已指定、P5 已签off → **ready-to-submit**；由真实 PI 本人通过 OpenReview 提交（agent 不代为提交）。
- **不变量**：P2/P3/P4 永久放弃、不另立「修复 broken transfer」新课题；v2.6 not activated、`data/generated/` 不创建；封存 test 不碰；不恢复任何已撤回贡献。
