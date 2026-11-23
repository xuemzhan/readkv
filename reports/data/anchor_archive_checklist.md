# SQuAD 锚点归档验收清单（提交 PI 锚点确认）

> 执行角色：数据工程师 · 日期：2026-11-23
> 依据：`docs/decisions/m4_blocker_ruling.md` §3（锚点先行：五项登记齐全后由工程师启动评测）
> 结论：**五项登记齐全，归档通过，提交 PI 锚点确认**；确认前不启动任何评测 run。

## 1. 五项登记核验

| # | 登记项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 来源 URL/标识 | ✅ | 官方 dev-v2.0.json URL（HTTP 200 实测）+ HF `rajpurkar/squad_v2`，见 `squad_anchor_manifest.md` §1① |
| 2 | 版本/日期 | ✅ | 文件内 `version:"v2.0"`，下载 UTC 2026-11-23T12:20:06Z |
| 3 | 许可证原文 | ✅ | CC BY-SA 4.0 官方主页声明 + legalcode 原文归档（真实字节 20,138 B，sha256 `28a9529c…fd1cf5`） |
| 4 | 原始文件真实 sha256 | ✅ | `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`（4,370,528 B，`sha256sum` 实测） |
| 5 | 处理脚本 commit | ✅ | 归档 HEAD `5bbb5dbf1829e11ca928d7aed48c5b2671c2d2b8` |

**5/5 齐全。**

## 2. 归档完整性核验

| 检查 | 结果 |
|---|---|
| 下载真实字节（非编造） | ✅ HTTP 200，size_download=4,370,528 |
| 内容真实性（version=v2.0、35 篇/1204 段/11873 问、首条 Normans/France） | ✅ 与官方 dev-v2.0 一致 |
| 许可属可用范围（仅评测、不改写发布 → 不触发 SA） | ✅ |
| 未修改 `data/tasks/cf_pairs.jsonl` / manifest | ✅（cf_pairs sha 仍 `f910f1f1…a894a`） |
| 未启动任何 GPU/评测 run | ✅ |
| 未改 `configs/prereg/**`（含 v2.4）、代码、论文、`reports/runs/**` | ✅ |

## 3. 提交 PI 确认事项

1. 确认 SQuAD dev-v2.0 归档与五项登记合规（本报告）；确认后由**工程师**按 v2.4 启动锚点评测 run（`anchor_squad_{affine|kd}_seed0`），本角色不启动。
2. 确认引用披露（SQuAD 2.0 dev / CC BY-SA 4.0 / Rajpurkar et al. 2016 + 2018）由写作者落实。
3. ARC（AWS `ai2-public-datasets` 公开桶 / HF，CC BY-SA 4.0）与 HellaSwag（HF/GitHub，MIT）按可达性顺位跟进归档（本轮未下载）。
4. 锚点结果按 v2.4 预承诺三情形归类，**不恢复任何已撤回贡献**，不构成贡献(3) 证据。

## 4. 说明

- 许可核验详见 `reports/data/anchor_license_check.md`（SQuAD/ARC=CC BY-SA 4.0，HellaSwag=MIT，均仅评测合规）。
- 归档清单与哈希见 `reports/data/squad_anchor_manifest.md`。
- 本清单只确认锚点归档，**不涉及 real split**（real 仍受二次签off与人工标注阻塞，见 `m4_acceptance_checklist.md`）。
