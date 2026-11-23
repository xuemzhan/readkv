# P5 封面信措辞上限裁决（M3 收口：以论文自我限定为界）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：paper-reviewer-a 终审 `reports/review/paper_a_final.md` §2 M3 指出 `docs/decisions/p5_final_signoff.md` §4.2 第 1 条「普适贡献定位：强调可复现的数据审计方法论……避免被判 audience too narrow」存在把贡献**升格为"通用审计方法论"**的措辞风险，与论文 `papers/readkv_v2_arxiv/main.tex:813-816`（及草稿版对应结论段）的自我限定冲突。
> 依据：`reports/review/paper_a_final.md` §1.4/§2 M3/§4 第 3 条；`papers/readkv_v2_arxiv/main.tex:803-823`（Conclusion & Limitations）、`:168-172`（新颖性限定）、`:100-101,:127-132`（负面结果定位）；`docs/decisions/{p5_final_signoff,final_boundary_study_signoff,research_scope_update}.md`；`docs/protocol.md §10`。
> 本裁决**只写决策文档**：不改 `src/**`、`reports/runs/**`、已冻结判据、数据、`papers/**` 论文源文件或任何既有决策文档原文；不写代码、不跑实验、不润色论文正文。

---

## 1. 核心裁定

> **封面信（cover letter）的一切措辞，严格以论文 §Conclusion and Limitations / `main.tex:813-816` 的自我限定为唯一上限。** 审计工作只能定位为「**具体预注册翻转案例 + 成对反事实 E_CF 审计轨迹 + 诚实负面结果**」；TMLR 契合点只写「**reproducibility study / negative empirical result**」；modest contribution 如实披露。**禁止**任何"通用/普适数据审计方法论""general method / new audit method""跨源普适性 / general leakage lesson"升格表述。

论文自我限定原文（封面信不得越过此线，`main.tex:813-816`）：

> "We make \emph{no} claim of a general counterfactual gap, a receiver-side mechanism, a general utility/fidelity distinction, a mechanism-layer first, or any method improvement; **nor do we claim a new audit method or general leakage lesson**."

新颖性限定原文（`main.tex:168-172`）：

> "our contribution is \emph{not} a general distinction, a mechanism-layer first, or a new audit method, but **a specific preregistered reversal case with a paired counterfactual E_CF audit trail**."（限于 one synthetic benchmark）

---

## 2. 可写 / 禁写清单

### 2.1 可写（cover letter 允许且鼓励）

1. **具体案例定位**："a concrete preregistered before/after data-repair reversal case on one synthetic cross-model KV-transfer benchmark, with a paired counterfactual `E_CF` audit trail."
2. **诚实负面结果**：数据缺陷（退化对、跨 split 逐字泄漏、模板骨架重合、簇退化）制造了统计上可信但虚假的正向发现，修复后结论翻转；这是一条失败边界 / 数据教训的负面实证结果。
3. **TMLR 契合点**：仅写 "a **reproducibility study / negative empirical result** that reveals how common data-quality defects can invert benchmark conclusions"——对应 TMLR "revealing strengths/weaknesses of methods / reproducibility" 的实验研究范畴；**不得**因担心 audience too narrow 而升格为一般性方法贡献。
4. **贡献状态如实披露**：贡献(1) 撤回、贡献(2) 撤回、贡献(3) withheld；affine 失败边界 + kd 情形 C 仅探索性观察；单合成等深对、`real=0`、8 族 exploratory、封存 test 未评、主终点未评估、SQuAD 锚点 `exploratory_disclosure`。
5. **可复现性陈述**：固定数据 SHA（`f910f1f1…a894a`）、commit 链、预注册（v2.1–v2.6）、已归档的权威 run 与 GPU 数据导出（`reports/data/gpu_experiments/v1/`）；Reproducibility Certification 仅"如实主张适用性"，由编辑决定，不保证获得。
6. **原创性与署名**：原创（非会议扩写）、单作者 Zhang Xuein。

### 2.2 禁写（cover letter 一律不得出现）

- ✗ "a **general / universal data-audit methodology**""a **new audit method**""a **general leakage lesson**"——与 `main.tex:813-816` 直接冲突；
- ✗ "a **general method**""**general** utility/fidelity distinction""**general** counterfactual gap"——论文明确否认；
- ✗ "**cross-source universality / 跨源普适性**""真实文档外部效度已验证""generalizable across models/domains"——违反边界披露；
- ✗ 任何已撤回贡献的恢复、机制定位、"reduces gap / improves over baselines / method improvement"；
- ✗ "strong significance / robust across pairs"——clean 结论均为 exploratory。

---

## 3. 对既有决策文档的约束关系

- `p5_final_signoff.md` §4.2 第 1 条「**普适贡献定位**」措辞**作废**，以本裁决为准。为保持历史决策可读，**不回写** `p5_final_signoff.md` 原文；两者并存时，封面信措辞以本裁决为最终上限。
- `p5_final_signoff.md` §4.2 其余各条（诚实披露 modest、Reproducibility Certification、原创性、署名、AE/reviewer 建议清单）继续有效，但凡与 §2 冲突处一律以 §2 为准。
- 本裁决与 `research_scope_update.md` §6 引用纪律、§1.3 不可变边界、`docs/protocol.md §10` 贡献门槛一致；不恢复任何贡献、不改论文正文、不改冻结判据。

---

## 4. 给各角色的指令

- **写作者（writer）**：正式 cover letter 以 §2 清单撰写；用 §2.1 第 1/2/3 条作为定位句，逐条自检 §2.2 禁写词零命中；以 `main.tex:813-816` 与 `:168-172` 为逐句对照上限；不因 audience 顾虑升格。`notes.md` 既有封面信草稿第①条「不宣称正向贡献」定位正确，可沿用并补入本裁决措辞上限。
- **真实 PI（人工）**：cover letter 与 AE/reviewer 建议由真实 PI 终审；若对 audience 定位有顾虑，只能在 §2.1 允许范围内权衡，不得据此越过 §2.2 红线。
- **论文审稿 A / B**：本裁决即对其 M3（A §2）的 PI 处置记录；请在其合规意见中确认封面信措辞上限已据此确立，无残留升格风险。
- **文档工程师（doc-engineer）**：可在 README / 可复现文档中如实引用本裁决为"封面信措辞上限"来源；不改论文与冻结判据。

---

## 5. 结论

> **M3 已由 PI 收口**：cover letter 措辞上限 = 论文 §Limitations / `main.tex:813-816`——「具体预注册翻转案例 + 成对反事实 E_CF 审计轨迹 + 诚实负面结果」，TMLR 契合点仅 "reproducibility study / negative empirical result"，modest contribution 如实披露；`p5_final_signoff.md` §4.2「普适贡献定位」措辞作废（以本裁决为准、原文不回写）。不恢复贡献、不改论文正文、不改冻结判据、不伪造。

**签署：PI / 课题组长（P5 封面信措辞上限裁决 · 2026-11-23）**
