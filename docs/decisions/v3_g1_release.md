# v3.0 G1 放行文件（新研究 · 2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行 G1 收口）。
> 依据：`docs/audit/GPU_experiment_plan_2026-11-25.md`、`docs/decisions/gpu_v3_scope_ruling.md`（G0）、
> `configs/prereg/gpu_followup_v3.0.yaml`（已冻结）、`docs/decisions/v3_baseline_spec.md`、
> `reports/review/v3_g1_feasibility_audit.md`、`reports/data/v3_e1_variant_audit.md`、
> `reports/data/v3_e2_test_lock.md`、`reports/review/v3_g1_engineer_implementation.md`、
> `reports/review/v3_g1_e2_entry_report.md`。
> 性质：**G1 放行裁决**。只放行 G2 技术 pilot；不放行 G3 正式格，不授权投稿，不改任何冻结判据或当前稿件。

---

## 1. G1 放行结论

> **G1 = PASS。** 四项阻塞全部关闭，环境/模型/数据/入口/测试均落盘；**放行 G2 技术 pilot**（单 seed/小样本），G3 正式格仍需 G2 逐包 PASS 后另行放行。

## 2. 冻结环境（本次新研究专用，不覆盖归档环境）

| 项 | 冻结值 |
|---|---|
| Python | 3.12.3（`/root/readkv/.venv`） |
| torch | 2.11.0+cu130（CUDA 13.0，wheel 来源 `pypi.tuna.tsinghua.edu.cn/simple`） |
| transformers | 5.24.0（与归档 API 一致，使用 `cache=`；4.57.6 因 `past_key_values=` API 不兼容已弃用） |
| numpy / scipy / pytest | 2.5.5 / 1.18.1 / 9.2.0 |
| pyyaml / tqdm / safetensors | 6.0.4 / 4.70.1 / 0.8.0 |
| modelscope / modelscope-hub | 1.40.3 / 0.7.2 |
| uv | 0.9.17 |
| GPU / 驱动 | NVIDIA GeForce RTX 5090，32607 MiB，driver 580.82.07（CUDA 13.0） |
| 安装方式 | `uv pip install`（隔离 venv）；项目以 `-e . --no-deps` 安装 |
| 说明 | 与归档环境（Python 3.13.11 / torch 2.15.0+cu132 / RTX 4090 24GB）不同；本文件为新研究的**显式版本取舍**，归档数字不被改写、不与本环境直接合并。 |

## 3. 模型来源与钉扎（modelscope.cn，PI 授权）

下载时间（UTC）：`2026-11-25T14:45:06Z`。证据：`reports/_non_authoritative/v3_env/model_manifest.json`（逐文件 SHA-256 与字节数）。

| 模型 | revision 字段 | 本地快照目录 | 文件数 / 总字节 |
|---|---|---|---:|
| `Qwen/Qwen3-0.6B` | `master`（API 无 commit 可钉） | `/root/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master` | 8 / 1,519,182,438 |
| `Qwen/Qwen3-1.7B` | `master`（API 无 commit 可钉） | `/root/.cache/modelscope/models/Qwen--Qwen3-1.7B/snapshots/master` | 10 / 4,079,423,307 |
| `Qwen/Qwen3-4B` | `master`（API 无 commit 可钉） | `/root/.cache/modelscope/models/Qwen--Qwen3-4B/snapshots/master` | 11 / 8,060,896,929 |

**钉扎方式声明**：ModelScope 公开 API 对三者均返回 `ModelRevisions: null` / `get_valid_revision() == "master"`，不提供可钉 commit。按 prereg §2「不得用漂移的 master 别名而不记实际文件 hash」，本次以**逐文件 SHA-256 + 下载日期 + 固定本地快照目录**作为不可变身份；所有 run 必须指向上述绝对路径，**禁止**重新解析 `master` 或触发再次下载。G2/G3 的 `config.json` 必须记录所用快照目录与对应文件哈希。

## 4. 数据指纹

- E1 六变体 × 3 seed × 2 split = 36 JSONL；逐文件 SHA-256 / 行数 / 族数 / 变更规则见 `data/variants_v3/manifest.json`，CPU 复核脚本 `data/variants_v3/verify_variants_v3.py` PASS。
- `dedup_only` = **训练集内去重**（s1 仅移除 1 行，119/120），未做 train–val overlap 清理，不混称；构成变化标记版本差异。
- `degenerate_only` 训练/验证行数变化（115/117/116；56/56/55），属标签/任务有效性缺陷：不进入 ridge 监督拟合，不声称对 mapper 拟合有因果效应，指标变化优先 CPU replay。
- `entity/template_disjoint_only` 行数/族数不变但 val 文本改变，属数据任务改变，Panel B 需 GPU 前向。
- `fully_repaired` 与 legacy 由不同生成器 commit / RNG 全量重生成，标记版本差异，非纯单缺陷 A/B。
- E2 test：整文件 SHA-256 `f910f1f1…a894a`，test split SHA-256 `c5450013…769a7a2`，300 对 / 16 family；锁文件 `reports/data/v3_e2_test_lock.md`。称「previously unevaluated held-out split」，不称 sealed。本轮未读取 test 内容、未评分。

## 5. 实现与自检

| 项 | 证据 | 结果 |
|---|---|---|
| 非等深注入错层修复 | `src/readkv/models/hooks.py` + `gpu_backend.py`，`source_layer_map` 溯源、学生空间恒等注入、`_layer_map_entry` 越界报错不取模 | 3 项相关回归测试 PASS |
| 非等深注入回归测试 | `tests/test_layer_map_injection.py`（5 项，含 V-stamp 仪器修正） | 5/5 PASS |
| E1 独立入口 | `experiments/e1_variant_gpu.py`：哈希不符 abort、test 路径拒绝、裸 master 拒绝、无自动重建、CPU-replay 模式、`--cpu-selfcheck` | 13 项全 true |
| E2 one-shot evaluator | `experiments/e2_test_evaluator.py`：锁文件 + 三重哈希、val 路径/调参 flag 拒绝、6 格固定、`--cpu-selfcheck` | 10/10 PASS |
| E2 入口 CPU 测试 | `tests/test_v3_entries.py` | 7/7 PASS |
| 全量单测 | `.venv/bin/python -m pytest -q` | **91 passed**（两次复跑一致） |

## 6. 科学决策落盘

- **E6 复现门 NOT PASSED** → 采用冻结内部对照 `v3-BM-MLP-KD`（7,340,032 参数、KL 目标），规格见 `docs/decisions/v3_baseline_spec.md`；不称已发表方法 faithful baseline。
- **E5 = affine only**，3 seed → 3 正式格；不追加 kd_only；P4 仍 NO-GO，仅一个额外模型对，不称跨模型泛化。
- 两个历史敞开项（`postprocess` Self E_CF 双写；layer-0 K/V 捕获失败测试）与 v3 **分离**：前者与本 GPU 链路无关；后者在对齐 transformers 5.24.0 后全量单测已通过（91 passed），不再阻塞 G2，但不得把该修复计入 v3 科学结果。

## 7. 门控状态

| 门 | 状态 |
|---|---|
| G0 范围裁决 | ✅（gpu_v3_scope_ruling.md） |
| G1 prereg + CPU 数据/基线审计 | ✅ **本文件放行** |
| G2 技术 pilot | ⏳ **现已授权**：逐包单 seed/小样本；逐包 PASS 才进入该包正式格 |
| G3 正式格 | ⛔ 未放行（需 G2 逐包 PASS 后另行裁决） |
| G4 统计与独立审阅 | ⛔ 未放行 |

## 8. 不可变边界重申

当前 TMLR 稿件只读；v2.1–v2.9 一字不回写；贡献(1)(2) 撤回、(3) withheld；P2/P3/P4 永久放弃；不重跑 v2.7 2×2 / 序列评分；不混入 SQuAD/ARC/HellaSwag/真实文档/AI 生成数据；E1 不称因果分解、E2 不称 sealed/不合并 replicate、E5 不称跨模型泛化、E6 不称 faithful baseline；agent 不代为投稿。

---

**签署：PI / 课题组长（G1 放行 · 2026-11-25）**
