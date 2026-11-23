# ReadKV GPU 补充实验运行表

**2026-11-23。** A00＝旧 train/旧 val，A01＝旧 train/修复版 val，A10＝修复版 train/旧 val，A11＝修复版 train/修复版 val。每个 GPU 评估格保存 Self、Identity、Joint、控制、逐对双侧正确率和 E_CF。以下是拟用运行编号。

| 顺序 | 运行编号 | 输入 / 用途 | 状态 |
| --- | --- | --- | --- |
| 0 | `audit-data-train-val` | CPU 验证 6 组 train 与 6 组 val 的生成身份 | 已核验逐组 120/120 train、60/60 val；待导出正式输入 |
| 1 | `audit-kv-identity-seed0` | GPU 环境和缓存恒等性 | 待运行 |
| 2 | `audit-affine-smoke-seed0` | 固定小子集走四格，核验输入与配对 | 待运行 |
| 3 | `audit-affine-a00-seed0` | 旧版历史对角格 | 待运行 |
| 4 | `audit-affine-a11-seed0` | 修复版对角格 | 待运行 |
| 5 | `audit-affine-a01-seed0` | 旧校准、修复版验证 | 待运行 |
| 6 | `audit-affine-a10-seed0` | 修复版校准、旧验证 | 待运行 |
| 7–10 | `audit-affine-a00-seed1`、`audit-affine-a11-seed1`、`audit-affine-a01-seed1`、`audit-affine-a10-seed1` | seed 1 四格 | 待运行 |
| 11–14 | `audit-affine-a00-seed2`、`audit-affine-a11-seed2`、`audit-affine-a01-seed2`、`audit-affine-a10-seed2` | seed 2 四格 | 待运行 |
| 15 | `audit-affine-factorial-summary` | CPU 汇总四格、配对区间、分切片及对角格复现 | 待运行 |

各 seed 复用同一个旧 mapper 与同一个修复版 mapper 评估对应两列。首轮后如需完整候选评分，可增加 `audit-affine-sequence-seed{0,1,2}`。详细准入和预算见 [实验方案](EXPERIMENT_PLAN.md)。
