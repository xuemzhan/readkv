# ReadKV 研究审查与论文审稿意见

**2026 年 11 月 23 日 · 建议大修后重审，暂缓投稿。**

审查以提交 `d0a8cca` 的 arXiv 版为主，并交叉核对长稿、历史与清洁运行、数据生成器、统计约定和投稿材料。判断针对当前稿件。按 TMLR 的两个标准，当前核心主张的证据充分性判为 **否**，对部分读者的潜在价值判为 **是**。稿件最有价值的结果是，一个可复核的 KV 迁移案例在基准重建后改变了科学判断。主要障碍是对翻转原因的归因超过了实验设计，部分关键指标的文字定义与执行口径不一致。对该判断的置信度为高。 [TMLR 录用标准](https://jmlr.org/tmlr/acceptance-criteria.html)

## 研究工作审查

论文研究 Qwen3-1.7B 到 Qwen3-0.6B 的严格零重预填充 KV 缓存迁移，用同一问题和两份事实不同的文档，测量迁移后候选答案对数优势变化相对于原生缓存的误差。研究保留了旧结果和撤回记录，使用 Self、Identity、错配、随机与零缓存对照，并同时披露模板族和逐对重采样区间。这些设计支持读者复核负面结果。历史与清洁版的三组验证集都能由相应代码和 seed 重建，每组 60 条逐对记录的样本哈希均能对齐。六个清洁 affine/KD 运行的 Joint $E_{\mathrm{CF}}$ 点估计、模板族区间与逐对敏感性区间均从原始日志复算到论文精度。 [主稿](../../papers/readkv_v2_arxiv/main.tex) · [归档数据](../data/gpu_experiments/v1/README.md) · [统计汇总](../bootstrap_summary.json)

| 主张 | 审查结论 |
| --- | --- |
| 历史版与重建版的 affine 结论翻转 | 支持此描述。历史 Joint dual 为 0.617–0.667，清洁版为 0.283–0.417。Joint $E_{\mathrm{CF}}$ 从 1.93–2.12 变为 6.90–8.54。对应验证集均为 60 对。 |
| 数据缺陷制造了假阳性，修复足以导致翻转 | 旧基准确有缺陷，撤回原结论合理。整批重建同时改变了多个环节，现有对照无法确定翻转由哪项变更造成，也无法量化各项影响。 |
| affine 迁移在清洁数据上失败 | 支持为单模型对、当前实现和合成验证集上的描述性失败。三组 Self–Joint dual 点差分别为 0.400、0.617、0.400。$E_{\mathrm{CF}}$ 点值在三组中均低于各自错配与零缓存对照。 |
| KD 保持效用但存在反事实误差 | 全切片 Joint dual 为 0.700–0.767，三组均未触发冻结诊断。仅计 F1–F4 时，seed 1 的 dual 点差达到 0.217。效用保持对统计范围敏感。$E_{\mathrm{CF}}$ 6.39–7.21 可作为描述性观察。 |
| Value 消费机制、CF-RCT 增益及泛化 | 机制仍应撤回。清洁机制实验、正式 CF-RCT 主终点、封存 test 评测及多模型对验证均缺席。SQuAD 仅提供额外的生成式 QA 观察。 |

## 主要审稿意见

### 1. 题名与摘要应撤下因果归因

正文称重建是受控比较，并称数据缺陷直接制造了假阳性。日志显示新旧运行都评估 `val`。新结构模板安排在 `probe/test`，主要结果没有评估这些模板；因此论文不能以 train/test 骨架重合的修复解释训练到验证集的估计变化。我用历史生成器复原了实际旧验证集，三组分别有 4、4、5 个必须翻转而候选文本相同的样本。按合并 A/B 两侧后取交集，旧 train/val 有 2、5、1 个相同的上下文字符串。这些发现直接关联主表样本，适合入稿。修订还需交代同时变化的校准和验证样本、实体词汇，以及统计区间口径。seed 0 的 Self $E_{\mathrm{CF}}$ 恒为 0 是定义所致，但 Self dual 从 0.683 升到 0.817，表明参考臂本身也变了。逐对 bootstrap 会影响区间，无法造成点估计变化。清洁版未重跑 P2，应表述为旧机制证据失效。

**必改**。把贡献表述为「审计发现旧基准存在缺陷；重建后的验证集上，原 affine 结论翻转」，并附实际 train/val 缺陷表与协议时间线。原测试计划与部分统计规则有事先记录，失败边界问题是在结果产出后重述。若保留「缺陷导致翻转」的主张，需要固定其余条件的逐项干预对照，或训练集版本 × 评估集版本的交叉对照。采用描述性主张时，已有记录足以完成这一项修订。 [数据修复记录](../data/data_fix_report.md) · [研究范围更新，第 7 节](../../docs/decisions/research_scope_update.md)

### 2. 修正 flip 分母、F5/F6 定义和候选评分说明

论文第 4 节声称 flip 排除 F5/F6，但 `summarize_cf` 仅按 `evaluable` 筛选，表中的值仍计入达到 Self 阈值的 F6。语料级 `398` 是 F1–F4 的全量计数。表中的每个运行有 60 对，其中 46 对归入 F1–F4，还要按 Self 阈值进一步筛选。按现有代码严格大于 0.1 的条件，清洁 affine 三组由 39/52、39/53、40/53 变成 34/45、35/46、34/46，KD 由 49/52、48/53、49/53 变成 42/45、41/46、42/46。F6 实际改了姓名，金标签依然在 A 与 B 间交换。F5 的两个候选文本相同、日志中六组 Self/Joint 的 F5 均为 7/7 dual、$E_{\mathrm{CF}}=0$，这项控制对任务效用没有区分力。另核对了公开 Qwen tokenizer：三个清洁 affine 运行各自的 F1–F4 验证样本中，46 对均至少有一个多 token 候选，且这些候选对首 token 互异。实现只比较候选首 token 的 logit。

**必改**。给出 F1–F4 的实际分子、分母、coverage 定义和分切片 dual。保留原冻结统计时，明确标记全切片算法及其限制。说明 F6 的构造及排除理由，并把 $g$、dual 和 flip 明确定义为候选首 token 的二选一代理指标。 [统计约定](../../configs/prereg/stats_convention_v2.3.yaml) · [指标代码](../../src/readkv/evaluate/counterfactual.py) · [生成器](../../src/readkv/data/build_cf_pairs.py) · [候选评分代码](../../src/readkv/models/gpu_backend.py) · [Qwen tokenizer](https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/tokenizer.json)

### 3. KD 更接近 Self，但保持效用的判断对口径敏感

全切片 KD 三组 Self–Joint dual 点差为 0.117、0.167、0.017。从配对逐对日志按模板族重采样 10,000 次所得探索性区间分别为 [−0.016, 0.254]、[0.016, 0.379]、[−0.048, 0.102]，前两组包含 0.2。仅看 F1–F4 时，三组点差为 0.152、0.217、0.022。`transfer_broken=false` 的含义是给定聚合下诊断条件未触发。类似地，$E_{\mathrm{CF}}$ 是非负绝对差，Self/Identity 为零由定义决定。均值的百分位区间排除零可描述误差大小，无法单独证明具有实践意义的效用—保真分离。还应说明错配控制对绝大多数目标复用验证集首条异样本，并列出逐 seed、逐方法的控制点值，以避免把摘要中的 seed 0 控制数字和全 seed 范围直接比较。

**必改**。将 KD 的结论限于「全切片上观察到较小的 dual 下降，误差仍为 6.39–7.21；仅在语义切片聚合时一组超过诊断阈值」。给出与 Self 的成对差及其区间。若要主张实质效用保持，须给出适用的容忍界值及非劣效证据。 [P1 评估与诊断规则](../../src/readkv/evaluate/cf_pipeline.py) · [归档日志](../data/gpu_experiments/v1/README.md)

### 4. 复现材料与基线预算需要更正

公开的 `cf_pairs.jsonl` 是 seed 0 导出。运行入口按各自 seed 在内存中分别生成数据。三组清洁 affine/KD 的 Joint 验证记录与同 seed 生成器均逐例匹配，但 seed 1/2 的完整验证样本记录均与 seed 0 导出不同。现有 S1 勘误称所有 clean run 读取同一文件且赋同一 SHA，和执行路径不符。Git 的 LF 版本为 `f910f1f1…a894a`；Windows 默认 CRLF 检出得到 `a99d0a25…37930`，归一到 LF 后相符。真实模型权重目前只记录 `snapshots/master`。此外，affine `fit` 按层、按头、按 K/V 闭式估计矩阵与截距。根据 28 层、8 个 KV 头、头维度 128 和实现推算，affine 拟合约 7,397,376 个系数，KD 记录为 7,340,032 个梯度优化参数。两者均使用校准数据，计算方式和预算不同。

**必改**。提供逐 run 的数据 seed、生成器修订、数据规格、规范化哈希与模型/tokenizer revision。论文应提供读者可访问的归档及复算命令。把 affine 写为「闭式校准，0 个梯度优化 epoch」，分别报告拟合系数、优化参数和计算预算。单独交代历史 CF-lite 烟测与正式 CF-RCT 评估的状态。 [溯源勘误](../data_hash_binding_erratum.json) · [affine 实现](../../src/readkv/mapper/representation.py) · [复现说明](../../docs/reproducibility.md) · [Qwen 配置](https://huggingface.co/Qwen/Qwen3-0.6B/raw/main/config.json)

### 5. SQuAD 锚点应按其实际抽样和评分解释

代码取文件顺序上的前 240 个可回答问题，日志仅覆盖两个文章标题。评分用第一个参考答案；官方脚本对所有参考答案取最大值。用已存预测和全部参考答案复核此子集，Self/affine Joint/KD Joint 的 F1 分别约为 0.2178/0.0082/0.0014，EM 仍为零。已有预测在该子集上显示两种迁移方案的 F1 都明显低于 Self，两项结果与合成域的成对候选读数不同。缺少对提示、输出格式、域偏移或基座能力的干预，EM 触底的原因未被识别。

**必改**。标明样本选择、文章覆盖、提示和解码、参考答案策略。按官方规则从已存预测重算子集分数，或将历史表明确标记为单参考子集。把「replicates the failure direction」收窄为该子集上的描述性 F1 下跌，并保留探索性判读。 [锚点实现](../../experiments/anchor_squad_gpu.py) · [冻结汇总](../anchor_eval_summary.json) · [官方评分脚本](https://github.com/rajpurkar/SQuAD-explorer/blob/master/evaluate-v2.0.py)

## 文献、编译与投递

- 现有文献已经包含部分模型对在线性 KV 迁移下明显退化，以及带错配、零和随机对照的缓存审计。稿件的学术价值应落在旧结果可追溯、同一问题的成对文档读数，以及结论对数据质量和评分口径的敏感性。抽查还发现 Contrast Sets 作者表错误、Heo 条目含多处名字缩写错误、BridgeKV 缺作者和完整题名。建议从论文主页导入元数据。 [Heo 等](https://arxiv.org/abs/2608.03893) · [缓存因果审计](https://arxiv.org/abs/2608.04893) · [Contrast Sets](https://aclanthology.org/2020.findings-emnlp.117/) · [BridgeKV](https://arxiv.org/abs/2611.11761)
- 原始 arXiv 源码第 792 行文本中的 `E_CF` 触发 `Missing $ inserted`，Tectonic 未生成 PDF。只在临时副本修复该字符后，TeX 与 BibTeX 可完成，但数据缺陷表、臂定义表、误差公式和前后对比表仍明显越界，最大约 386 pt。长稿生成 PDF，结果表仍有约 103 pt 的溢出。当前两份稿件均署名，且采用普通 article 类。TMLR 要求匿名稿及官方模板。建议重排表格、避免在一行重复三个 seed 的区间、用逐 seed 点图取代重复的示意框，并把内部签核和取消阶段移到补充材料。 [arXiv 源码](../../papers/readkv_v2_arxiv/main.tex) · [长稿源码](../../papers/readkv_v2_draft/main.tex) · [TMLR 作者指南](https://jmlr.org/tmlr/author-guide.html)
- 本机 Windows CPU 环境（Torch 2.14.0、Transformers 5.17.0）运行测试得到 52 通过、1 失败。失败发生在 Qwen3 缓存注入恒等性测试，报 `layer 0 has no K/V after prefill`。代码传入 `cache=`，本机 Qwen3 签名使用 `past_key_values`。归档 GPU 环境使用 Transformers 5.24.0，且归档 E0 通过。本机失败需要作为依赖兼容性问题核对，审查未重跑原始 GPU 评测。 [hook 实现](../../src/readkv/models/hooks.py) · [归档环境](../environment.json)

## 复审条件

以现有证据完成一版描述性的负面结果稿有可行路径。优先重写因果措辞，补实际 `val` 缺陷和切片统计，纠正逐 seed 溯源、基线预算与 SQuAD 指标，最后生成可读的匿名 TMLR PDF。核心复审问题是读者能否凭归档重现「何时和在哪一部分样本上，迁移判断发生变化」。在这个范围内，当前清洁 affine 的负面结果值得保留，现有日志可完成主要修订。审查仅读取模型运行产物、重算日志并在临时目录编译，原稿与冻结记录均保持原样。
