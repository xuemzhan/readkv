# C3 字段假阳性修复报告（选项 B · 审计脚本局部扩展）

> 日期：2026-11-23。依据：`docs/decisions/consistency_field_ruling.md`（C3 选 B）、`configs/prereg/gpu_followup_v2.7.yaml` §1。
> 边界：仅改 `scripts/consistency_check.py` 的 `_check_model_pair` + 新增回归测试；不改任何 run 产物 / prereg / 数据 / 论文；不跑 GPU。

## 1. 修改点

- 在 `_check_model_pair` 的 `exp is None`（PAIR_EXPECT 查找失败）分支内、锚点路径推断之后，新增：当 config 含 `calibration_version` 与 `validation_version` 时，按审计入口硬编码默认推断 MVP 等深对 `qwen3-1.7b-to-0.6b`（teacher/student 标记 1.7B→0.6B、28→28 等深断言由 `layer_map` 确认），返回 `ok=true`、`inferred_model_pair`、`exempt=true`、`infer_2x2=true`、`equal_depth_asserted`、`inference_note`。
- **泛化**：按字段判定，不硬编码任何 run_id；适用任何带 cal/val version 的 2×2 类 run。
- **不触碰既有判定**：修改仅在 `exp is None` 分支内、且锚点推断之后；所有带 `model_pair` 的既有 run、锚点 run、历史 run 走原路径不变；未改 `PAIR_EXPECT` 条目或任何阈值。

## 2. 回归测试（`tests/test_consistency_model_pair.py`，5 项全通过）

- (a) 2×2 config（cal/val version + 28→28 layer_map）→ ok=true、推断 MVP、等深断言 true —— PASS。
- (a') 2×2 config 但 layer_map 28→36（等深断言失败）→ ok=false —— PASS。
- (b) 既有 model_pair config 正常（1.7B→0.6b + 路径匹配）→ ok=true、exempt=false —— PASS。
- (b') 既有 model_pair config 误配（4b→1.7b 但路径 1.7B/0.6B）→ ok=false —— PASS。
- (c) 锚点 config（stage=external_anchor + teacher/student 路径）→ ok=true、exempt=true、推断 MVP —— PASS。

`pytest`：**58 passed**（原 53 + 新 5）。

## 3. 修复前后判定对比（重跑输出到 /tmp，未改仓库 reports/consistency_report.json 等既有产物）

| 项 | 修复前 | 修复后 |
|---|---|---|
| 12 格 `audit_2x2_*` | ok=false（`unknown model_pair` 假阳性）、traceable=true | **全部 ok=true、traceable=true、infer_2x2=true**，无假阳性 |
| 其余 31 run（22 superseded + 9 权威/锚点/历史） | ok/superseded/exempt/protocol 判定 | **逐项完全一致，changed=仅 12 格**（预期修复，无副作用） |

修改前基线存 `/tmp/opencode/consistency_BEFORE.json`，修改后 `/tmp/opencode/consistency_AFTER.json`；逐项对比脚本确认除 12 格外零变化。

## 4. commit+push 链

`bfd5793`（脚本局部修复 + 5 回归测试，本地=远程=`bfd5793`）；push 期间远程曾前进到 `b267efa`（并行实例），已基于最新远程提交，push 成功。

## 5. 给审稿人复核路径

- 修改：`scripts/consistency_check.py::_check_model_pair`（2×2 推断分支）；测试：`tests/test_consistency_model_pair.py`。
- 复现：` .venv/bin/python -m pytest tests/test_consistency_model_pair.py -q`；` .venv/bin/python -m scripts.consistency_check --reports-root reports --output /tmp/<out>.json`。
- 验收：12 格 ok=true/traceable；旧 run 判定不变；58 测试通过；无 run 产物被改（git status 对 reports/runs/ 为空）。
- C3 闭环标记请在 P5 前置清单中据本报告 + 审稿复核填写；C1（统计口径）/C2（因果措辞）/C4（论文补稿）仍须独立闭环。
