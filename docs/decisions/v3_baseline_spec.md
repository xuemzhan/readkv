# v3.0 E6 预算匹配内部对照规格（新文件 · 不回写 v3.0）

> 裁决人：**真实 PI（用户）**。日期：2026-11-25。
> 来源：真实 PI 对 G1 审计（`reports/review/v3_g1_feasibility_audit.md` §2）的答复：E6 复现门未通过 → 冻结新内部对照 `v3-BM-MLP-KD`；E5 仅 affine（3 格）。
> 性质：**新增规格文件**，冻结 `configs/prereg/gpu_followup_v3.0.yaml` 一字不改；本文件是 v3.0 §6 `fallback` 的具体实现规格，在看到任何结果前冻结。

---

## 1. E6 复现门结论（落盘）

- KV-Lingo（arXiv:2609.32610）与 CacheLink（arXiv:2610.15509）目前只核验到**摘要级**；代码仓库、权重、许可、完整训练目标、训练语料、逐层映射细节均**未核验**。
- 判定：**复现门 NOT PASSED**。不得称任一外部方法为 faithful baseline（v3.0 §6 `if_fail`、G0 ruling §1 E6、plan §6.1）。
- 若后续取得代码/权重，须在结果揭盲前逐项核验：全文方法、代码/权重可用性与许可、mapper 结构、训练数据、训练目标、输入信息、推理严格 zero-re-prefill（`verify_zero_re_prefill`），并单独冻结判定。

## 2. `v3-BM-MLP-KD` 规格（冻结）

| 项 | 冻结值 |
|---|---|
| 名称 | `v3-BM-MLP-KD`（budget-matched per-layer K/V linear mapper, KD objective）——**不称已发表方法基线** |
| 架构 | 逐学生层、逐 KV head 的线性映射 `W ∈ R^{128×128}`（**无 bias**，与现有闭式 ridge affine 区分）；K 与 V 各一套；覆盖 28 层 × 8 KV heads × head_dim 128 |
| 参数量 | `128×128 × 2(K,V) × 8 heads × 28 layers = 7,340,032`，与现有 kd_only 的 `trainable_params=7,340,032` 刻意相等 |
| 参数匹配容差 | 事先定义：参数量**精确相等**；若实现差异导致不等，须在 G1 放行文件说明并不得称预算匹配 |
| 训练数据 | 与 kd_only 相同的 120 训练对，同一 clean train split |
| 训练设置 | 8 epochs、lr=1e-3、Adam、seed 0/1/2 |
| 训练目标 | `KL(native Self logits ‖ mapped logits)`，即 `src/readkv/train/kd_gpu.py:140-147` 的 `L_KD`（`lam_kd=1.0, lam_reg=1e-4, lam_cf=0`） |
| 梯度 | 只回传映射缓存，学生权重冻结（`:93-96`） |
| 同条件 | 同模型对（Qwen3-1.7B→0.6B）、同 train/val、同 3 seed、同 `zero_re_prefill=true` |
| 评测 | 与 affine/kd_only 在同一 clean val 上逐对评测；分开报告，不 pooled |

## 3. E5 mapper 集合（冻结）

- E5 第二模型对（Qwen3-4B→1.7B）**仅 affine**，3 seed = **3 个正式格**；不追加 kd_only。
- 因此 E5 不受 E6 内部对照规格耦合；P4 仍 NO-GO，仅一个额外模型对，不称跨模型泛化。

## 4. 分项披露清单（每个 baseline 必报）

1. 参数量（trainable params，按层/通道分解）+ 参数匹配容差定义；
2. GPU 时间（训练秒数 + 总墙钟，逐格落盘）；
3. 前向/反向次数（每 epoch、每 seed 的 student forward 与 backward 数）；
4. 显存（峰值 `torch.cuda.max_memory_allocated()`，区分已分配/保留）；
5. 训练目标明文（ridge λ=1e-3 / `L_KD` 的 lam 组合 / `v3-BM-MLP-KD` 的 KL 公式）；
6. 事前定义的模型质量、训练预算、主指标、失败/中断处理、比较族；即使排名不变也完整报告训练成本差异；
7. 复用 affine/kd_only 权威结果须核验 data hash / checkpoint / code 绑定，否则三 seed 新跑；
8. 若纳入 E5 的 4B→1.7B，分开报告，不与 MVP affine 直接比较。

---

**签署**：真实 PI（用户）答复，由 main agent 原样记录（v3.0 E6/E5 冻结规格 · 2026-11-25）。
