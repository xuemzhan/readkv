# 干净数据方向性翻转 · 紧急对抗性复核报告

> 审稿人：reviewer（对抗性审阅 / readkv）。日期：2026-11-23。
> 性质：紧急复核（PI `docs/decisions/clean_data_reversal_ruling.md` §5 触发，不阻塞在跑 kd_only）。
> 依据：`clean_data_reversal_ruling.md`、`reports/data/{data_fix_report.md,acceptance_checks.json}`、`configs/prereg/stats_convention_v2.3.yaml`、`reports/runs/p1_clean_mvp_seed{0,1,2}/**`、`reports/runs/p1_gpu_mvp_repro_seed{0,1,2}/`（旧对照）、`git diff 458de18..efc3ba3`、跑分代码与 hooks/backend。
> 当前 HEAD=`efc3ba3`。**范围**：判定翻转是「真实科学结果」还是「实现 bug」，并评估 PI 的贡献降级/撤回裁定是否成立。本轮未改代码/`scores.jsonl`/prereg/论文。

---

## 0. 总体判定（先给结论）

> **判定：翻转可信（可信度：高）。这是真实科学结果，不是实现 bug。**

理由链（逐项证据见 §1–§4）：P1 跑分路径代码在旧新两个 commit 间**逐字未变**；唯一代码改动是新增一个 P3 专用可微 readout（P1 不调用）+ 数据生成器 M1–M3 修复；旧数据确证含退化对与 train/test 泄漏；干净数据 E0 实现门仍 PASS、Self/Identity 锚点健康（甚至更好）；三 seed 一致地出现 joint 坍塌而 K-only/V-only 近 Self。据此 PI 的「贡献(1) 降级、贡献(2) 撤回、走失败边界研究」裁定**成立**。

但复核发现 **3 项需 PI 处理的副作用/披露问题**（数据哈希未入 run 产物、v2.3 文件哈希不一致、索引未更新）与 **1 项叙事精度问题**（「E_CF 与控制相当」措辞略强）——均为披露/溯源层，不改变「翻转可信」结论（见 §5）。

---

## 1. 必做动作执行结果

| 动作 | 结果 |
|---|---|
| `.venv/bin/python -m scripts.bootstrap_ci_report` | 成功，26 runs；输出结构已按 v2.3 重组（`stats_convention`/`cluster_bootstrap_convention`/`flip_denominator`/`runs`）→ `reports/bootstrap_summary.json` |
| `.venv/bin/python -m scripts.consistency_check` | checked=26, failed=22 → `reports/consistency_report.json`（失败原因见 §5.3，非数据修复 bug） |
| prereg 完整性 | 受 git 跟踪的 v2.1/v2.2/phase1/phase3/protocol `git diff HEAD` = 空（未篡改）；**v2.3 未纳入 git 跟踪**，其当前 sha256=`e44c6acb…` 与 manifest/验收记录的 `5200940c…` 不一致（见 §5.2） |
| 数据哈希 | `sha256sum data/tasks/cf_pairs.jsonl` = `f910f1f1…a894a`，与 manifest/修复报告/裁决一致 ✅；**但三个 run 产物中未记录该哈希**（溯源缺口，§5.1） |

---

## 2. 新 P1 三 seed 产物与复算

### 2.1 完整性与 provenance ✅

三个 `p1_clean_mvp_seed{0,1,2}` 均含 6 文件（config/metrics/scores/ecf_ledger/manifest），`git_hash=efc3ba3`(=HEAD)、`zero_re_prefill=true`、`dtype=bfloat16`、`kernel=sdpa`、`bootstrap_seed={0,1,2}`、`seeds=[0,1,2]`、mapper=affine、identity layer_map(28→28) 齐全。consistency_check 对三个 clean run 均 `ok=true/traceable=true`。数据质量字段完整：`degenerate_must_flip_pairs=0`、跨 split 重叠(context/query/edited_span/source/cluster)全 0、实体池重叠全 0、`flip_denominator=398 (excludes F5,F6)`、template_family 共 56 族/24 结构、train/test 骨架不重合。

### 2.2 从 scores.jsonl 独立重算 ✅（与 metrics/PI 上报一致）

| seed | joint E_CF | joint dual | Self dual | flip | coverage | mismatch/zero 控制 E_CF |
|---|---|---|---|---|---|---|
| 0 | 6.900 | 0.417 | 0.817 | 0.750 | 0.867 | 8.383 / 8.584 |
| 1 | 8.159 | 0.283 | 0.900 | 0.736 | 0.883 | 9.046 / 9.065 |
| 2 | 8.540 | 0.383 | 0.783 | 0.755 | 0.883 | 9.432 / 9.684 |

全部与裁决 §0 数值一致。joint dual 较 Self 下降 0.400/0.617/0.400，远超 0.2 阈值 → `transfer_broken=true` 可信。E_CF 为 Self 锚点（=0）的 6.9–8.5 倍，方向明确。

### 2.3 E0 干净数据复验 ✅

`e0_clean_mvp_seed0`：min_cos=1.0、max_KL=0、EM=0.975（≥0.929）、round-trip bit-identical、zero-re-prefill 全 True、误差上限 2.2e-16 ≪ 效应/3 → **PASS**。实现门在干净数据上仍成立，排除「数据重建引入 tokenization/注入实现回归」的担忧。

---

## 3. 排除实现 bug（核心审查）

### 3.1 跑分路径代码逐字未变 ✅

`git diff 458de18 efc3ba3` 对跑分关键路径的结果：

| 文件 | 差异 |
|---|---|
| `experiments/P1_gpu.py` | **无差异** |
| `src/readkv/evaluate/cf_pipeline.py`（含 `annotate_transfer_health`、`run_cf_pipeline`） | **无差异** |
| `src/readkv/models/hooks.py` | **无差异** |
| `src/readkv/evaluate/counterfactual.py` | **无差异** |
| `src/readkv/models/layer_map.py`、`mapper/representation.py` | **无差异** |
| `src/readkv/models/gpu_backend.py` | +68 行：仅**新增** `torch_candidate_logits()`（P3 可微 readout），现有 `candidate_logits()` 逐字未改 |
| `src/readkv/data/build_cf_pairs.py` | +416/−174 行：M1 候选相异/退化对断言、M2 split 不相交实体池、M3 结构未见模板 |

**P1_gpu.py 经 `run_cf_pipeline` → `candidate_logits` 打分，不调用新增的 `torch_candidate_logits`**（grep 确认）。故新旧运行的模型前向、注入、de-RoPE/re-RoPE、position offset、layer_map、候选 readout、E_CF 定义、transfer_health 逻辑**完全一致**；唯一实质变化是**数据内容**。翻转只能来自数据修复，非代码回归。

### 3.2 旧数据缺陷得到直接证实 ✅

从旧 `p1_gpu_mvp_repro_seed0/scores.jsonl` 直接观察：候选存在 `('王五','王五')`、`('周八','周八')` 等**候选相相同或实体退化的 pair**；val 的 9 个 template_family 全部为后缀 `-C` 的同源变体（结构仅 8 类），与 train 共用全部 8 个姓名实体。这与修复报告「退化对 18、train/test 模板骨架 100% 重合、8 姓名全共享」一致。修复后候选全相异（F5 非翻转负控除外）、模板骨架 train∩test=∅、实体池不相交。**旧 gap 建立在退化对 + 泄漏之上，属数据缺陷假象——该判断成立。**

### 3.3 排除候选顺序/符号/位置类 bug ✅

- 干净数据 self arm 的 `candidate_A != candidate_B` 对全部 must_flip 样本成立；`D_self≈0` 的 7 对**全部是 F5**（`must_flip=false` 的非翻转负控，设计使然），非 bug。
- Self 锚点 dual 在干净数据上为 0.783–0.900（旧数据 0.683），**自然学生在干净数据上答得更好**，说明数据质量提升而非破坏；若数据重建破坏 tokenization/位置，Self 锚点应先崩塌，事实相反。
- K-only / V-only 的 dual 仍达 0.80、flip≈0.94–0.98（近 Self），只有 Joint（两端均映射）坍塌——这是「mapper 在未见面实体/结构上的泛化失败」的典型模式，而非全局实现回归。

### 3.4 v2.3 统计口径复核 ✅

v2.3 bootstrap 以 `template_family` 为主聚类单元、同时输出 pair-level 敏感性、族数<24 标 `exploratory`。干净 val 只有 **8 个 template_family**（<24），故三个 clean run 均正确标 `exploratory=true`；template-family CI 明显宽于 pair 级（seed0 joint `6.900 [3.564, 10.100]` vs pair `[5.496, 8.321]`），但**下界仍 >0**，方向稳健。flip 分母 398 与 manifest/代码一致。统计口径正确实现，无「只报窄 CI」「按测试改聚类」违规。

---

## 4. 混合信号的精细判读（PI §5.2 关注点）

`transfer_broken=true` 由三条 OR 信号中的**一条**（dual drop=0.4≥0.2）触发；另两条**未触发**：

- `joint_ecf_ge_control`：mismatch/zero 均 **false** —— joint E_CF（6.9–8.5）**仍低于**错配/零缓存控制（8.4–9.7）；
- `info_attribution`：seed0 为 mismatch +1.48 / random −0.13 / zero +1.68 —— **2 正 1 负**，`info_mostly_negative=false`。

即：这是「**joint dual 坍塌 + E_CF 远离 Self，但正确缓存仍部分优于错配/零控制**」的混合信号，不是「joint E_CF 完全达到/超过无信息控制」的彻底无信息状态。裁决 §1.1「E_CF 与错配/零缓存控制相当」的表述**略强于数据**：准确说法是「E_CF 大幅升高、接近但尚未超过错配/零控制，且伴随 dual 坍塌」。**这不改变 broken-transfer 定性**（dual 坍塌 0.4 是充分且最稳健的失败信号），但论文应据此精确措辞，避免夸大（见 §5.4）。另注：verdict_note 文本写「frozen verdict=None」而实际 `decision.verdict=distortion_exists`，属注释模板的字符串小瑕疵，不影响冻结判据本身。

---

## 5. 风险与需 PI 处理事项

| 编号 | 发现 | 等级 | 是否影响「翻转可信」 |
|---|---|---|---|
| S1 | 三个 clean run 的 `config.json`/产物**未记录数据哈希** `f910f1f1…a894a`，run→数据无法从 run 产物单独绑定 | 次要 | 否（但削弱可复现溯源，建议补 metadata 勘误） |
| S2 | v2.3 为**未跟踪文件**，当前 sha256=`e44c6acb…` ≠ manifest/验收记录 `5200940c…`；§4 显示 `recomputed_value` 由 null 回填为 398，但回填后未更新两处哈希，且 null→398 之外的差异使哈希无法用单一回填解释 | **主要（溯源/冻结一致性）** | 否（统计口径内容与实现一致、无按测试改判据证据），但须 PI 澄清回填过程并重算哈希，排除「冻结后被改」疑虑 |
| S3 | `runs_index.json`/`errata` **未更新**：clean run 未入索引、旧 repro run 未标 superseded；`consistency_check` failed=22 除 8 个旧 superseded 外，14 个旧 run 因 HEAD 前进（gpu_backend.py 增方法）触发「run code differs vs HEAD」 | 次要 | 否（clean run 全 ok；失败为代码演进的正常连带），但须更新索引避免下游误用旧数 |
| S4 | 「E_CF 与错配/零控制相当」措辞略强（实测 joint E_CF 仍低于控制、info 2 正 1 负） | 次要（披露） | 否；论文须按 §4 精确措辞 |
| S5 | `transfer_broken` 仅由单一信号（dual drop）触发、且 `exploratory=true`（8 族<24） | 次要（强度） | 否；不得作「强显著性/跨对泛化」主张 |

---

## 6. 对 PI 裁定的复核意见

| PI 裁定 | 审稿复核 | 依据 |
|---|---|---|
| 贡献(1) 立即冻结降级 | **成立** | utility-preserving 前提塌陷：joint dual 0.28–0.42 vs Self 0.78–0.90；旧 gap 系退化对+泄漏假象（§3.2/§3.3） |
| 贡献(2) 立即撤回 withheld（不等 P2） | **成立** | 机制对象（干净失真）不存在；旧 P2 建立在污染数据上；无需再投入 P2 算力 |
| 走失败边界研究 / 数据泄漏教训的负面结果论文 | **成立** | 前后对照实证充分（旧 1.93–2.12/broken=false ↔ 新 6.9–8.5/broken=true），方法学教训有据 |
| 贡献(3) withheld、P3 取消、投稿暂缓 | **成立** | 主终点未评估、无机制/方法证据 |

**条件建议**：在维持上述裁定的同时，要求工程师闭环 S1/S2/S3（数据哈希入产物、澄清 v2.3 回填并重算哈希、更新索引），要求写作者按 §4/S4 精确措辞并保留 `exploratory`/单对/合成域边界。这些是溯源与披露层的收尾，不阻塞方向裁定。

---

## 7. 阶段与门控建议

- **方向裁定**：维持 PI 紧急裁决——贡献(1) 降级、贡献(2) 撤回、失败边界/数据教训重新定位。翻转可信（高），**无需停冻结待工程修复**（无实现 bug）。
- **kd_only 三 seed**：继续完成，按裁决 §3.3 的 A/B/C 预承诺判读（失败边界确认择支）。
- **P2/P3/P4**：维持取消/NO-GO（前提已塌，不投入新算力）。
- **P5**：维持暂缓；重开投递须先闭环 S1/S2/S3 + 论文按新定位重写 + 本复核确认。
- **是否需工程修复**：不需要针对「翻转」本身修复；仅需完成 §5 溯源/索引收尾。

---

## 8. 结论

紧急复核确认：干净数据 P1 三 seed 产物完整、provenance（除数据哈希未入产物外）齐全；从 scores 独立重算的方向性坍塌（E_CF 6.9–8.5、dual 0.28–0.42、transfer_broken=true）属实；**跑分代码逐字未变、唯一变化是数据生成修复与一个 P1 不调用的 P3 新方法**，旧数据的退化对与 train/test 泄漏被直接证实，干净数据 E0 仍 PASS、Self/Identity 锚点健康。据此判定 **翻转可信（高），是真实科学结果而非实现 bug**，旧 gap 为数据缺陷假象成立。PI 的贡献(1) 降级、贡献(2) 撤回、转失败边界研究裁定**复核通过**。附 5 项溯源/披露层收尾事项（S1–S5），均不改变主判定。**是否按新定位重开 P5 与措辞定稿由 PI 裁决，审稿侧不定稿。**

**签署：reviewer（对抗性审阅），2026-11-23。**
