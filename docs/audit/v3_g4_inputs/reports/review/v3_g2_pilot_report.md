# v3.0 G2 技术 pilot 报告（2026-11-25）

> 角色：工程师。依据：`docs/decisions/v3_g1_release.md`（G1 PASS，仅放行 G2 技术 pilot）、
> `configs/prereg/gpu_followup_v3.0.yaml`（FROZEN）、`docs/decisions/v3_baseline_spec.md`（FROZEN）、
> `reports/_non_authoritative/v3_env/model_manifest.json`。
> **性质：G2 技术 pilot，单 seed / 小样本。未运行任何正式格（G3 未放行）；未读取或评分任何 test 内容；
> 本文不含科学结论。所有数值只用于判断技术路径是否可用，不得当作证据或结果引用。**

---

## 0. 环境与钉扎（先于任何 GPU forward 核验）

| 项 | 值 |
|---|---|
| 环境 | Python 3.12.3 / `.venv`；torch 2.11.0+cu130；transformers 5.24.0（`cache=` API） |
| GPU | NVIDIA GeForce RTX 5090，32607 MiB，driver 580.82.07，CUDA 13.0；`torch.cuda.is_available()=True` |
| dtype / kernel | bfloat16 / sdpa（frozen，未临场改动） |
| 模型快照 | `/root/.cache/modelscope/models/Qwen--Qwen3-{4B,1.7B,0.6B}/snapshots/master`（绝对路径，固定本地目录） |
| 逐文件 SHA-256 | 对 `model_manifest.json` 列出的全部 8+10+11 个文件逐一重算：**全部 OK**（`ALL_MODEL_HASHES_OK=true`）；未触发再下载、未重新解析 `master` |
| 入口路径限制 | `e1_variant_gpu` / `v3_e6_control_gpu` 拒绝含 `master/main/latest` 的原始别名，故在 `reports/_non_authoritative/v3_g2_pilot/pinned/` 下建立 **SHA 命名符号链接**指向上述固定快照；链接名含 `config.json` SHA 前缀，实际文件仍逐 SHA 绑定 |
| 结构确认 | 4B=36 层 / 32 attn heads / 8 KV heads / head_dim 128；1.7B=28 层 / 8 KV heads / 128；0.6B=28 层 / 8 KV heads / 128 |
| 数据指纹 | `data/variants_v3/manifest.json` SHA `6b3d63ae…c2ff9`；`fully_repaired/train_seed0.jsonl` SHA `9b035227…91e953`；`fully_repaired/val_seed0.jsonl` SHA `19e9839e…c595`；与 manifest 登记逐项一致 |

**调度**：全部 GPU 作业严格串行（一次一个进程，无并发抢卡）。

---

## 1. Pilot 1（E1 单缺陷干预筛查）

### 1.1 字面命令 → ABORT（冻结角色门）

按任务给出的字面组合执行（`--variant fully_repaired --panel A`，train=`fully_repaired/train_seed0.jsonl`，
val=`legacy_bundle/val_seed0.jsonl`）：**在模型加载前即被冻结入口的 Panel 角色门拒绝**：

```
Panel A requires (train,val) variants ('fully_repaired', 'fully_repaired');
hash matches train=['fully_repaired'], val=['legacy_bundle','dedup_only']
```

产物：`reports/_non_authoritative/v3_g2_pilot/v3_E1_fully_repaired_s0_smoke/`
仅含 `config.json` + `manifest.json`（`status=ABORTED`），**无 `scores.jsonl` / `metrics.json`**，如实入账。

根因：冻结 G1 入口把 `CLEAN_VARIANT=fully_repaired` 作为 Panel A 的“clean v2.1 val”；
而任务描述把 `legacy_bundle/val_seed0.jsonl`（generator 458de18，历史参照）称为“clean v2.1 val”。
二者不一致。按“不自行修正实验设计”约束，本轮**未修改**冻结入口、未改数据、未替换哈希。

### 1.2 技术桥接 smoke（冻结一致的 clean val）→ PASS

为验证 E1 的 GPU 技术路径，用同一冻结入口、同一 seed/变体/Panel，仅把 val 换成冻结一致的
`fully_repaired/val_seed0.jsonl`，以新 run-id 运行（非权威、非字面指令、非科学结果）：

| 项 | 值 |
|---|---|
| run_id | `v3_E1_fully_repaired_s0_smoke_bridge` |
| 配置 | variant=fully_repaired, panel=A, seed=0, 28→28 identity, affine λ=1e-3, bf16/sdpa, zero-re-prefill=true |
| 输入哈希 | train `9b035227…`, val `19e9839e…`, manifest `6b3d63ae…`（运行时重算一致）；无 test 路径 |
| 规模 | n_train=120, n_val=6, n_scores=48（8 臂 × 6 对），families=6 → exploratory=true |
| 峰值显存 | 4450.0 MiB allocated / 4464.0 MiB reserved（独立探针实测） |
| 耗时 | 88.3 s（入口 metrics）；探针 18.4 s |
| forward 计数 | 总 14（离线 cache capture 10 + inference 4），inference 输入长度 `[7,7,7,7]`，无 doc token |
| cache 形状 | teacher/student/mapped 均 28 层 × (8, 25, 128) |
| Self / Identity | identity 注入与原 Self 的 g 值最大差 **0.0**；Self/Identity/Joint/control 等 8 臂齐全 |
| zero-re-prefill | **True**（basis = forward_audit；strict `verify_zero_re_prefill` 通过） |
| 判定 | **技术路径 PASS**；字面指令因冻结角色门 **BLOCKED（需 PI 澄清 clean val 归属）** |

---

## 2. Pilot 2（E5 第二模型对 4B→1.7B）

| 项 | 值 |
|---|---|
| pilot ID | `v3_E5_pilot_s0` — **NON-AUTHORITATIVE，pilot ID，不是正式格** |
| 入口 | `experiments.P1_gpu.py`，seed 0，n_train=6，n_val=6，eval_splits=val（无 test） |
| 模型 | teacher `Qwen3-4B` / student `Qwen3-1.7B`，两份 `config.json` SHA 与 manifest 一致 |
| layer map | 36→28 **proportional**：`{0:0,1:1,2:3,3:4,…,26:33,27:35}` |
| 耗时 / 计数 | 42.0 s；n_captures=60，n_injections=240；identity E_CF 结构自检 = 0.0 |
| 峰值显存 | **11039.5 MiB allocated / 11054.0 MiB reserved**（4B+1.7B 同卡，远低于 32607 MiB，无 OOM） |
| 探针耗时 / forward | 21.2 s；inference 输入长度 `[7,7,7,7]`（doc token 0） |
| cache 形状 | teacher 36 层 (8,25,128)；student 28 层；mapped 28 层 (8,25,128) |
| **非等深注入修复** | `resolve_injection_layer_map` 在学生空间缓存上返回 **None（恒等）**；层号项等于 source map、无取模回绕；V-stamp 实测读取顺序为 `0,1,…,27`（逐学生层正确）；`per_layer_injection_correct=true` |
| Self / Identity | logits 最大差 **0.0** |
| zero-re-prefill | **True**（strict forward audit） |
| 判定 | **PASS**（技术路径与注入修复在真实 36→28 模型上成立） |

**处置**：在 `reports/runs/v3_E5_pilot_s0/` 增加 `PILOT_NOTICE.json`，显式标记
`authoritative=false / formal_cell=false`；该注释在 `P1_gpu.py` finalize 之后加入，故未写入其
`manifest.json`（保持原 run 产物不被改写）。P1_gpu 打印的 E_CF / 决策字段**不解释为结果**，
仅为 6 对单 seed 的烟测输出；未据此做任何科学判断，未运行 E5 正式矩阵。

---

## 3. Pilot 3（E2 技术路径，非 test）

| 项 | 值 |
|---|---|
| 入口 | pilot-only `reports/_non_authoritative/v3_g2_pilot/e2_path_probe.py`（**未调用** `e2_test_evaluator.py`） |
| 固定配置 | affine λ=1e-3；kd_only epochs=8 / lr=1e-3 / lam_kd=1.0 / lam_cf=0 / lam_reg=1e-4；bf16/sdpa；seed 0；mappers=(affine, kd_only) —— 与 E2 冻结配置一致 |
| 数据 | train=`fully_repaired/train_seed0.jsonl`（`9b035227…`），val=`fully_repaired/val_seed0.jsonl`（`19e9839e…`），n_train=6, n_val=6；**路径与每行 split 双重拒绝 test**，未读 test 内容 |
| 模型 | pinned 1.7B / 0.6B（SHA 命名链接），28→28 identity |
| 峰值显存 | 4483.3 MiB allocated |
| 耗时 | 151.4 s（两者合计） |
| forward / zero-re-prefill | strict `inject_and_generate` 审计输入长度 `[7]`，doc token 0 → **True** |
| 路径验证 | affine 与 kd_only 均成功加载并在 6 对非 test val 上产出有限分数（`results_non_authoritative`，仅作路径 sanity，**不作结论**） |
| 判定 | **PASS（技术路径）**；E2 one-shot test 评测仍属 G3，**未放行、未执行** |

---

## 4. Pilot 4（E6 预算匹配内部对照 `v3-BM-MLP-KD`）

### 4.1 首次尝试 → ABORT（实现缺陷，已记录）

`v3_E6_BM-MLP-KD_s0_smoke`：`RuntimeError: Expected all tensors to be on the same device, but found
at least two devices, cuda:0 and cpu!`。根因：mapper 模块默认建在 CPU，而学生与 mapped cache 在 CUDA。
该失败 run 目录（`config.json` + `manifest.json`，无 scores）**保留入账**，不覆盖。

### 4.2 修复后重跑 → PASS

修复：训练函数把模块 `.to(device)`（学生所在 CUDA 设备），使 K/V 映射与 re-RoPE/前向同设备。

| 项 | 值 |
|---|---|
| run_id | `v3_E6_BM-MLP-KD_s0_smoke_r2`（NON-AUTHORITATIVE pilot，非正式格） |
| 参数 | `trainable_params=7,340,032`；仅 `W_K/W_V`，各 (28,8,128,128)，**bias_params=0**；identity init |
| 冻结超参 | epochs=8, lr=1e-3, lam_kd=1.0, lam_reg=1e-4, lam_cf=0, seed=0 |
| 目标 | `L_KD = Σ_sides KL(log_softmax(mapped)‖log_softmax(self), log_target=True, reduction='batchmean')`；`loss = 1.0·L_KD + 1e-4·reg (reg=0)` —— 与 `kd_gpu.py:140-147` 同式；loss_first=4.480 → loss_last=0.0065，全部有限 |
| 计数 | 48 optimizer steps；训练 student forward 96；eval injections 36；captures 49；n_scores=18 |
| 峰值显存 | 4597.7 MiB allocated / 4658.0 MiB reserved |
| 耗时 | 26.9 s（train 23.9 s） |
| Self / Identity | logits 最大差 **0.0**；cache 形状 28 层 (8,25,128) |
| zero-re-prefill | **True**（训练前向长度审计 + Joint strict forward audit 双通道） |
| 判定 | **PASS** |

---

## 5. 门控结论

| 包 | pilot 结论 |
|---|---|
| E1 | **技术路径 PASS**（桥接 smoke）；字面指令 **BLOCKED**（clean val 归属与冻结 G1 入口不一致，需 PI 澄清） |
| E5 | **PASS**（真实 36→28 注入修复、Self/Identity、zero-re-prefill、显存均通过） |
| E2 | **技术路径 PASS**（固定 affine/kd_only 配置在非 test val 上运行；test 评测属 G3 未执行） |
| E6 | **PASS**（修复设备 bug 后：参数预算、KL 目标、显存/时间、zero-re-prefill 全通过） |

**G2 技术 pilot 总门：CONDITIONAL PASS** —— 四个包的技术路径均可用；但 E1 存在一处**冻结语义冲突**
（见 §1.1），需 PI 裁决后方可把 E1 纳入 G3。未运行任何正式格；未产生任何科学结论；未读 test。

---

## 6. Blockers / 需 PI 裁决事项

1. **E1 clean val 归属冲突（阻塞 E1 进入 G3）**：任务字面指定 `legacy_bundle/val_seed0.jsonl` 为
   “clean v2.1 val”，但冻结 `e1_variant_gpu.py` 的 `CLEAN_VARIANT=fully_repaired`（generator efc3ba3，
   其 manifest 注记 “v2.1 fully repaired”），Panel A 强制 `(train,val)=(variant, fully_repaired)`。
   请 PI 明确：Panel A 的 clean val 究竟取 `legacy_bundle` 还是 `fully_repaired`；若取前者，需由 PI
   按程序修改冻结入口/规格，**工程师本轮不擅改**。
2. **E6 设备 bug 已修但首跑留痕**：`v3_E6_BM-MLP-KD_s0_smoke`（ABORTED）与 `_r2`（PASS）均保留；
   后续正式格应只引用修复后代码，不复用首跑目录。
3. **E2 one-shot test 评测未执行**：G3 未放行；本轮仅验证技术路径，不构成 E2 结果。
4. **正式统计/审阅门 G4 未放行**：本轮所有数字（含 E5 P1_gpu 打印的 E_CF、E2 6 对 sanity 分数）
   均为非权威烟测，不得进入论文、不得与归档结果合并。

---

## 7. 本轮写入清单（均在授权边界内）

| 文件 | 性质 |
|---|---|
| `src/readkv/mapper/mlp_kd.py` | 新增 `v3-BM-MLP-KD` 干净实现 + 训练函数 |
| `experiments/v3_e6_control_gpu.py` | 新增 E6 入口（哈希/路径拒绝/`--cpu-selfcheck`/`--smoke`/`--out-dir`） |
| `tests/test_v3_e6_control.py` | 新增 6 项单测（参数量=7,340,032、无 bias、冻结守卫、入口自检） |
| `reports/_non_authoritative/v3_g2_pilot/**` | pilot 产物、探针、SHA 命名链接、失败/桥接 run 目录 |
| `reports/runs/v3_E5_pilot_s0/PILOT_NOTICE.json` | E5 pilot 非权威注释（pilot ID，不是正式格） |
| `reports/review/v3_g2_pilot_report.md` | 本报告 |

**未写入**：`configs/**`、`papers/**`、`docs/decisions/**`、`data/**`、任何冻结文件；
未修改 `e1_variant_gpu.py` / `P1_gpu.py` / `e2_test_evaluator.py`。

**回归**：修改后全量单测 **97 passed**（原 91 + 新增 6）；`py_compile` 三份新 py 文件通过。

---

**签署：工程师（G2 技术 pilot 实现与执行；2026-11-25）。所有 GPU 数字为 pilot 烟测，非科学证据。**
