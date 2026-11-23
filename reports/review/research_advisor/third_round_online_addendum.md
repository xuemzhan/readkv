# 第三轮联网核定（主会话代执行；research-advisor 额度不足）

- 日期：2026-11-23
- 性质：`research-advisor` 因 free usage limit 未能运行；websearch 工具同时不可用。本文件由主会话通过 arXiv API / 页面抓取完成，属于**主会话代执行**，不是独立 agent 的第三轮签署。
- 范围：结合 2026-10/11 最新公开工作，重新核定“原研究能否通过改善数据/算法/实验继续”，以及 PI 的 NO-GO/双轨结论是否成立。
- 证据粒度：以下均核验 arXiv 标题、作者、摘要与日期；未逐篇读全文，章节级细节需后续核验。

---

## 1. 最新关键文献

| 编号 | 论文 / 日期 | 与本项目的关系 | 对原研究的影响 |
|---|---|---|---|
| N1 | **Can KV Cache Be Reused Across Model Updates? A DeepSeek-V4-Flash Case Study**，arXiv:2611.14051，2026-11-10 | 跨版本 KV 复用；提出 **Functional Cache Divergence**；明确“任务 utility”与“对原生行为的 fidelity”是两个不同标准 | **直接 anticipate H1 的核心区分**（虽为跨版本、非跨模型）；“utility-preserving gap”概念已公开，原评价层新颖性进一步收窄 |
| N2 | **Close Enough is Nowhere Near: Fidelity-Consumability Decoupling in KV Caches**，arXiv:2610.22016，2026-10-15 | 八种 substitute-cache 方法均停在无信息 baseline；提出“更 faithful 不等于可消费”；改用 reader 保留自身 cache、把 sender cache 当额外 context | **对原“替换式 Mapper”路线最不利**：公开负面结果说明“提高映射保真”可能不是正确目标；支持 PIVOT，而非继续 P2/P3 |
| N3 | **To Cache or Not to Cache: Understanding and Mitigating Safety Incompatibility in Cross-Model KV Cache Reuse**，arXiv:2610.15721，2026-10-11 | 跨模型 KV 复用导致 safety 偏差；**value reuse 偏差显著大于 key reuse**；VReparo 用 per-layer/per-head affine 校正 | anticipate 机制层的 Value 侧发现，并增加 safety 评价维度；affine 基线已有人做到更强形式 |
| N4 | **ACCT: Asymmetric Cross-LLM Context Transfer**，arXiv:2610.42116，2026-10-30 | query-relevant token 选择 + 稀疏 KV，75% 压缩下匹配/超过 target 原生性能 | 强 baseline；很可能消除原“gap”，G1 若跑必须纳入 |
| N5 | **Swarm Telepathy: Prefill-Free KV-Cache Transfer Across Families**，arXiv:2610.15095，2026-10-10 | 跨家族 prefill-free 传输，17 benchmarks、12 LLM/6 families；比 text communication 平均高 40% accuracy | 强 cross-family baseline；原“跨模型迁移失败”叙事被进一步压缩 |
| N6 | **RaReCache: Bridging the Gap in Cross-Model KV Cache Reuse via Rank disagreement-based Selective Recomputation**，arXiv:2610.11358，2026-10-08 | 失败集中在信息密集 token；30% 重算保留 95–99% target accuracy | 强 baseline + 失败机制解释；原“affine 坍塌”更像已知失败模式，不是新发现 |
| N7 | **When Does Latent Communication Pay? A Causal Audit of Relayed KV Caches in Multi-Agent LLMs**，arXiv:2608.04893，2026-08-05 | mismatched/zero/random cache 对照 + 预注册 TOST；区分“cache 有用”与“配对信息传输” | **anticipate 信息归因/审计方法论**；原 evaluation 层的“联合报告/控制组”不再新颖 |
| N8 | **CacheFuse: Enabling Training-Free Latent Communication Between Language Models**，arXiv:2610.16165，2026-10-12 | 训练-free 线性插值融合 cache；4 benchmarks 提升最高 8.6pp | 极简强 baseline；降低“必须训练 Mapper”的必要性 |
| N9 | **Translating KV Caches Between Hybrid-Attention Language Models**，arXiv:2611.12062，2026-11-09；**BridgeKV**，arXiv:2611.11761，2026-11-09 | 覆盖 MLA、线性注意力、稀疏注意力、混合架构；BridgeKV 做 large-prefill/small-decode | 方法空间迅速扩张；原 MVP 等深对的边际贡献进一步降低 |
| N10 | **CacheLink / KV-Lingo / Heo et al.**（既有） | 功能 K/V 校正、蒸馏翻译、闭式 ridge | 仍是最直接的相关工作；N1–N9 进一步强化“方法层拥挤” |

> 结论：2026-10/11 的公开工作已经把 **utility vs fidelity**、**substitute-cache 负面结果**、**强 cross-model baseline**、**causal audit 方法论** 都覆盖到；原研究的“评价层 + 机制层 + 方法层”三贡献空间比 10 月顾问报告时更窄。

---

## 2. 对 PI 结论的逐条核定

| PI 结论 | 核定 | 理由 |
|---|---|---|
| 原研究按 v2.1–v2.6 **NO-GO** | **成立，且更强** | v2.4 明文永久放弃 P2/P3/P4；v2.1/v2.2 的 δ 基于 pre-fix 数据；N1/N2/N7 进一步 anticipate 原贡献 |
| 可继续“负面/边界论文 + 数据/外部效度”双轨 | **成立** | 数据审计翻转 + 配对反事实 E_CF 仍有独特案例价值；SQuAD 锚点/v2.6 数据是合法增量，但不恢复贡献 |
| 若真实 PI 坚持原研究，需撤销 decision 8、修订 v2.4、冻结 v2.7，并先过 G1 | **成立，但 G1 的优先级应下调** | N2/N4/N5 表明强 baseline 很可能消除 gap；G1 更像“最终确认/负面结果”，不是“救援机会” |
| G1 是最高信息量最小实验 | **部分成立，但从“推荐”降为“可选”** | 若目标是判断原 H1 是否还活着，G1 仍是最便宜；但文献已给出较强先验：大概率 null 或仅剩不可部署差距 |
| 数据/算法/实验可改善 | **数据可改善覆盖，算法/方法受治理与文献双重挤压** | 数据不能再造现象；强 Mapper 可能消除 gap；CF-RCT 需新版本且新颖性低 |

---

## 3. 修订后的 PI 裁决

### 3.1 原研究（H1/H2/H3）：NO-GO（科学 + 治理双重）

- **治理**：v2.4 永久放弃 P2/P3/P4，贡献(1)/(2) withdrawn、贡献(3) withheld；v2.6 再次声明不是 P3 重启。
- **科学**：N1 已公开“utility ≠ fidelity”；N2 已公开 substitute-cache 负面结果；N4/N5/N6/N8 提供强 baseline；N7 anticipate 审计方法。原 H1/H2/H3 即使勉强重启，也很难形成足够新颖的正向贡献。
- **δ 问题**：v2.2 的 δ=0.5 基于 pre-fix 数据；clean P3 必须重新选 δ，不能直接复用。

### 3.2 可继续的轨道

| 轨道 | 裁决 | 说明 |
|---|---|---|
| **A. 负面/边界论文** | **GO（主轨道）** | 核心是“数据泄漏/模板重合制造假阳性 + 修复后 affine 迁移失败边界”；必须新增引用 N1/N2/N3/N7，避免声称一般性发现 |
| **B. 数据/外部效度资产** | **CONDITIONAL GO** | SQuAD 锚点、v2.6 HellaSwag 种子 AI 数据、v2.5 校验；只能作额外探针，不是 real、不恢复贡献 |
| **C. G1 强基线确认** | **可选（低优先级）** | 若做：只 val、≥3 seed、ACCT/SwaT/CacheBridge/CacheFuse/kd_only；判据为 utility-preserving + gap 仍存在；但预期多为 null，不能据此恢复贡献 |
| **D. P2/P3/P4 重启** | **NO-GO** | 除非真实 PI 撤销 decision 8 + 修订 v2.4 + 冻结 v2.7；即便如此，N1–N9 已使正向新颖性很低 |

### 3.3 对“改善数据/算法/实验”的最终回答

- **数据**：可以扩簇、补锚点、做 v2.6 数据；但**不能**把“utility-preserving gap”造出来；real=0 仍是硬边界。
- **算法**：可以加 ACCT/SwaT/CacheBridge/CacheFuse 等强 baseline；但它们很可能**消除** gap，这会让原 H1 更彻底地失败，而不是救援。
- **实验**：可以做 G1 确认；不建议再做 P2/P3；封存 test 不应为了“救原研究”而提前碰。
- **最合理路径**：把资源投入负面/边界论文 + 数据审计资产；G1 仅作为一次低成本的“是否还有残余现象”的确认，不作为主线。

---

## 4. 结论

> **最新文献进一步支持 PI 的 NO-GO/双轨结论，而不是推翻它。**  
> 原研究（H1/H2/H3）在 v2.1–v2.6 下已无合法且高新颖性的继续路径；N1/N2/N7 已 anticipate 其核心概念与方法论，N4/N5/N6/N8 提供了可能消除 gap 的强基线。项目应继续“负面/边界论文 + 数据/外部效度资产”，G1 降为可选的最终确认；若真实 PI 仍坚持原研究，必须先完成制度修订（撤销 decision 8、修订 v2.4、冻结 v2.7），并接受高概率 null 的结果。
