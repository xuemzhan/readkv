# 2×2 GPU 补充实验统计解读（v2.7 预承诺判读）—— 修订版 v2

> 角色：科学家（统计设计与解读）。日期：2026-11-23。
> **修订说明（v2，取代 v1 的 §1.1 / §1.4 / §2.2 / §3 后半 / §4 / §5 相关结论）**：v1 曾指出 `reports/audit_2x2_bootstrap.json` 缺 L / 对比 CI 且 12 格误用 `cluster-fallback`/60 逐对簇（`exploratory=false`）。工程师已按 v2.7 主口径补算，新增 `reports/audit_2x2_l_ci.json`、`reports/audit_2x2_ci_fix_report.md`、`scripts/audit_2x2_ci.py`（commit 链 `e9f5773 → 6c6b7d3 → 857ea56 → 0bf43ab`）。本修订版**直接引用补算产物**，关闭 v1 所述缺口；不重算 CI、不改产物。
> 边界：只写本 `docs/` 文档；不改数据、代码、prereg、论文；不跑实验；不编造数字。数值均引自 `reports/audit_2x2_l_ci.json`、`audit_2x2_ci_fix_report.md`、`audit_2x2_formal_summary.json`、`engineer_status.md §16`、`configs/prereg/gpu_followup_v2.7.yaml`。

---

## 0. 判据与执行前提（不变）

- 设计：2×2（校准语料版本 old 458de18 / repaired efc3ba3 × 验证语料版本 old / repaired），3 seed，12 格；主指标 `L = Self 双侧正确率 − Joint 双侧正确率`（百分点）；主 CI = `template_family` 簇级 bootstrap 10000 + pair-level 敏感性；`n_clusters=8 < 24` → **全部 12 格 `exploratory=true`**（v2.7 §2，`audit_2x2_l_ci.json`）。
- 判读纪律：v2.7 §3「结果前锁定四分支、对号入座、禁止事后择支」；`causality_boundary`、`causality_wording_rule` 全部适用。
- 执行完整：12 格全部 attempt 1、0 失败；对角格 A00≡`p1_gpu_mvp_repro`、A11≡`p1_clean` 各 60/60 joint E_CF 逐对完全一致；`consistency_check` 的 `ok=false` 为 `model_pair` 字段契约假阳性（非数据/指标错误）。

---

## 1. 补算后的完整 CI（关闭 v1 口径缺口）

### 1.1 L 主 CI（template_family，8 簇，exploratory=true，单位 pp）

| 格 | s0 | s1 | s2 |
|---|---|---|---|
| A00 | +1.67 [−3.33, 7.02] | −5.00 [−15.25, 6.67] | +3.33 [0.00, 10.34] |
| A11 | +40.0 [16.67, 62.71] | +61.67 [38.33, 83.05] | +40.0 [20.34, 58.73] |
| A01 | +26.67 [1.69, 48.39] | +28.33 [9.84, 48.28] | +33.33 [11.67, 54.84] |
| A10 | +38.33 [15.79, 57.38] | +23.33 [6.90, 38.33] | +25.0 [3.39, 43.55] |

要点：**A11 / A01 / A10 九格 L 主 CI 下界 > 0**（含修复数据的格）；**A00 旧对角格三格 CI 围绕 0**（s0/s1 跨 0，s2 下界=0）。每格另附 pair-level 敏感性（如 A11_s0 [23.33, 55.0]），与模板族主区间同号、较窄——**报告时须以模板族主区间为主、pair-level 仅作敏感性**（v2.7 forbidden_after_freeze 第 3 条）。joint E_CF 主区间亦已补正（如 A11_s0 6.900 [3.564, 10.100]），不再沿用逐对簇冒充独立样本。

### 1.2 两项预固定对比 CI（四项 × 3 seed，单位 pp）

**① 固定 val 换校准（同 val 按 sample_id 配对、按模板族重采样）：**

| 对比 | s0 | s1 | s2 | CI 层面 |
|---|---|---|---|---|
| legacy val：A10−A00 | +36.67 [15.52, 54.84] | +28.33 [13.79, 42.37] | +21.67 [0.00, 41.27] | **3/3 下界 ≥0**（s2 恰为 0.0，压线） |
| fixed val：A11−A01 | +13.33 [−1.64, 30.0] | +33.33 [10.0, 55.17] | +6.67 [−14.52, 28.81] | **仅 1/3 下界>0，s0/s2 跨 0** |

**② 固定 mapper 换 val（跨版本 val 为不同样本集，按 v2.7 `cross_version_note` 用两独立 val 各自模板族簇重采样的均值差，非配对）：**

| 对比 | s0 | s1 | s2 | CI 层面 |
|---|---|---|---|---|
| legacy cal：A01−A00 | +25.0 [−2.46, 46.21] | +33.33 [10.49, 54.69] | +30.0 [6.69, 51.56] | 2/3 下界>0，s0 跨 0 |
| fixed cal：A11−A10 | +1.67 [−29.24, 31.70] | +38.33 [10.27, 64.73] | +15.0 [−12.72, 43.75] | 1/3 下界>0，s0/s2 跨 0 |

（`ci_fix_report.md §2` 与 `audit_2x2_l_ci.json::predeclared_contrasts` 一致；对比② attempt1 因跨版本 sample_id 无交集失败，attempt2 改非配对独立簇重采样成功，日志留痕。）

### 1.3 "方向稳健"的精确表述（关键纪律）

- **点估计层面**：两项对比 12 个点估计**全部为正**，跨 3 seed 同号成立 → 只能写"点估计跨 seed 同号"。
- **CI 层面**：方向稳健**仅在部分对比成立**——仅① legacy val A10−A00 三 seed 下界均 ≥0（s2 压线 0.0）。① fixed val、② 两项对比多数 seed 的 CI 跨 0。
- **禁止**写"CI 确认方向稳健 / 全部显著 / 稳健为正"。全部 12 格 `exploratory=true`（8 族 < 24），任何区间结论均为探索性描述，不作强显著性推断。

---

## 2. 四分支判读（维持 mixed_interaction，不升级为 calibration_version_effect）

### 2.1 结论：**维持 `mixed_interaction`（主）；`whole_version_only` 仍为不可突破的归因边界**

补算**确认而非改变** v1 判读。理由：

1. **branch 3 条件仍成立且被 CI 强化为"方向依赖 seed 与验证集"**：点估计上两种换法全部 12 项为正（"两种换法都改变"成立）；CI 层面方向稳健性依所固定 val / 校准版本而变——legacy val 的校准对比下界全 ≥0，而 fixed val 校准对比与两项 eval 对比多数跨 0。这正是 v2.7 branch 3 的"方向依赖 seed 和验证集"。
2. **不满足升级 branch 1（calibration_version_effect）的条件**：v2.7 branch 1 要求"固定 val 换校准后 L 差异持续且**方向稳健**"。补算显示该稳健性只在 legacy val 成立，fixed val 上 A11−A01 在 s0/s2 跨 0（2/3 跨 0）——**"方向稳健"未在两套 val 上一致成立**，故不符合升级条件。
3. **不满足 branch 2（eval_set_sensitivity）的"变化更大"**：② 的 CI 多数跨 0，且 fixed cal A11−A10 点估计 s0 仅 +1.7、s1 +38.3、s2 +15.0，幅度依 seed 剧烈波动，不能称"更大/更稳健"。
4. **不调整归类本身即合规**：v2.7 §3 禁止事后择支。补算只是补齐 v1 已指出缺失的区间，并未产生新的方向反转；此时把 mixed_interaction 改判为 calibration_version_effect 属"看到结果后择支"，须避免。
5. **branch 4（whole_version_only）**：2×2 设计仍能分离两因素的点估计贡献（虽交互纠缠），不宜降为"仅识别整体切换"的主判读；但其 `causality_boundary` 作为叠加边界**支配所有归因措辞**（见 §4.3）。

（记录：修复报告 §4 自述与科学家 mixed_interaction 判读一致；本修订独立复核后确认维持。）

### 2.2 对「数据缺陷制造假发现」叙事的支持边界（不变）

- 可支持："受控 2×2 显示数据版本切换系统改变 L（修复相关格 L 主 CI 下界>0，旧对角格 CI 围绕 0）"——**受控观察**。
- 不可支持："去重 / 退化对 / 模板重叠 / 新增未见模板中某一项**制造**了原发现"。v2.7 `causality_boundary`：归因单项须单独干预（本轮不做）；新增未见模板主要在 probe/test，当前 val 无法推断其效果。`main.tex` 的 "data defects manufactured / directly produced" 强因果措辞**必须撤除**。

---

## 3. 对角格一致性与归因边界（不变）

- A00≡repro、A11≡p1_clean 各 60/60 joint E_CF 逐对一致（sample_hash==cache_hash），identity/zero_re_prefill 全通过 → 统一环境复验成功、历史结果可追溯；版本间差异更可信来自数据版本本身。
- 边界不变：对角一致只证明复现与可追溯，**不证明单项因果、不涉封存 test / 主终点**。`whole_version_only` 归因边界、贡献(1)(2) 撤回、(3) withheld、主终点未评估——**全部不变**（`formal_summary §contribution_status_unchanged`、v2.7 invariants）。

---

## 4. 给写作者的措辞边界（更新）

### 4.1 CI 支持、可写（须带 exploratory 限定）
- "在受控 2×2 中，含修复数据的三格（A11/A01/A10）Self−Joint 双侧正确率差 L 的主区间（template_family 8 簇 bootstrap）在全部 3 seed 上点估计为正且下界 >0（L 点估计 23.3–61.7 pp；**均 exploratory，簇数 8<24**）。"
- ① legacy val 换校准 A10−A00："三 seed 点估计 +21.7~+36.7 pp，CI 下界均 ≥0（s2 下界=0.0 压线）"——可写"方向一致"，须标探索性。
- "点估计跨 seed 同号"（12 项对比全正）——**只能这样表述**，不可写"CI 确认"。

### 4.2 必须标注"CI 跨 0 / 探索性"
- A00 对角格三格 L 主 CI 围绕 0（s0/s1 跨 0，s2 下界=0）→ 写"旧对角格差异围绕 0、区间跨 0"。
- ① fixed val A11−A01 的 s0/s2、② eval 两项对比的多数 seed CI 跨 0 → 逐项标"区间跨 0，方向仅为点估计观察"。
- **全部 12 格、全部对比**统一标 `exploratory=true`（8 模板族 < 24）；不作强显著性、不报"显著为正"。

### 4.3 仍然禁止
- 写"CI 层面确认方向稳健 / 全部显著 / 稳健为正"；只报 pair-level 窄 CI 或用旧 `delta_lock` 的 8 簇区间冒充本次产物。
- 单项因果措辞（去重 / 退化对 / 模板重叠 / 未见模板任一"制造"翻转）；把整体版本切换说成单项缺陷因果。
- 恢复贡献(1)(2)、声称贡献(3)、声称主终点已评估或触碰封存 test；把 AI 生成集或 ARC/HellaSwag 混算进本实验。

---

## 5. 给写作者的一句话结论

**2×2 结果段应定性为"探索性的受控版本敏感性观察（mixed_interaction）"**：可报 A11/A01/A10 三格 L 主 CI 下界>0（23.3–61.7 pp）与 ① legacy-val 校准对比三 seed CI 下界≥0，但必须逐项注明全部 exploratory（8 簇<24）、A00 对角格与 ① fixed-val、② 两项 eval 对比的 CI 跨 0、"方向稳健"仅限点估计跨 seed 同号；不得写 CI 确认显著、不得作单项缺陷因果、贡献与主终点状态不变。

---

## 6. 统计风险与披露项（更新）

1. **全部探索性**：12 格 8 簇 < 24，`exploratory=true`；即使 9 格 CI 下界>0 也不作强推断。
2. "方向稳健"仅点估计层面全成立；CI 层面仅① legacy val 成立（s2 下界恰 0.0 压线）——须如实写为部分成立。
3. 对比②为非配对独立簇重采样（跨版本 val 是不同样本集），与① 的配对口径不同，不可直接比较区间宽度。
4. 多重比较：4 格×3 seed + 4 对比×3 seed，未见 Holm 校正；跨 seed 同号是一致性检查非显著性证据。
5. L 尺度颗粒度：60 对，最小分辨率 1/60≈1.67 pp；20 pp 历史阈值仅作图表参考。
6. 补算性质：`audit_2x2_l_ci.json` 为 CPU 从冻结 scores 重算的补充层，原 `bootstrap.json` 与 12 格 run 产物未改动；commit 链可追溯（修复报告 §5）。

**签署：科学家（2×2 结果统计解读 · 修订版 v2 · 2026-11-23）。未改数据/代码/prereg/论文，未跑实验，未重算 CI（直接引用补算产物），未编造数字。判读维持 mixed_interaction；whole_version_only 归因边界与贡献状态不变。**
