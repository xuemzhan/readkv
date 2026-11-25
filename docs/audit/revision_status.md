# 本轮修订状态（基于 docs/audit 审稿结论与修改方案）

**范围**：用户选定「先做可行部分」+「四份稿件同步」。本机无 CUDA（`torch 2.14.0+cpu`），因此所有需要 GPU 的实验没有运行，也没有伪造其结果。

## 已完成

| 项 | 产物 | 说明 |
|---|---|---|
| E3 对照 CI + 配对检验 + TOST | `scripts/audit_reanalysis.py`、`configs/prereg/equivalence_margin_v2.9.yaml`、`reports/audit_reanalysis.json`、`docs/audit/reanalysis_results.md` | δ=2 先声明；发现审稿人建议的「与零信息对照无法区分」并不普遍成立：seed 0 对 zero 显著更小（p=0.010），TOST 仅 seed 1 全部成立 + seed 2 random 成立。已按数据如实改写。 |
| E4 E_CF 效度 | 同上 + `papers/readkv_v2_tmlr_anonymous/figures/fig7_ecf.{pdf,png}` | 归一化比值 0.32→0.80–0.90，说明不只是量纲变化；Spearman ρ 在两 mapper 间反号（−0.436 / +0.435）；E_CF CI 重叠而 dual 差 28–45 点。 |
| E7 序列打分扩展 | 同上 | F1–F4 只有 6 个 family；扩到全部 60 对得 8 个 family，seed 1 A11 61.7→40.0（−21.7 点），方向保留、仍 exploratory。 |
| 文本重构 | 四份 `papers/readkv_v2_*/main.tex` 全部同步；`papers/readkv_v2_draft/cover_letter.md` 更新 | 摘要/引言改为正向叙事；新增三个结果子节与附录表；合并为单一 Scope of claims；删除 Status/PI 签字/commit hash/P2–P4/G1/scenario C 等内部痕迹；CF-RCT/M4/SQuAD 压缩或移出证据链。 |
| 可复现性 | `scripts/reanalysis_tables.py`、`scripts/check_manuscript.py`、`tests/test_audit_reanalysis.py`、更新 `README.md` / `run_all.py` / `verify_figures.py` | 新增表由 JSON 生成，不手写数字；5 个新测试通过；四份稿件静态检查 0 issue；7 张图重生成并通过 verify_figures。 |

## 未完成（明确写入稿件 Limitations，需 GPU）

- **E1** 单缺陷干预（只去重 / 只去退化对 / 只换模板 / 只实体互斥）：因此不声称泄漏的定量归因。
- **E2** sealed test 评测（300 对从未评测）。
- **E5** 第二个模型对（4B→1.7B）：因此不声称跨模型泛化。
- **E6** 已发表方法基线 / 参数匹配变体：kd_only 预算不对称仍披露。
- **E8** SQuAD 锚点未重做，仅保留一句地板效应说明，不作证据。

## 已知限制

- 本机无 LaTeX 引擎，`papers/readkv_v2_tmlr_anonymous/main.pdf` 与 `supplement.zip` 仍是旧版；投稿前须在带 TeX 的机器上重新编译并更新匿名补充包。
- `python -m pytest`：79 tests，**77 passed / 2 failed**；失败项为 `tests/test_hooks.py::test_capture_inject_identity_matches_full_prefill` 与 `tests/test_sequence_scoring.py::test_score_candidate_sequence_cpu_tiny`（transformers 版本导致的 layer-0 K/V hook 兼容问题，与本轮改动无关）。新增的 5 个 reanalysis 测试全部通过。
