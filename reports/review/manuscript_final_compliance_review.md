# 最终稿件独立合规复核（第二轮复审定向大修关闭情况）

> 审稿人：reviewer（readkv 独立质量守门人）。日期：2026-11-24。
> 更新：复核期间 writer 两次更新稿件——arxiv 先同步为描述性版本，随后把第 1127 行裸 `E_CF`
> 修为 `$E_{\mathrm{CF}}$`（mtime 04:18Z）。本 note 以复核结束时落盘状态为准。
> 对象：`papers/readkv_v2_draft/{main.tex,cover_letter.md,notes.md}`、
> `papers/readkv_v2_tmlr_anonymous/main.tex`、`papers/readkv_v2_arxiv/main.tex`、
> `docs/audit_seq_statistical_interpretation.md`、`docs/decisions/sequence_scoring_baseline_ruling.md`、
> `reports/review/independent_research_and_manuscript_review_2026-11-24.md`、
> `reports/review/sequence_scoring_compliance_note_b0.md`。
> 性质：**只读独立复核**；未重跑 GPU、未改任何文件（仅新增本 note）。
> **编译能力声明：本机无 tectonic / pdflatex / xelatex / lualatex / bibtex，以下编译相关检查全部为静态检查，
> 不签为「编译验证通过」；~103 pt / ~386 pt 横向溢出须在可编译环境复核。**

---

## 0. 总判定

| 项 | 结论 |
| --- | --- |
| ① 编译致命错误 | draft/anon/arxiv 静态 PASS（arxiv 裸 `E_CF` 在复核中已被 writer 修复）；本机无编译器，全部仅静态、不签编译通过 |
| ② 2×2 表注/权重/计数/交互 | PASS（draft/anon/arxiv） |
| ③ 因果措辞统一 | PASS（draft/anon/arxiv 内容均已描述性化） |
| ④ 指标口径 | PASS（draft/anon/arxiv） |
| ⑤ `_b0` 序列评分入稿 | PASS（draft/anon/arxiv，仅 `_b0` 权威 id） |
| ⑥ 元数据 | PASS（含如实标注未核），1 处非阻塞披露不一致 |
| ⑦ 匿名稿 | PASS |

> **P5 新签 off 合规意见：CONDITIONAL GO（条件放行）。**
> R1–R4 已关闭（B0 基线 + scientist `docs/audit_seq_statistical_interpretation.md` 分支①预承诺归类），
> 第二轮复审定向大修在 draft / 匿名稿 / arxiv 三稿上已按静态检查逐项关闭，三稿数值一致、因果措辞统一，
> 三稿文本模式均无裸 `E_CF`、无裸下划线、`\begin`/`\end` 与表格列数静态核对通过。
> 但本机无编译器，**全部为静态检查，我不签「编译验证通过」**；~103/~386 pt 横向溢出须在可编译环境复核。
> 故最终重新签 off 前须满足 §4 条件（尤其实际编译 + PI 新出签 off）。按裁决 §4/§6，
> 最终签 off 由 PI 新出（不改写旧 `p5_final_resignoff.md`），本实验与稿件修订均不替代投稿前的人工复核环节。

---

## 1. 逐项核对

### ① 编译致命错误 —— draft/anon PASS（静态）；arxiv PENDING；全程静态、非编译验证

- draft 原第 753 行 `\texttt{mixed_interaction}` 裸下划线 → 现为 `\texttt{mixed\_interaction}`（第 857 行）；
  全文文本模式无裸 `E_CF`（正文均为 `$E_{\mathrm{CF}}$`）；`\begin`/`\end` 32/32 平衡；11 个 `tabular`
  列数与列定义逐表吻合（静态脚本核对，0 不符）。→ 静态 PASS。
- anon：文本模式无裸 `E_CF`；`\begin`/`\end` 24/24；10 个 `tabular` 列数 0 不符。→ 静态 PASS。
- **arxiv**：内容已同步（标题改描述性、无 `manufactured`/`preserves utility`/`zero trainable` 等旧措辞，
  2×2、`_b0`、SQuAD 数值齐全）。复核中曾发现第 1127 行 `\textbf{E_CF is not quality.}` 裸下划线
  （复审 §2.3「arXiv 792 行裸 `E_CF`」同一问题，行号漂移）；**writer 于 04:18Z 修为
  `\textbf{$E_{\mathrm{CF}}$ is not quality.}`**。复核结束态：arxiv 文本模式裸 `E_CF`=0、裸下划线=0，
  `\begin`/`\end` 34/34。→ 静态 PASS。
- **静态检查限制**：未实际编译；列数/环境配对为启发式静态核对，不能替代 Tectonic；复审记录的横向溢出
  （draft ~103 pt、arxiv ~386 pt）未复核。我不签编译通过。

### ② 2×2 表注/权重/计数/交互 —— PASS

- 表注（draft 778–781 / anon 407–410 / arxiv 787–788）：**A00/A10 用旧 val、A01/A11 用修复版 val**，
  首索引=校准、次索引=验证 ✓。
- 权重（draft 795–825 / arxiv 808–833）：点估计按 60 对样本加权；跨验证对比采用样本加权主口径
  （每个抽中族之和÷抽中样本数），**族等权作敏感性**并同时给点差（A01−A00 seed0 23.2 vs 25.0）✓。
- 计数：正文/anon/arxiv 均写 **12 项预定对比（not nine；nine = 含修复版数据的单格数）**，
  A01−A00 跨零 1/3、A11−A10 跨零 2/3、**合计 3/6**，「in most seeds」明确替换为计数 ✓。
- 交互（draft 848–858 / arxiv 861–863）：−23.3[−47.6,3.4]/+5.0[−22.9,31.0]/−15.0[−44.0,16.1]，
  **三个区间均跨零**，判读 mixed_interaction，不升级 ✓。
- 非阻塞次要：cover letter 第 71 行仍写「most contrast intervals cross zero」未给显式计数（正文已给 3/6），
  建议同步为「3 of 6」；不影响核心统计结论。

### ③ 标题/摘要/投稿信/正文因果措辞 —— PASS

- 标题三稿一致为描述性「A Finding Reversed After Corpus Reconstruction: A Controlled Version-Contrast Study…」；
  摘要与 cover letter 不再称机制/gap 被追溯到具体缺陷并消失 ✓。
- 机制状态统一：旧机制**证据撤回**、清洁数据下是否存在**未决**（无 clean P2）；cover letter 第 24–27 行、
  摘要第 70–72 行明确 ✓。
- 无通用审计方法/贡献恢复：cover letter 第 43–46、108–112 行显式否认 general audit method / 新指标 /
  utility-fidelity 首创 / 一般泄漏教训；正文无单项缺陷强因果肯定用法 ✓。
- 区分冻结的 v2.7/v2.8 交叉实验与结果后形成的审计问题：正文与 scientist 文档均明示 ✓。

### ④ 指标口径 —— PASS

- 398 = **语料级** must-flip 计数（排除 F5/F6），与验证格候选分母、Self 阈值后分母**三分母分列**
  （draft 322–332 / arxiv 对应段）；A11 flip 分母 34/45、35/46、34/46 ✓。
- 首 token **二选一代理**（Section metrics，draft 469–471）；F5 相同候选→代理误差 0、dual=1、排除；
  F6 **改姓名且改金标签**、排除（draft 334–342）✓。
- KD 效用语言：不写 preserves utility；全切片 dual 差 11.7/16.7/1.7、F1–F4 seed1 21.7、对切片敏感、
  exploratory（draft 摘要/引言/§kdbase；arxiv 同步）✓。
- affine **零梯度优化 epoch**、闭式 ridge 仍从校准估计约 7.4M 系数；kd 7.34M 参数/8 epochs，
  明确「not parameter- or step-matched」（draft 522–532）✓。
- SQuAD：明确标**单参考子集**（前 240 可回答/两篇/首参考答案），并引复审全参考重算
  F1≈0.2178/0.0082/0.0014、EM 全零（draft 710–725；arxiv 727–754）✓。

### ⑤ `_b0` 序列评分入稿 —— PASS

- 仅引用六个权威 `_b0` 正式格 `audit_seq_{A11,A00}_s{0,1,2}_b0`（draft 883–886 / anon 445–446 /
  arxiv 893–894），旧 id 标 superseded、不作证据 ✓；`reports/runs_index.json` 9 旧 id 非权威、6 `_b0` 权威（前 note 已核）。
- 主分析 F1–F4 数值（A11 full L +0.4783/+0.4348/+0.5217；A00 42/42/41、A11 46/46/46；
  cell_diff、reading_diff、reading_of_diff 三套 CI）与 scientist `docs/audit_seq_statistical_interpretation.md`
  §2.1/§3.1/§3.2/§3.3 **逐值一致**；全 60 对 8 族作敏感性 ✓。
- 分支①措辞不升级：仅「两种候选评分下点估计方向一致」，报告幅度与区间、标 exploratory；
  A11 s1 reading_diff 主区间不含零但 L_full 仍正、cell_diff 未消失→不触发②，归一不改判读→不触发③ ✓。
- 两套口径差异如实登记（primary F1–F4 6 族 vs 全 60 对 8 族，A11 s0 first +0.4348 vs +0.3833，
  分母不同非分数不一致，方向/分支不变）✓；E_CF 不跨口径比较 ✓。

### ⑥ 元数据 —— PASS（含如实标注未核），1 处非阻塞披露不一致

- Contrast Sets：Gardner 等完整作者表，Findings EMNLP 2020、arXiv:2004.02709、doi:10.18653/v1/2020.findings-emnlp.117，
  notes §5.1 记一手核验 ✓；Heo 等：T. Heo 等完整作者表、arXiv:2608.03893 ✓。
- BridgeKV：完整 bibitem（P. Behnam 等，arXiv:2611.11761，submitted 9 Nov 2026），cover letter 显式披露
  「N1–N9 作者由 arXiv API 元数据补全、未通读全文」→ 属「如实标注未核」✓。
- 非阻塞不一致：notes §5.2 仍写「N9b BridgeKV 作者未独立核验、仍占位」，但 bibitem 已列出完整作者；
  cover letter 对 N1–N9 作者作统一「API 补全」披露。建议 writer 统一措辞（要么更新 notes、要么回退 bib 占位），
  不影响核验级别披露的实质。

### ⑦ 匿名稿 —— PASS

- `\author{Anonymous Author(s)}`、`\date{}`；无作者邮箱/自致谢/自引身份泄露（正文无 `zxm0813`/`Zhang Xuein`/`@gmail`，
  仅注释说明双盲约定）✓；自包含（标准宏包、无外部 .sty、无硬编码 `/root/readkv`）✓。
- 与 draft 数值一致：2×2 表、`_b0` 三表、SQuAD、样本加权/3-of-6/12-contrasts 均逐值对齐 ✓；
  摘要约 184 渲染词（<200）三稿一致 ✓。

---

## 2. R4 关闭确认

`docs/audit_seq_statistical_interpretation.md` 已产出：预承诺声明、三分支逐条核对、归类①
`consistent_across_scoring`、三项比较三套 CI、与 `summary_b0`/handoff 的两套口径差异登记、可复算脚本齐备；
前 note 的 R4 OPEN 已关闭。分支归类无事后择支、无贡献恢复、无单项因果。✓

## 3. 非阻塞残余项（不阻止条件放行，须如实披露）

1. 本机无编译器，三稿均为静态检查；~103/~386 pt 溢出待可编译环境复核（放行条件项，非稿件缺陷）。
2. cover letter「most contrast intervals」未给 3/6 显式计数（次要措辞）。
3. notes §5.2 与 bibitem 的 BridgeKV 作者核验状态措辞不一致（次要披露）。
4. SQuAD 单参考 240 例子集、图 1–3 文字占位、N1–N9 未通读全文——均已如实披露，非新阻塞。

## 4. 放行条件（CONDITIONAL GO 的前置）

1. 在可编译环境用 Tectonic/pdflatex 实际编译 draft、anon、arxiv 三稿，确认无致命错误并复核横向溢出
   （本复核仅静态，无法替代；三稿静态裸 `E_CF`/裸下划线/环境/列数已通过）。
2. PI 据最终稿本**新出**重新签 off（不改写旧 `p5_final_resignoff.md`）；venue=TMLR、署名不变，
   最终由真实 PI 经 OpenReview 提交，agent 不代投。
3. （建议）writer 把 cover letter「most contrast intervals」改为「3 of 6」，并统一 notes §5.2 的
   BridgeKV 作者核验措辞与 bibitem。

> 边界重申：本 note 仅做稿件与文档的静态合规核对，未重跑 GPU、未改任何文件、未重算统计量；所列数值均来自
> 冻结产物与 scientist/复审复算的转抄一致性核对，无 mock 数字。稿件修订与本实验均不改变贡献撤回/withheld、
> 主终点未评估、封存 test 未评测、P2/P3/P4 永久放弃、real=0 的边界。
