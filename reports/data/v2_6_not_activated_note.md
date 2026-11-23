# v2.6 not-activated 合规说明（AI 数据提案已撤回 · 无生成产物）

> 执行角色：数据工程师 · 日期：2026-11-23 · 性质：简短合规留档（只读核验 + 说明，不改数据/判据/论文/运行产物）。

## 1. v2.6 状态：not activated（无适用对象）

- `configs/prereg/ai_generated_data_v2.6.yaml` 保持**冻结不变**，但按 `docs/decisions/ai_dataset_final_ruling.md`（13:11:44）判定为 **not activated / 无适用对象**；`docs/decisions/research_scope_update.md` §5.3（13:43:59，PI 终裁）**维持该状态**。
- `ai_generated_dataset_ruling.md` 的「有条件 GO」已被**撤回**（历史文本保留，以最终裁决为准）。
- 不新增 v2.7；`configs/prereg/` 无 re-enabling 版本。激活须先撤销最终裁决 + 新增 v2.7+ prereg + PI 重新裁决（均未发生）。

## 2. AI 数据提案：已评估并撤回，无生成产物

- 提案（HellaSwag 种子 AI 生成反事实对）经科学家评估（`docs/data/hellaswag_seed_semantic_assessment.md`）与 PI 终裁：**不启动**。
- **未**下载 HellaSwag 字节；**未**创建 `data/generated/`（实测 absent）；**未**写生成脚本；**未**产生任何生成对、manifest、sha256、质量审计或生成 run。
- 无遗留产物；不得在论文/报告中声称存在 human-seeded / model-generated 数据集。

## 3. real=0 维持，锚点为唯一外部效度探针

- `real=0` 不变；贡献(1)(2) 撤回、贡献(3) withheld 不变；P2/P3/P4 不重启；封存 test 不碰。
- **SQuAD / ARC 锚点是唯一获批的外部效度探针**，仅评测（SQuAD 已授权 `anchor_{squad}_{affine,kd}_seed0`），不改写、不再发布衍生语料，不构成贡献证据、不并入合成 test、不重算主终点。

## 4. SQuAD 锚点归档只读核验：齐全 ✅

| 项 | 登记 (`squad_anchor_manifest.md` / `anchor_archive_checklist.md`) | 磁盘实测 | 一致 |
|---|---|---|---|
| ① 来源 URL/标识 | 官方 dev-v2.0.json（HTTP 200）+ HF `rajpurkar/squad_v2` | 归档已记录 | ✅ |
| ② 版本/日期 | v2.0 dev，下载 2026-11-23T12:20:06Z | 文件内 version=v2.0 | ✅ |
| ③ 许可原文 | CC BY-SA 4.0 legalcode，20,138 B | 20,138 B；sha `28a9529c…fd1cf5` | ✅ |
| ④ 原始文件 sha256 | `80a5225e…82d8`，4,370,528 B | `80a5225e…82d8`，4,370,528 B | ✅ |
| ⑤ 处理脚本 commit | 归档 HEAD `5bbb5dbf…` | 归档已记录（收尾项见 anchor_confirmation §1.3） | ✅ |

- **5/5 齐全；文件哈希与登记完全一致；只读确认通过。未重复下载、未改动归档文件。**

**签署：数据工程师（v2.6 not-activated 合规说明 · 2026-11-23）**
