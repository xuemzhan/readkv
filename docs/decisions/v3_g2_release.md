# v3.0 G2 放行文件（新研究 · 2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行 G2 收口）。
> 依据：`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN）、`docs/decisions/v3_g1_release.md`、
> `reports/review/v3_g2_pilot_report.md`、`data/variants_v3/manifest.json`、`docs/decisions/v3_baseline_spec.md`。
> 性质：**G2 放行裁决 + E1 规范冲突裁定**。放行 G3 正式格；不放行投稿；不改冻结判据或当前稿件。

---

## 1. E1 规范冲突裁定（G2 唯一阻塞项，现关闭）

- 事实：G2 E1 literal 命令把 `legacy_bundle/val_seed0.jsonl` 称作「clean v2.1 val」，被 G1 冻结入口的 `CLEAN_VARIANT = fully_repaired` 门控拒绝（未加载模型、未产出分数）。随后 bridge smoke 改用 `fully_repaired/val_seed0.jsonl` 并通过。
- **裁定：`fully_repaired/val_seed{k}.jsonl` 是 Panel A 的规范 clean v2.1 val。** 依据：v3.0 §3 `variants` 明确 `fully_repaired（当前 v2.1 全修复版本）`，Panel A 要求「所有 mapper 均在同一 v2.1 validation 上评分」；G1 数据 manifest 亦将 fully_repaired 登记为 v2.1 全修复版本。
- 前述 literal 命令是**本次会话中 main agent 的指令笔误**（把 legacy val 误标为 clean），不是冻结入口或数据的缺陷；该命令已被 bridge smoke 取代，不产生任何权威结果。
- 执行含义：E1 Panel A 固定使用 `data/variants_v3/fully_repaired/val_seed{k}.jsonl` 作为评测集；`legacy_bundle/val_seed{k}.jsonl` 仅作为 legacy 历史锚点，不称为 clean v2.1 val。不改 v3.0、不改数据、不改入口常量。

## 2. G2 结果总览

| 包 | pilot 结果 | 关键证据 |
|---|---|---|
| E1 | **PASS**（bridge smoke） | 120 train / 6 val，8 arms，88.3 s，peak 4450 MiB，inference forwards 7/7/7/7，strict zero-re-prefill True，Self/Identity g-diff 0.0 |
| E5 | **PASS** | 4B→1.7B 36→28 proportional；`resolve_injection_layer_map → None`，source-map 保留无取模，V-stamp 读取顺序 0..27；Self/Identity 0.0，strict zero-re-prefill True，peak 11039.5 MiB；run 标 NON-AUTHORITATIVE |
| E2 技术路径 | **PASS** | 固定 affine + kd_only 在 6 个**非 test** val 对上运行；pinned 1.7B/0.6B；显式 test 路径/行拒绝；zero-re-prefill True，peak 4483.3 MiB，151.4 s |
| E6 | **PASS（修复后）** | 首跑因 CUDA/CPU device bug ABORTED（保留、非权威）；`_r2` 参数 7,340,032、bias=0、shape (28,8,128,128)×2，loss 4.48→0.0065，48 steps/96 forwards+36 injections，peak 4597.7/4658.0 MiB，26.9 s，zero-re-prefill True |
| 全量单测 | **97 passed** | 91 原有 + 6 E6 新增 |

## 3. G2 门控结论

> **G2 = PASS（ CONDITIONAL 已关闭）。** 四条技术路径均通过，E1 规范冲突已按 §1 裁定关闭。所有 pilot 数字均为 **NON-AUTHORITATIVE**，不进入论文、不与归档结果合并。

## 4. G3 放行（正式格）

**授权范围**：仅 v3.0 §3–§6 定义的正式格，串行执行，不覆盖归档，所有 seed/对照/失败 run 入账。

| 顺序 | 包 | 正式格 | 约束 |
|---:|---|---|---|
| 1 | E5 | affine × seed 0/1/2 = **3 格** | 仅 affine；pinned 4B/1.7B；逐格零 re-prefill + cache 形状审计；不与 MVP 合并 seed/CI |
| 2 | E6 | `v3-BM-MLP-KD` × seed 0/1/2 = **3 格** | 仅用修复后代码；失败 run `v3_E6_BM-MLP-KD_s0_smoke` 不得复用；分项披露参数/时间/前向反向/显存/目标 |
| 3 | E2 | affine + kd_only × seed 0/1/2 = **6 格** | one-shot dedicated evaluator；同一固定 300 对；锁文件哈希全匹配；无调参/返修/多轮查看；16 family → exploratory |
| 4 | E1 | Panel A 15 格 + Panel B 15 格 = **最多 30 格** | Panel A val 按 §1 用 fully_repaired；Panel B 固定 clean mapper；degenerate 变体先 CPU replay，仅输入文本变化才 GPU 前向并单列 data_task_change；报告全部六种版本条件，不称因果分解 |

**停止规则**：任一格技术门失败 → 停该包并报告，不跨包掩盖；OOM 不通过改精度/kernel 后继续合并。

## 5. 仍未放行

- **G4 统计与独立审阅**：未放行；须在 G3 全部完成后由 scientist + reviewer 做 family bootstrap + pair 敏感性、预承诺分支对号入座、所有失败 run 入账。
- **投稿**：agent 不代为投稿；本裁决不涉及任何论文改动或投稿动作。
- 两个历史敞开项与 v3 分离；E6 首个失败 run 保留为非权威证据。

---

**签署：PI / 课题组长（G2 放行 · 2026-11-25）**
