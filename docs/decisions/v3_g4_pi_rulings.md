# G4 风险项 PI 裁定（v3.0 新研究 · 2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行 G4 收口）。
> 依据：`reports/review/v3_g4_compliance_review.md`（CONDITIONAL PASS，R1–R4）、`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN，SHA `d8c2321fc4ba6abeda80e6f581d3f7ef6c592c9173de757aad1a40120ae811e6`）、`reports/review/v3_g3_batch1_report.md`、`reports/review/v3_g3_batch2_report.md`。
> 性质：对审查风险的裁定；不改冻结判据、不改运行产物、不改论文。

---

## R1（主要）— `config.json:protocol_version` 不一致 → **接受为陈旧元数据，非判据切换**

- 事实：E1/E6 写 `"3.0"`，E2/E5 写 `"2.0"`；E5 的 `experiment_config.prereg` 仍指向 `phase1_benchmark_decision.yaml (frozen protocol-v2.0)`。
- 核验：所有 run 的冻结判据字节 SHA 均为 `d8c2321f…20ae811e6`（v3.0 原文未改）；E2 `metadata.prereg_version=3.0`；batch1 §0 已逐项复核 prereg 哈希未变。该字段来自复用的 `RunContext` schema 默认值/旧入口模板，不是运行时实际采用的判据。
- **裁定：不构成判据切换或先跑后改。** 权威判据身份以 `configs/prereg/gpu_followup_v3.0.yaml` 的字节 SHA 与 run `experiment_config` 中记录的 prereg 哈希为准；`protocol_version` 仅为陈旧字符串。不得据该字段重判任何结果。

## R2（主要）— `consistency_check.py` 103/103 FAIL → **接受直接 SHA-256 证据标准**

- 事实：工具因工作区非 git 仓库（`head_hash=""`）及 v2 时代 `PAIR_EXPECT` 的模型对/层映射预期而全失败。
- 核验：reviewer 以直接 SHA-256 复验 122 个文件、0 处不一致；`reports/review/v3_g{1,2,3_batch1,3_batch2}_*.md` 中的哈希链自洽。
- **裁定：工具失败属环境/版本限制，不是 v3 研究发现。** 本次以直接文件哈希核验替代 `consistency_check` 作为不可变性证据；不把该 FAIL 记入 v3 科学结论，也不据此改动任何产物。

## R3（主要）— 科学家报告曾为占位未签 → **以重新签发为准**

- 事实：`docs/audit/v3_statistical_interpretation.md` 首版因子 agent 读白名单不含 `reports/**` 而全部为 `⟨FILL⟩`，未签发；该「不伪造」处理正确。
- 处置：已将 39 个 run 的 `config/scores/metrics/manifest` 与相关报告做**逐字节只读副本**至 `docs/audit/v3_g4_inputs/`（178 文件、`SHA256SUMS.txt`，抽样源/副本哈希一致），解除读限制；科学家正在据此重算并替换全部占位符。
- **裁定：R3 在科学家签署带数值与分支裁决的版本后关闭。** 在此之前 G4 不得视为双签完成，不得对外引用占位版。

## R4（次要，知悉）— 接受诚实限制，不补测、不重跑

1. E2 冻结 evaluator 未落盘 peak memory / elapsed / forward count / cache 形状 / Self–Identity 差值：属已知实现限制，报告已如实标注，**未伪造**；E2 one-shot 已用尽，不得为补指标重跑。
2. 通用 `bootstrap_ci_report.py` 会把 E2 六格合并为单一 `arm="unknown"`：禁止用于 E2 推断；E2 只用 dedicated evaluator 自带的逐格 family CI（`exploratory=true`，no pooled inference）。
3. `v3_E5_pilot_s0` 为非权威 pilot，使用裸 master 快照路径；所有正式格均用 SHA 钉住链接。该 pilot 仅作技术门证据，不进入统计或结论。

---

**签署：PI / 课题组长（G4 风险裁定 · 2026-11-25）**
