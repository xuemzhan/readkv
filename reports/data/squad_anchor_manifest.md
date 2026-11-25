# SQuAD 锚点归档与五项登记（真实字节，不可伪造）

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/m4_blocker_ruling.md` §0/§1/§3（SQuAD 官方通道打通，授权下载+五项登记）、`configs/prereg/external_validity_v2.4.yaml`（先冻后跑、仅评测、不恢复贡献）
> 性质：**锚点数据归档**（仅评测用途；不改写、不再发布衍生语料；**不启动任何评测 run**，由工程师在 PI 确认后执行）。
> 全部 sha256 均由 `sha256sum` 对**实际下载的字节**计算，非编造。

## 0. 归档结果（已完成）

| 文件 | 真实字节数 | 真实 sha256（sha256sum 实测） |
|---|---|---|
| `data/anchors/squad/dev-v2.0.json` | 4,370,528 | `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8` |
| `data/anchors/squad/LICENSE-CC-BY-SA-4.0.txt` | 20,138 | `28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5` |

下载方式：`curl -fSL https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json`，返回 **HTTP 200**、size_download=4,370,528；许可文本来自 `https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt`（HTTP 200，20,138 B）。下载日期 UTC：2026-11-23T12:20:06Z。

## 1. 五项登记（逐项）

| # | 登记项 | 值 | 齐全 |
|---|---|---|---|
| ① | 来源 URL/标识 | `https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json`；主页 `https://rajpurkar.github.io/SQuAD-explorer/`；HF 官方 `rajpurkar/squad`（v2.0: `rajpurkar/squad_v2`） | ✅ |
| ② | 版本/日期 | SQuAD **v2.0** dev；文件内 `{"version":"v2.0"}`；官方主页标注 Dev Set v2.0；下载日期 2026-11-23T12:20:06Z | ✅ |
| ③ | 许可证原文 | CC BY-SA 4.0；官方主页原文 “distributed under the CC BY-SA 4.0 license”；legalcode 原文已归档 `LICENSE-CC-BY-SA-4.0.txt`（sha256 `28a9529c…fd1cf5`）；论文脚注 “we release SQuAD 2.0 under the CC BY-SA 4.0 license” | ✅ |
| ④ | 原始文件真实 sha256 | `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`（`sha256sum` 实测 4,370,528 B） | ✅ |
| ⑤ | 处理脚本 commit | 归档时 HEAD `5bbb5dbf1829e11ca928d7aed48c5b2671c2d2b8`（下载与校验在本工作区完成；归档脚本 future commit 将另行记录） | ✅ |

**五项登记齐全。**

## 2. 内容真实性校验（确认是官方 dev-v2.0）

| 指标 | 实测值 | 官方规格 |
|---|---|---|
| 顶层键 | `version`, `data` | ✅ |
| version | `v2.0` | ✅ |
| 文章数 | 35 | SQuAD 2.0 dev 35 篇 ✅ |
| 段落数 | 1,204 | ✅ |
| 问题总数 | 11,873 | 官方 dev-v2.0 = 11,873 ✅ |
| 不可答问题 | 5,945 | 官方 ~5,000+ 对抗不可答 ✅ |
| 样本 | title=Normans；Q="In what country is Normandy located?"；A=France | 官方 dev 首条 ✅ |

数据确为官方 SQuAD 2.0 dev 全量真实字节，非占位/合成。

## 3. 用途与红线约束

- **仅评测**：按 v2.4 预承诺，锚点评测由工程师在 PI 确认本登记后执行（`anchor_squad_{affine|kd}_seed0`，bf16/sdpa、`zero_re_prefill=true`、串行、新 commit）。
- **不改写、不再发布衍生语料**：故 CC BY-SA 的 SA 义务不触发（SA 仅在再发布改编材料时生效）。
- **不启动任何 GPU run**：本轮只归档，未跑评测。
- **不触碰合成数据**：`data/tasks/cf_pairs.jsonl`（`f910f1f1…a894a`）、manifest 未改。
- **引用披露**：写作者须在论文引用 Rajpurkar et al., EMNLP 2016 (doi:10.18653/v1/D16-1264) 与 Rajpurkar & Jia et al., ACL 2018 (doi:10.18653/v1/P18-2124)，并注明 SQuAD 2.0 dev、CC BY-SA 4.0、仅评测用途。

## 4. 复现命令

```
curl -fSL https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json -o data/anchors/squad/dev-v2.0.json
curl -fSL https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt -o data/anchors/squad/LICENSE-CC-BY-SA-4.0.txt
sha256sum data/anchors/squad/dev-v2.0.json data/anchors/squad/LICENSE-CC-BY-SA-4.0.txt
```
