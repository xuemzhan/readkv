# audit_seq_summary_b0 — CPU 汇总（protocol-v2.8 干净基线）

> 仅从六个 `_b0` 正式格的 scores.jsonl / metrics.json 复算；不新增 GPU run，不重判结果。
> 权威集 = `_b0` 八格；旧 id 为非权威历史。首/整串/归一并列，E_CF 不跨口径比大小。

## 1. 逐 seed 主表（L = Self−Joint 双侧正确率，百分点）

| cell | seed | L(first) | L(full) | L(len-norm) | Self双语(first) | Joint双语(first) |
| --- | --- | --- | --- | --- | --- | --- |
| A11 | 0 | 0.383 | 0.433 | 0.450 | 0.700 | 0.317 |
| A11 | 1 | 0.617 | 0.400 | 0.450 | 0.783 | 0.167 |
| A11 | 2 | 0.400 | 0.467 | 0.550 | 0.667 | 0.267 |
| A00 | 0 | 0.017 | 0.000 | 0.000 | 0.567 | 0.550 |
| A00 | 1 | -0.067 | -0.050 | -0.050 | 0.483 | 0.550 |
| A00 | 2 | 0.033 | 0.033 | 0.033 | 0.533 | 0.500 |

## 2. 配对读数差 L(full)−L(first)（template_family 主 CI，pair-level 敏感性见各格 metrics）

- A11 s0: point=0.0500, CI=[-0.1803, 0.2586], n=60, exploratory=True
- A11 s1: point=-0.2167, CI=[-0.3333, -0.1167], n=60, exploratory=True
- A11 s2: point=0.0667, CI=[-0.0820, 0.2333], n=60, exploratory=True
- A00 s0: point=-0.0167, CI=[-0.0690, 0.0339], n=60, exploratory=True
- A00 s1: point=0.0167, CI=[-0.0492, 0.0984], n=60, exploratory=True
- A00 s2: point=0.0000, CI=[0.0000, 0.0000], n=60, exploratory=True

## 3. cell_diff（每 seed A11−A00 的 L 差，描述性；判读由 scientist 按 v2.8 §7 完成）

- first: s0=+0.367, s1=+0.683, s2=+0.367
- full: s0=+0.433, s1=+0.450, s2=+0.433
- length_normalized: s0=+0.450, s1=+0.500, s2=+0.517

## 4. 三读数 / 审计完整性

| run | scores | 三读数齐全 | E_CF(joint,first) | E_CF(joint,full) | coverage(joint,first) | 审计 records |
| --- | --- | --- | --- | --- | --- | --- |
| audit_seq_A11_s0_b0 | 120 | True | 6.900 | 15.952 | 0.867 | 480 |
| audit_seq_A11_s1_b0 | 120 | True | 8.159 | 17.305 | 0.883 | 480 |
| audit_seq_A11_s2_b0 | 120 | True | 8.540 | 18.998 | 0.883 | 480 |
| audit_seq_A00_s0_b0 | 120 | True | 1.968 | 1.818 | 0.800 | 480 |
| audit_seq_A00_s1_b0 | 120 | True | 1.934 | 1.694 | 0.817 | 480 |
| audit_seq_A00_s2_b0 | 120 | True | 2.123 | 1.852 | 0.800 | 480 |
