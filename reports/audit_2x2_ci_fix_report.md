# 2×2 统计口径补算修复报告（v2.7 合规缺口 S：L/对比 CI 缺失）

> 日期：2026-11-23。依据：`docs/audit_2x2_statistical_interpretation.md`（科学家，§1.1/§5.1 合规缺口）、`configs/prereg/gpu_followup_v2.7.yaml` §2（主口径 template_family + pair 敏感性 + <24 exploratory）。
> 边界：纯 CPU 从冻结 scores + val JSONL 重算；**不改任何 run 产物 / bootstrap.json 原文件 / prereg / 数据 / 论文**；不重跑 GPU。

## 1. 修复前口径（缺口）

`reports/audit_2x2_bootstrap.json` 对 12 格只给各臂 **E_CF** 区间，且 `cluster_unit=cluster-fallback`、`n_clusters=60`、`exploratory=false`（逐对唯一簇重采样，违反 v2.7）；**无 L 的 CI、无两项预固定对比的 CI**。带 `template_family/8 族/exploratory=true` 的区间属旧 `delta_lock` run，非本次 12 格。

## 2. 修复后（补算产物 `reports/audit_2x2_l_ci.json`）

- **关联键**：`version_tag + sample_hash`（scores 的 `sample_id` = val JSONL 的 `sample_id`），规避跨版本 `pair_id` 碰撞；12 格 × 60 对全部匹配，`unknown_family_pairs=0`。
- **L 主口径**：`L = (Self_dual − Joint_dual)×100`（逐对配对），主 CI = **template_family 簇级 bootstrap 10000**（seed=各格 seed），pair-level 逐对敏感性 CI 并列；每格 `n_clusters=8 < 24` → **`exploratory=true`（12/12）**。
- **E_CF 主口径补正**：每格 `joint_E_CF_template_family_ci` 给出 template_family 主区间（如 A11_s0 = 6.900 [3.564, 10.100]，与原 delta_lock template_family 口径一致），不再沿用逐对簇冒充独立样本。
- **两项预固定对比 CI**：
  - ①固定 val 换校准（同 val 按 sample_id 配对，按模板族重采样）：legacy val A10−A00 三点点估计 +36.7/+28.3/+21.7 pp，CI 分别 [15.5,54.8]/[13.8,42.4]/[0.0,41.3]；fixed val A11−A01 点估计 +13.3/+33.3/+6.7，CI [-1.6,30.0]/[10.0,55.2]/[-14.5,28.8]。
  - ②固定 mapper 换 val（**跨版本 val 是不同样本集**，按 v2.7 cross_version_note 用两个独立 val 各自 template_family 簇重采样的均值差 CI）：legacy cal A01−A00 点估计 +25.0/+33.3/+30.0，CI [-2.5,46.2]/[10.5,54.7]/[6.7,51.6]；fixed cal A11−A10 点估计 +1.7/+38.3/+15.0，CI [-29.2,31.7]/[10.3,64.7]/[-12.7,43.8]。
  - 注：对比① fixed val 的 s0/s2、对比② 多数 seed 的 CI 跨 0 → **按 v2.7 exploratory 口径，不得声称 CI 层面确认方向稳健/显著**；点估计跨 seed 同号仍成立。

## 3. 失败/重试记录（≤3 次，日志留痕）

| 尝试 | 日志 | 根因分类 | 根因 | 可识别修复（新 commit） | 结果 |
|---|---|---|---|---|---|
| 1 | `/tmp/opencode/audit_ci_attempt1.log` | 统计 | 对比②换 val 按 sample_id 配对，但跨版本 val 的 sample_id 不同（legacy/fixed 实体与文本隔离）→ 交集 n=0，对比② CI 缺失 | 对比②改非配对：两独立 val 各自按 template_family 簇重采样均值差（commit `6c6b7d3`） | 部分成功（L 主 CI 已出，对比②缺失） |
| 2 | `/tmp/opencode/audit_ci_attempt2.log` | — | — | — | **成功**（12 格 L 主/敏感性 CI + 四项对比 CI 全产出） |

- 脚本首版 commit `e9f5773`；修复 commit `6c6b7d3`；均 commit+push、远程同步确认。

## 4. 关键数值（L 主 CI，pp，template_family 簇级）

| 格 | s0 | s1 | s2 |
|---|---|---|---|
| A00 | +1.67 [-3.33, 7.02] | −5.00 [-15.25, 6.67] | +3.33 [0.00, 10.34] |
| A11 | +40.0 [16.67, 62.71] | +61.67 [38.33, 83.05] | +40.0 [20.34, 58.73] |
| A01 | +26.67 [1.69, 48.39] | +28.33 [9.84, 48.28] | +33.33 [11.67, 54.84] |
| A10 | +38.33 [15.79, 57.38] | +23.33 [6.90, 38.33] | +25.0 [3.39, 43.55] |

A11/A01/A10 十格 L 主 CI 下界 >0（修复数据相关格），A00 三格围绕 0（旧对角格，多数 CI 跨 0）；与科学家 mixed_interaction 判读一致。

## 5. commit+push 链

`e9f5773`（补算脚本）→ `6c6b7d3`（对比②非配对修复）→ `见本次 commit`（补算产物 + 本报告）。每次 push 后 `git ls-remote` 与本地 HEAD 一致。

## 6. 给科学家/审稿人复核路径

- 补算产物：`reports/audit_2x2_l_ci.json`（cells: L 主 CI/pair 敏感性/E_CF 主口径/n_clusters/exploratory；predeclared_contrasts: 四项 ×3 seed 配对 CI + method 字段）。
- 脚本：`scripts/audit_2x2_ci.py`（可重跑复现；种子=各格 seed，n_resamples=10000）。
- 原产物 `reports/audit_2x2_bootstrap.json` 与 12 格 `reports/runs/audit_2x2_*/` **未改动**；本文件是新增补充层。
- 判读纪律：全部 exploratory（8 族<24），不得作强显著性主张；whole_version_only 归因边界与贡献状态不变。
