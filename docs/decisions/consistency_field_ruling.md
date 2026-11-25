# C3 字段假阳性裁决：修审计脚本（选项 B）（V2.0 · 2×2）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：审稿 `reports/review/audit_2x2_formal_review.md` §3 C3——12 格因审计入口用 `calibration_version/validation_version` + teacher/student 路径替代 `model_pair` 字段，在 consistency_check 中 ok=false（字段对接假阳性，数据/指标无误）；审稿给 A（报告标注，零改动）/ B（修脚本识别新字段，+commit+回归）二选一，倾向 B 但不代决。
> 依据：`reports/review/audit_2x2_formal_review.md` §3、`scripts/consistency_check.py`（`_check_model_pair` line 124，已有锚点路径推断先例 line 133–150）、`configs/prereg/gpu_followup_v2.7.yaml` §1（替代字段合规）。
> 本裁决只写决策文档；本轮不改 `src/**`（含 scripts）、`reports/runs/**`、冻结判据、数据或论文；不写代码、不跑实验（实现由工程师据此执行）。

---

## 1. 裁定：选项 B（修审计脚本识别新字段）

> **裁定：采用选项 B——工程师修改 `scripts/consistency_check.py`，使其识别 `calibration_version`/`validation_version` + `input_sha256` 作为 `model_pair` 的等价字段（按审计入口硬编码默认推断 MVP 等深对），使 12 格 ok=true；不改其他 run 的判定逻辑；新 commit + 回归测试。**

理由（四维度）：
1. **工具契约 bug 应修根因**：v2.7 §1 明确允许用 `calibration_version/validation_version` + 硬编码 teacher/student 表达模型口径（"未规定必须以 model_pair 字面呈现"）；脚本 `_check_model_pair` 不识别该合法字段，是**审计工具的契约缺口**，不是研究设计问题。修根因优于每次人工解释。
2. **未来审计可靠性**：选项 A 会让每次审计都显示 12 条假阳性，下游自动汇总可能把 ok=false 误当作真问题；选项 B 使机器可读结论干净，对后续 2×2 相关 run 与最终交付更稳。
3. **不触及红线**：修改限于 `scripts/consistency_check.py` 的字段识别，**不改任何冻结判据、不改任何 run 产物（scores/config/metrics）**——符合"审计脚本可改、产物不可改"的既有纪律；且脚本中已有"锚点 run 按 teacher/student 路径推断"的同类先例（line 133–150），本修改是同一模式的自然扩展，回归风险可控。
4. **成本小**：局部函数扩展 + 回归测试 + 新 commit，远低于选项 A 累积的人工解释成本与误判风险。

**为何不选 A**：选项 A 虽"零改动、零回归风险"，但把工具 bug 永久留给下游人工解释，与"可复现/机器可读审计"的项目目标相悖；在修复成本可控且有先例的情况下，B 更优。

---

## 2. 修改范围（严格限定）

**允许修改**：仅 `scripts/consistency_check.py` 的 `_check_model_pair`（及必要的常量/辅助函数）：
1. 在 `PAIR_EXPECT` 查找失败、且 config 含 `calibration_version` 与 `validation_version` 时，按审计入口硬编码默认（Qwen3-1.7B→0.6B、identity 28→28 等深断言）推断为 MVP 等深对，返回 `ok=True`，附 `inferred_model_pair` 与 `inference_note`（如"2×2 audit run: model determined by hardcoded 1.7B→0.6B entrypoint + equal-depth assertion (v2.7 §1)"）。
2. 可选用 `input_sha256` 四份数据路径辅助确认数据版本身份（非必须，若有助于溯源）。
3. 修改须**泛化到任何带 `calibration_version`/`validation_version` 的 2×2 类 run**，不硬编码 12 个 run_id。

**禁止修改**：
- 不得改变任何既有 `model_pair`/teacher/student 路径 run 的判定逻辑（锚点 run、clean run、历史 run 的 ok/superseded 判定必须逐项不变）；
- 不得改 `PAIR_EXPECT` 中既有条目或任何冻结判据、阈值；
- 不得改 `reports/runs/**`、`configs/prereg/**`、数据或论文。

---

## 3. 验收标准（工程师执行后）

1. **12 格 ok=true**：重跑 `consistency_check`，12 个 `audit_2x2_*` 格全部 `ok=true`、`traceable=true`、`run_code_unchanged_vs_head=true`，无 `unknown model_pair` 假阳性。
2. **旧 run 判定不变**：对当前全部 31+ 历史 run 重跑，24 个既有判定（22 superseded + 各权威 ok）**逐项与修改前一致**——尤其锚点 run 的 teacher/student 推断路径不受影响，clean run 的 ok=true 不变。
3. **新 commit + 回归测试**：修改纳入新 commit；增加单元测试覆盖"(a) 带 calibration_version/validation_version 的 2×2 config → ok=true；(b) 既有 model_pair config 判定不变；(c) 锚点 config 判定不变"三种情形；`pytest` 全通过。
4. **不污染产物**：重跑审计输出定向 `/tmp` 或经确认的路径，不改仓库 `reports/consistency_report.json` 等既有产物（除非 PI/审稿人明确要求更新权威审计产物）。

---

## 4. 12 格科学证据不受影响（明确）

- **C3 是字段对接假阳性，不影响 12 格数据/指标**：审稿已独立核实 12 格 provenance（12/12）、数据哈希（48/48）、L 值复算（12/12）、对角核对（6/6，60/60 逐对一致）全部通过；`traceable` 与 `run_code_unchanged_vs_head` 全 true。改脚本只为消除告警，**不改变任何实验结论**。
- **C3 与 C1/C2 独立**：C3 处置（本裁决）不构成 P5 重新签off的实质障碍；C1（bootstrap 统计口径：template_family 主 CI + exploratory + L 对比 CI + 敏感性）与 C2（因果措辞降级）才是 2×2 的主要合规前置，须另行闭环（见 audit §6）。
- **P5 前置条件中 C3 的闭环标记**：当且仅当 §3 四条验收全部满足（12 格 ok=true + 旧判定不变 + 新 commit/回归 + 不污染产物），审稿人在 P5 重新签off前置清单中把 **C3 标记为"已闭环（选项 B，脚本修复 + 回归通过）"**；在此之前标"待落实"。

---

## 5. 执行分工与顺序

- **工程师**：实现 `_check_model_pair` 局部扩展（§2）→ 加回归测试 → 新 commit → 重跑 consistency 并按 §3 自验 → 报告结果。
- **审稿人**：复核 §3 四条验收（尤其旧 run 判定不变、12 格 ok=true），在 P5 前置清单标记 C3 闭环；与 C1/C2 一并纳入最终 compliance note。
- **顺序依赖**：C3（本裁决）可与 C1（统计口径补齐）、C2（因果措辞降级）**并行**推进；三者全部闭环 + C4（论文补 2×2 段）后，方可 P5 重新签off。**本裁决本身不触发 P5 签off。**

---

## 6. 结论

- **选项 B 获批**：修 `scripts/consistency_check.py` 识别 `calibration_version/validation_version` 等价字段，严格限定修改范围（§2），新 commit + 回归，12 格 ok=true 且旧 run 判定不变（§3）。
- **12 格科学证据不受假阳性影响**；C3 闭环仅在 §3 验收全过后标记。
- 不变项：主终点、贡献(1)(2) 撤回/(3) withheld、P2/P3/P4 永久放弃、v2.7 口径、2×2 数据与结论——全部维持；C1/C2/C4 仍须独立闭环后方可 P5 重新签off。

**签署：PI / 课题组长（C3 字段假阳性裁决 · 2026-11-23）**
