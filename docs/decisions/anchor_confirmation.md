# SQuAD 锚点确认与评测 run 授权（V2.0 · 锚点先行）

> 裁决人：PI / 课题组长。日期：2026-11-23。
> 触发：数据工程师完成 SQuAD 锚点归档与五项登记（`reports/data/{squad_anchor_manifest,anchor_archive_checklist}.md`），提交 PI 锚点确认；承接 `docs/decisions/m4_blocker_ruling.md` §3"锚点先行、独立于 M4"。
> 依据：`configs/prereg/external_validity_v2.4.yaml`（先冻后跑、仅评测、预承诺三情形、不恢复贡献）、`reports/data/anchor_license_check.md`、`docs/decisions/human_decisions.md`。
> 本确认只写决策文档，不改任何冻结文件（含 v2.4/v2.5）、数据文件、`reports/runs/**`、论文；不写代码、不跑实验。

---

## 1. 锚点归档确认

> **裁定：确认 SQuAD 锚点归档与五项登记合规，授权工程师启动锚点评测 run。**

### 1.1 五项登记核验（PI 确认）

| # | 登记项 | 归档值 | 确认 |
|---|---|---|---|
| ① | 来源 URL/标识 | 官方 `rajpurkar.github.io/.../dev-v2.0.json`（实测 HTTP 200）+ HF `rajpurkar/squad_v2` | ✅ |
| ② | 版本/日期 | SQuAD v2.0 dev，文件内 `version:"v2.0"`，下载 2026-11-23T12:20:06Z | ✅ |
| ③ | 许可证原文 | CC BY-SA 4.0，legalcode 原文归档（20,138 B，sha256 `28a9529c…fd1cf5`） | ✅ |
| ④ | 原始文件真实 sha256 | `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`（4,370,528 B，`sha256sum` 实测） | ✅ |
| ⑤ | 处理脚本 commit | 归档时 HEAD `5bbb5dbf…` | ✅（收尾见 §1.3） |

- **内容真实性独立佐证**：PI 本轮独立 webfetch 实测 `dev-v2.0.json` 返回 `version:"v2.0"`、首条 title=Normans / Q="In what country is Normandy located?" / A=France，与归档报告 §2 一致；35 篇/1,204 段/11,873 问与官方规格吻合，确为官方 dev 真实字节，非占位/合成。
- **用途合规**：仅评测、不改写、不再发布衍生语料 → **CC BY-SA 的 SA 义务不触发**（SA 仅在再发布改编材料时生效）。
- **隔离确认**：未修改合成 `cf_pairs.jsonl`（仍 `f910f1f1…a894a`）与 manifest，未触碰任何冻结文件。

### 1.2 授权范围

授权工程师按 v2.4 启动 **SQuAD 锚点评测 run**（仅 seed0、仅评测）。**本授权不含**：任何 real split 入库、任何合成主终点重算、任何贡献恢复——real 仍受二次签off + 标注口径（v2.5）约束。

### 1.3 收尾项（不阻塞本次授权）

1. 第⑤项"处理脚本 commit"当前为归档时 HEAD（`5bbb5dbf…`）；工程师应在下一个纳入归档/评测脚本的 commit 中回填实际处理脚本 commit hash 至锚点登记，完善溯源。
2. 审稿人在阶段复核时用 `sha256sum` 重算归档文件哈希，核对与 `80a5225e…` 一致（例行复算，不作为本确认的前置）。

---

## 2. 给工程师的锚点评测 run 纪律

| 项 | 要求 |
|---|---|
| **run_id** | `anchor_squad_affine_seed0`、`anchor_squad_kd_seed0`（符合 v2.4 `anchor_{squad\|arc}_{affine\|kd}_seed0` 命名） |
| **数据** | 使用已归档 `data/anchors/squad/dev-v2.0.json`（记录文件 sha256 `80a5225e…` 于 run config/report） |
| **臂** | Joint（affine）与 kd_only 两臂，各 seed0 |
| **种子** | 仅 seed0（锚点为外部效度观察，非主终点，不要求 ≥3 seed） |
| **运行配置** | dtype=bfloat16、kernel=sdpa、`zero_re_prefill=true` |
| **provenance** | **新 commit 纳入全部跑分代码**（避免 R1 重演）；每 run `config.json` 含 `git_hash`、`protocol_version`（2.4 相关）、`data_sha256=80a5225e…`、`seed`、`dtype`、`kernel`、`zero_re_prefill`、锚点标识 |
| **执行** | 串行（并发有 3–7× 惩罚）；产物写 `reports/runs/<run_id>/` |
| **指标** | 标准 QA 常规质量（EM/Accuracy）等锚点指标；按 v2.4 `external_anchors` 口径 |
| **统计** | 按 v2.4 口径；锚点结果不在合成 test 主终点 CI 之列 |
| **报告** | 按 **v2.4 预承诺三情形**归类（复现→强化外部效度 / 相反→收窄适用边界不反转叙事 / 混合→探索性披露）；**不恢复任何已撤回贡献**，不构成贡献(3) 证据 |

---

## 3. 锚点评测目的与边界

- **目的**：(i) 检验"affine 迁移失败边界"是否**跨数据源成立**；(ii) 为自建 `E_CF` 提供与标准 QA 的**外部锚点**。
- **明确不是**：重跑或替换 V2.0 合成主终点、贡献(3) 证据、贡献(1)(2) 恢复依据。
- **禁止**：不得把锚点结果与合成 test 混算主终点或重算已冻结 CI；不得据锚点结果改贡献状态或事后择支（v2.4 `forbidden_after_freeze` 全部适用）。
- **披露**（给写作者）：论文/报告如实写明 SQuAD 2.0 dev、CC BY-SA 4.0、仅评测、不发布衍生语料；引用 Rajpurkar et al., EMNLP 2016 (doi:10.18653/v1/D16-1264) 与 Rajpurkar & Jia et al., ACL 2018 (doi:10.18653/v1/P18-2124)。

---

## 4. 后续锚点（顺位，不阻塞本授权）

ARC（AWS `ai2-public-datasets` 公开桶 / HF，CC BY-SA 4.0）与 HellaSwag（HF/GitHub，MIT）按可达性与许可顺位跟进归档；每个均须先完成五项登记 + PI 确认后再启动评测。本确认仅覆盖 SQuAD。

---

## 5. 结论

- **确认**：SQuAD 锚点五项登记齐全、内容真实、仅评测不触发 SA、隔离合规；**授权工程师启动 `anchor_squad_affine_seed0` / `anchor_squad_kd_seed0`**。
- run 纪律见 §2（seed0、bf16/sdpa、zero_re_prefill、新 commit、config 含 git_hash+数据哈希、串行、产物入 reports/runs）。
- 目的为跨数据源外部效度检验，非主终点；按 v2.4 预承诺三情形报告，不恢复贡献，不与合成 test 混算（§3）。
- 收尾：回填处理脚本 commit（§1.3）、审稿重算哈希；ARC/HellaSwag 顺位跟进（§4）。

**签署：PI / 课题组长（SQuAD 锚点确认 · 2026-11-23）**
