# 对第三轮复审（B0）结论与修改的独立核查

**2026-11-24。结论：复审的技术诊断基本成立，主结论可以采信；但它的结果表混用了两套同分规则，其中首 token 一行与由它派生的一行数值是错的，因此「需要据此改表」的建议不成立——稿件早已采用被推荐的规则。多数「待修」在本地工作区已被修改实现，两处仍未处理（代码层面的 Self E_CF 与预注册强度的公开说明）。**

被审对象：[第三轮复审](./independent_research_and_manuscript_review_sequence_b0_2026-11-24.md)（审计对象 commit `ec0c02b`，与本地 HEAD 一致），以及工作区中未提交的修改（TMLR 稿、README、封面信）。

核查方法：全部在本机 CPU 上用归档记录复算，不用 GPU、不重跑模型。

1. `python reproduce.py --repo .`（在临时目录运行，避免覆盖稿件目录）——完整走一遍归档校验与重算；
2. 从 `evaluation.json` 的逐对分数独立实现两套同分规则（tie→A / tie→B，均接受「任一候选」标签）；
3. 从 `data/audit_2x2/` 原始语料重算缺陷计数；
4. `pytest -q` 复跑测试；用 Tectonic 编译稿件的两个版本（HEAD 版与工作区版）。

---

## 1. 逐条判定

| 复审结论 | 判定 | 独立证据 |
| --- | --- | --- |
| 6 格 12 个输入哈希、24 个文件哈希、720 条分数行可验证 | **成立** | `reproduce.py --repo .` 全链通过，输出 `Verified 720/720 historical decisions`，重生成的 `results.tex` 与稿件内文件 SHA256 完全相同（`60366C0B…AD7979`） |
| 2,880 条分支记录、5,340 次 forward | **成立** | 同上，`results.json → audit` 即为该数值，`reproduce.py` 断言失败会抛错 |
| 720 对臂级首 token margin 与旧 2×2 最大差 1.43×10⁻⁶ | **成立，且精确复现** | 我复算得到同一极值 **1.43e-06**，落在同一记录 `A11_0/val-F1-0032/joint` |
| 420 个单 token 分支的整串分数与首 token 相同 | **成立** | 扫描 6 格全部候选分项，0 处不等 |
| tie→A + 接受「任一候选」可回放 720/720 旧标签 | **成立** | 我实测 tie→A 为 **720 一致 / 0 不一致**；tie→B 为 714/6 |
| 6 条差异来自 F2/F3 的确切同分 | **成立** | 两套规则之间恰好 **6 个语义标签翻转、0 个对照切片标签翻转** |
| 84 条 F5 差异来自「A/B」识别问题 | **成立** | F5 金标签为 `('A/B','A/B')`；2×2 归档该切片双侧正确率为 **1.0**，序列评分存档为 **0.0** |
| A11 每个 seed 7 对不等长；等长子集整串 L 为 48.7/43.6/56.4 | **成立** | 我的独立复算：7/7/7 对，39 对子集给出 **48.7 / 43.6 / 56.4** |
| 首 token 一行与「整串相对首 token」一行（§1.1 表） | **不成立** | 见 §2：该两行用未 harmonize 的 tie→B 计算，与账本不符 |
| `postprocess()` 把同一 E_CF 写进 Self 与 Joint 行 | **成立（代码层面）** | 代码为 `for row in (base, cur): row["E_CF"][r] = ecf`；原始运行里 self 行 E_CF 与 joint 行相同（首对均为 12.296875） |
| 「A11 seed 0 的 Self 和 Joint 都被报告为 6.900」 | **不成立（表格误读）** | 稿件该表两列是 **Joint (family)** 与 **Joint (pair)** 两种重采样单位，不是 Self/Joint 两臂；稿件从未报告 Self 的 E_CF（`reproduce.py` 中 `self_ecf` 恒为 0） |
| HEAD 版匿名稿编译失败（`\ii`、`sec:metrics`、article+geometry） | **成立（针对 HEAD）** | `git show ec0c02b:…/main.tex` 为 755 行、`article`+`geometry`，第 670 行 `\ii`、第 73 行 `sec:metrics`；工作区版本已换成 TMLR 源，编译 **10 页、0 warning、0 overfull** |
| README 把模板切换留到 camera-ready | **成立（针对 HEAD）** | HEAD 的 README 第 13 行仍写「改用 `\usepackage{tmlr}` 并恢复作者信息」；工作区 README 已改为随包提供 TMLR 样式 |
| 摘要 8.38/8.58 需标为 seed 0 示例 | **已过时** | 现稿摘要写「ranges from 6.90 to 8.54」，对应表内三个 seed 的族区间点估计；全文无 8.38/8.58 |
| 封面信「most contrast intervals」应按 3/6 改写 | **已过时** | 现封面信无此表述，改为「三组方向一致、一个 seed 幅度显著变化」 |
| 附录族数宜写 8+8 | **部分已实现** | 正文「eight families per version, with six in the semantic scoring subset」；附录表注已写「independently resample eight clusters per version」 |
| 「primary CI 汇总表把族等权区间用于同六行」 | **不成立（现稿）** | 现稿两张表分别给出 sample-weighted 与 family-equal 两套点估计与区间，数值互不相同（如 A01−A00 seed 0：25.0 vs 23.2），标签一致 |
| 预注册强度只可写「B0 重跑前已版本化」 | **成立，且现稿已如此** | 现稿仅写「plan was checked into Git before the reproducible scoring rerun」；`v2.8` 配置的唯一提交是 B0 提交 `35e78e0`（2026-11-24 00:16 UTC，即 08:16 北京时间），该提交晚于旧 A11 seed 0 归档的 07:50 |
| 本机测试 72 通过、2 失败（缓存捕获 layer 0 无 K/V） | **成立，精确复现** | `pytest -q`：74 收集、**72 通过、2 失败**，失败用例同为 `test_hooks.py::test_capture_inject_identity_matches_full_prefill` 与 `test_sequence_scoring.py::test_score_candidate_sequence_cpu_tiny`，报错同为 `layer 0 has no K/V after prefill` |
| 360 对查询/候选拼接边界无差异 | **无法独立验证** | 需原 tokenizer；结构上与 6 run × 60 对一致，未重算 |

## 2. 唯一实质错误：§1.1 表混用了两套同分规则

复审自己也主张「以旧规则（同分取 A）重算」，但它的首 token 一行用的是新规则（同分取 B），而整串各行用的是旧规则，于是派生行变成跨规则的差：

| 统计量（百分点） | 复审值 | 账本 / 稿件 | 差异来源 |
| --- | ---: | ---: | --- |
| A11 L，首 token，seed 0 | 43.48 | **45.65** | A11 seed 0 有 1 对同分，tie→B 少记 1 对 |
| A11−A00，首 token，seed 0 | 43.48 | **45.65** | 同上 |
| A11−A00，首 token，seed 1 | 74.74 | **72.36** | A00 seed 1 有 1 对同分，tie→B 记为 −9.52 而非 −7.14 |
| 整串相对首 token，对 A11−A00 | +4.35 / −24.12 / +8.70 | **+2.17 / −21.74 / +8.70** | 用 tie→B 的首 token 减 tie→A 的整串 |
| A11 L，整串 / 长度归一 | 47.83 / 43.48 / 52.17；50.00 / 50.00 / 63.04 | 完全一致 | — |
| A11−A00，整串 / 长度归一 | 47.83 / 50.62 / 47.30；50.00 / 57.14 / 58.17 | 完全一致 | — |

复审内部也自相矛盾：它同时写「seed 1 的 A11 L 减少 21.7」与「该版本差减少 24.1」。在旧规则下 A00 的整串−首 token 变化恒为 0（三个 seed 点估计都是 0.0），所以版本差的变化只能与 A11 自身的变化相等，即 −21.7。

**为什么后果有限**：稿件已经采用被推荐的口径。`reproduce.py` 用 `g >= 0` 取 A 并接受「任一候选」，`main.tex` 明写「historical first-candidate tie rule … verified all 720 first-token dual labels」，且 `reproduce.py --repo .` 端到端重算出的 `results.tex` 与稿件逐字节一致。因此复审要求「更新表与历史回放声明」并不需要执行；需要改的只是它自己的表。

## 3. 已实现与仍未处理的修改

工作区（未提交）相对 HEAD 的改动，逐项对应复审要求：

| 复审要求 | 状态 |
| --- | --- |
| 改用官方 TMLR 模板并生成可编译匿名 PDF | **已完成**（`tmlr.sty` + `tmlr.bst` 随包，10 页 0 warning） |
| 主文同列 Self / Joint / L | **已完成**（Table 2 为 Native / transferred 两列） |
| 明示「方向一致、幅度敏感」 | **已完成**（摘要与 §4.2 各一处） |
| 不主张「第二分支无条件未触发」 | **已完成**（只写版本化时点） |
| 摘要控制数字改为跨 seed 范围 | **已完成**（6.90–8.54） |
| 封面信去掉「most contrast intervals」 | **已完成** |
| 附录 8+8 族说明 | **已完成**（正文＋表注） |
| 统计出口把 Self 的 E_CF 归零或移入独立字段 | **未完成**：`experiments/sequence_scoring_gpu.py::postprocess` 仍对 `(base, cur)` 双写；稿件侧由 `reproduce.py` 的 `self_ecf = 0.0` 兜住，所以不影响已发表数字，但原始 `scores.jsonl` 里 self 行带的是 joint 的误差 |
| 公开说明预注册只能限定为「重跑前已版本化」 | **部分完成**：正文已如此，但复现说明（README／附录数据声明）未提该限制 |

## 4. 本次唯一一处稿件修改

复审的拆分（84 来自「任一候选」识别，6 来自同分）比稿件原句更准确：F5 的 84 条差异与同分规则无关——F5 金标签是 `A/B`，2×2 归档按「任一候选」记 1，序列评分器按字符串前缀判定记 0。原句把 90 条差异统一归因于「同分取第二个候选」，属因果误述。已改为：

> Before harmonization, 84 F5 labels differed because the archived scorer could not credit either candidate, and six semantic labels differed because it broke exact ties towards the second candidate.

改动范围仅此一句；重编译后 10 页、0 warning、0 overfull，6 张图全部嵌入，图表数值未受影响（`verify_figures.py` 仍是 0 mismatch）。

## 5. 对「是否正确与合理」的总结

- **技术诊断：可靠。** 哈希／分支／forward 计数、margin 极差、两套同分规则的回放差、测试失败的用例名与报错，我都能逐项复现到相同数值。这类「可复现的定量指控」是这份复审最有价值的部分。
- **结果表：不可直接引用。** 首 token 行与派生行是跨规则混合，误差 2.2–2.4 个百分点；其余各行精确。
- **修改建议：方向合理，处置偏保守。** 它把「稿件需要按新规则重算」写成待修项，而稿件早已如此；但它对模板、编译、预注册强度、Self 误差字段的判断在 HEAD 上都是真问题，工作区已按它的要求改掉了其中大部分。
- **主结论站得住。** 「对角两格方向一致、seed 1 幅度对评分方式敏感、证据仅覆盖 A00/A11」与账本一致；「不需要追加 GPU」的裁剪也合理，因为唯一会推翻结论的情形是把主张扩张到整个 2×2 交互。
- **两条仍然敞开的实质问题**（不属于本次修改范围，记在此处）：`postprocess()` 的 Self E_CF 双写未修；本机 `hooks.py` 缓存捕获在 layer 0 取不到 K/V，两条失败测试说明当前环境下的前向接口回归没有通过，只能靠归档记录复核。

## 6. 复核方式（可重跑）

```
python reproduce.py --repo . --directory <empty dir>   # 归档校验 + 重算，应输出 Verified 720/720
python -m pytest -q                                    # 应为 72 通过 / 2 失败（layer 0 缓存捕获）
cd figures && python verify_figures.py                 # 图中数字对表，应为 0 mismatch
```

本文所有复算脚本为一次性使用，未写入仓库；结论中的每个数字都可用上表第三列的命令或其等价实现重得。
