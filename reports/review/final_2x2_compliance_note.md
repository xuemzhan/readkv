# 2×2 补充实验 C1–C4 闭环 · 最终 Compliance Note

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 依据：前一审计 `reports/review/audit_2x2_formal_review.md`（C1–C4 发现）、`configs/prereg/gpu_followup_v2.7.yaml`、`reports/audit_2x2_l_ci.json`、`reports/audit_2x2_ci_fix_report.md`、`docs/audit_2x2_statistical_interpretation.md` v2、`reports/consistency_field_fix_report.md`、`docs/decisions/consistency_field_ruling.md`、`papers/readkv_v2_draft/{main.tex,cover_letter.md}`、commit 链。
> 当前 HEAD=`b69b9a9`。**范围**：核验 C1–C4 是否闭环 + 无回归，出 P5 重新签 off 建议。本轮未改代码/数据/prereg/论文/run 产物，审计输出定向 /tmp。

---

## 0. 总体判定

> **结论：C1 / C2 / C3 / C4 四项全部闭环 ✅。前次审计的两项主要问题（C1 统计口径、C2 因果措辞）及其余两项（C3 假阳性、C4 论文补稿）均已按 v2.7 落实，经独立复核与产物重算确认。**
>
> **P5 重新签 off 建议：GO（放行至 ready-to-submit）**——可交真实 PI 按 TMLR 流程提交，附 4 项非阻塞残余（§5）。最终提交动作（署名邮箱、OpenReview、版权/许可、AE/reviewer 建议）由真实 PI 人工完成，本 note 不代为投递、不定稿措辞。

---

## 1. 必做动作执行结果

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report --output /tmp/opencode/final2x2_bootstrap.json` | 成功，43 runs；仓库产物未改写 |
| `.venv/bin/python -m scripts.consistency_check --output /tmp/opencode/final2x2_consistency.json` | checked=43, **failed=22**（前次 34 → 22，12 假阳性消除） |
| prereg 完整性 | v2.1–v2.7 全部 TRACKED 且 `git diff HEAD -- configs/prereg/` = 空（未篡改）✅ |
| `pytest tests/test_consistency_model_pair.py` | 5 项通过（回归测试存在且通过）✅ |

---

## 2. C1–C4 闭环逐项核验

### C1 统计口径 — **已闭环** ✅

- **产物存在**：`scripts/audit_2x2_ci.py`、`reports/audit_2x2_l_ci.json`、`reports/audit_2x2_ci_fix_report.md` 均在；commit 链 `e9f5773→6c6b7d3→857ea56→0bf43ab` 与科学家判读 `b267efa` 在 git 历史中。
- **口径核验**（从 `audit_2x2_l_ci.json`）：12 格均含 `L_template_family_ci`（主）、`L_pair_level_sensitivity`（敏感性）、`joint_E_CF_template_family_ci`、`n_clusters=8`、`exploratory=true`、`unknown_family_pairs=0`；四项预固定对比 × 3 seed 均含 point/CI/n_clusters/exploratory/method 字段（对比① paired-by-sample_id、对比② unpaired 独立簇重采样，符合 v2.7 `cross_version_note`）。
- **独立复算**：A11_s0 的 L 主 CI 用 `version_tag+sample_hash` 关联 `fixed/val_seed0` 的 template_family、8 簇 10000 重采样得 **40.00 [16.67, 62.71]**，与产物逐字一致（pair-level 敏感性 [23.33,55.0] 较窄——报告以主区间为准，符合 forbidden 第 3 条）。
- **无窄 CI 冒充 / 无错误 exploratory 标记**：全 12 格 `exploratory=true`（8<24），未沿用旧 `delta_lock` 8 簇区间冒充、未只报 pair-level。✅

### C2 因果措辞 — **已闭环** ✅

- main.tex 全文 grep `manufactur / directly produc / caused by / sufficient to / produced the spurious` —— **零命中**；原强因果句已降级。现文采用「whole version switch, not any single defect」（101/143–144/367/571 行）、表题 "Before/after corpus-version contrast (**descriptive**; not single-defect…)"（571 行）。cover letter 亦无强因果措辞（零命中）。符合 v2.7 §3 `causality_wording_rule` 与科学家 v2「撤除 single-defect manufactured/directly produced」要求。✅

### C3 假阳性 — **已闭环** ✅

- `scripts/consistency_check.py::_check_model_pair` 已扩展识别 `calibration_version/validation_version` → 推断 MVP 对等深对（按字段、不硬编码 run_id）；5 项回归测试（`tests/test_consistency_model_pair.py`）通过，pytest 58 passed 与报告一致。
- **重跑确认**：12 格全部 `ok=true / traceable=true / infer_2x2=true`；failed 从 34 降至 22，22 个失败**全部为 superseded 历史 run**（无其它判定变化），与前次「其余 31 run 判定零变化」一致。✅

### C4 论文补 2×2 — **已闭环** ✅

- main.tex 新增 `\subsection{Controlled 2×2 corpus-version contrast (exploratory)}`（sec:audit2x2，702 行）+ 表 `tab:audit2x2`（718–736 行），数值逐字转抄 `audit_2x2_l_ci.json`/`formal_summary`，全部标 exploratory、8 簇<24；明确 mixed_interaction（不升级 calibration_version_effect，752–753 行）、归因边界（whole version switch / 单项缺陷不可归因，755–761 行）、贡献状态不变（767 行）。commit `3386e56`、`b69b9a9` 在历史。✅

---

## 3. 无回归核验（贡献/定位/统计）

| 项 | 状态 | 证据（main.tex 行号） |
|---|---|---|
| 贡献(1)(2) 撤回、(3) withheld | ✅ 无回归 | 18–19、68、88、595、660、767、829–831 |
| 主终点（paired E_CF vs kd_only，CI 上界<0）未评估 | ✅ | 71、153、467、473、658–659、830 |
| 封存 test 从未评测 | ✅ | 68、424、473、786、831 |
| real=0 / M4 blocked / 真实文档外部效度未验证 | ✅ | 154–155、390–405、418–419、792–795 |
| SQuAD 锚点 exploratory_disclosure（kd 对照未复现、EM floor、单 seed/240、无跨源） | ✅ | 145–149、663、698–699 |
| P2/P3/P4 永久放弃 | ✅ | 19、154、283、298–299、658–659、830–831 |
| v2.6 AI 数据 withdrawn / not activated | ✅ | 28–30、209–211、407–409、794 |
| TMLR / 署名 Zhang Xuein \<zxm0813@gmail.com\> | ✅ | 42–43、156、847 |
| 单一合成等深对、无跨对/真实世界/强显著主张 | ✅ | 128、418、786–787、836 |

**结论**：全部保持不变，无因 2×2 结果而恢复贡献或强化叙事。

---

## 4. 对论文因果措辞的放行建议

- **放行**：现在 main.tex 的因果措辞（整体版本切换受控观察 / 描述性翻转 / mixed_interaction / 归因边界）符合 v2.7 §3，可放行；新增 2×2 段的「方向稳健」表述严格限定为「点估计跨 seed 同号」，未写「CI 确认显著」，符合科学家 v2 §1.3/§4 纪律。
- **不放行**：任何恢复 "data defects manufactured / directly produced / caused by / sufficient to" 单项因果、声称 CI 确认方向稳健/显著、升级 calibration_version_effect、恢复贡献(1)(2)/声称(3)、跨源/真实世界泛化的措辞——v2.7 forbidden 与 §3 归因边界持续禁止。

---

## 5. 残余非阻塞项（供 PI 知悉，不影响投稿）

| 编号 | 项 | 等级 | 说明 |
|---|---|---|---|
| N1 | main.tex 第 746 行把 A10−A00 写作 "fixed-validation calibration contrast" | 次要（标签笔误） | A00/A10 均用 **legacy** val，正确应为 "legacy-validation calibration contrast"（A11−A01 才是 fixed-val）。数值与 CI 正确（legacy val A10−A00 三 seed 下界≥0），仅对比名称前后颠倒，易误导读者；建议写作者一行修正。不影响统计结论。 |
| N2 | 多重比较未见 Holm 校正（4格×3seed + 4对比×3seed） | 次要（披露） | 科学家 v2 §6.4 已列为统计风险；全部 exploratory，不作强推断；建议在限制段一句披露（若尚未写）。 |
| N3 | L 尺度颗粒度 1/60≈1.67 pp、20 pp 历史阈值仅参考 | 次要（披露） | 科学家 v2 §6.5 已记；正文表注可保留说明。 |
| N4 | 对比②为非配对独立簇重采样，与①配对口径不同 | 次要（披露） | `l_ci.json::predeclared_contrasts.method` 已逐项标注，审稿/科学家解读已声明不可直接比较区间宽度；正文若展示对比 CI 应附此说明。 |

均为披露/标签层，不构成投稿阻塞，无需重新审计。

---

## 6. P5 重新签 off 建议与前置条件

- **建议：GO（放行至 ready-to-submit）**。C1–C4 全部闭环，前次审计的两项主要问题已解决，无贡献/定位/统计回归，prereg 未篡改，审计脚本修复无副作用。
- **前置条件（均已满足，留档用）**：① C1 统计口径合规（template_family 主 CI + 8 簇 exploratory + L 对比 CI + 两项敏感性方法标注）；② C2 因果措辞按 v2.7 降级；③ C3 假阳性修复且旧判定零变化；④ C4 论文补 2×2 段且贡献不变量无回归。
- **交真实 PI 的人工动作**（本 note 不代为执行）：修正 N1 标签笔误（建议）、披露 N2–N4（建议）、确认署名邮箱、TMLR OpenReview 账号提交、版权/许可声明、cover letter、AE/reviewer 建议。
- **不触发**：无实现 bug、无判据篡改、无 mock 混入、无贡献升格、无 Oracle 泄漏；无需停冻结或重跑任何实验。

---

## 7. 结论

C1（统计口径补算）、C2（因果措辞降级）、C3（consistency 假阳性修复）、C4（论文补 2×2 段）四项经文件/commit/产物核验与独立 CI 重算确认**全部闭环**；重跑两审计脚本（输出 /tmp、仓库产物未改）确认 12 格 ok=true、22 失败全为 superseded、prereg v2.1–v2.7 未篡改；论文贡献(1)(2) 撤回/(3) withheld、主终点未评估、real=0、锚点 exploratory_disclosure、P2/P3/P4 永久放弃、TMLR/署名均无回归。**P5 重新签 off 建议 GO（放行至 ready-to-submit）**，附 4 项非阻塞残余（N1 标签笔误 + N2–N4 披露）。真实 PI 人工提交动作与措辞定稿不由本 note 代替。

**签署：reviewer（对抗性审阅），2026-11-23。**
