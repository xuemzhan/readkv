# v3.0 新研究最终签 off（2026-11-25）

> 裁决人：PI / 课题组长（本会话由真实 PI 授权 main agent 执行收口）。
> 依据：`configs/prereg/gpu_followup_v3.0.yaml`（FROZEN，SHA `d8c2321fc4ba6abeda80e6f581d3f7ef6c592c9173de757aad1a40120ae811e6`）、`docs/decisions/{gpu_v3_scope_ruling,v3_baseline_spec,v3_g1_release,v3_g2_release,v3_e2_argument_ruling,v3_e2_interface_ruling,v3_e2_rows_ruling,v3_g4_pi_rulings}.md`、`docs/audit/v3_statistical_interpretation.md`（科学家签署，G4-READY）、`reports/review/v3_g4_compliance_review.md`（CONDITIONAL PASS）、`reports/review/v3_g{1,2,3_batch1,3_batch2}_*.md`。
> 性质：**新研究的最终签 off**。不改任何冻结判据、不回写当前稿件、不代为投稿；所有数字仅转抄科学家已签署报告，不重算、不伪造。

---

## 1. 门控与验收

| 门 | 状态 | 证据 |
|---|---|---|
| G0 范围裁决 | ✅ | 真实 PI 授权 E1/E2/E5/E6；结果另立新研究；modelscope.cn 来源 |
| G1 冻结 + CPU 审计 | ✅ | `gpu_followup_v3.0.yaml` 先写后跑；E1 六变体/E2 test 锁/模型 SHA 钉扎/97→103 单测通过 |
| G2 技术 pilot | ✅ | 四条技术路径 PASS；E1 规范冲突已裁定；放行正式格 |
| G3 正式 GPU 格 | ✅ | **39 个权威格**：E5 3 + E6 3 + E2 6（单次 one-shot）+ E1 30；串行、全 provenance |
| G4 统计 + 独立审阅 | ✅ | 科学家签署（占位符 0）；reviewer CONDITIONAL PASS；R1–R4 已由 PI 裁定关闭 |

**G4 风险关闭**：R1（陈旧 `protocol_version` 字符串，非判据切换）、R2（非 git 工作区致 `consistency_check` 失败，改以 122 文件直接 SHA 核验）、R3（科学家首版占位未签 → 已用 staged 只读副本重算并签署）、R4（E2 技术量未落盘等诚实限制，接受、不补测、不重跑）。

## 2. 结果摘要（仅转抄科学家签署版）

| 包 | 预承诺分支裁定 | 关键数值（family 主 CI；pair 敏感性并列） |
|---|---|---|
| **E1** | `single_defect_associated` **不成立**；并列 `interaction_or_combination` + `seed_or_composition_sensitive` | Panel A dedup/entity/template 三 seed 与 legacy 数值完全相同（s0 5.3633 [2.9211,7.5882]）；差距集中在 `fully_repaired`（s2 8.4304 [5.0937,11.4264] vs legacy 6.4262 [3.7522,8.8599]，joint dual 反降）；Panel B entity `_r2` 因 `data_task_change=true` coverage .2333、E_CF 0.62–0.88 |
| **E2** | `held_out_consistent`（固定配置外推） | affine joint dual .28/.3667/.32、E_CF 8.5007/8.0445/8.3940；kd_only joint dual .7633/.5933/.6667、E_CF 7.0169/7.2834/7.3814；16 family → exploratory，no pooled |
| **E5** | `replicated_on_one_extra_pair`（**仅方向**） | Self dual .8167/.8667/.8333 vs Joint .15/.1833/.1667；E_CF 6.9854 [3.914,9.929] / 7.6323 [4.512,10.579] / 7.6615 [4.407,10.700]；`transfer_broken=true`、控制未被支配 |
| **E6** | 无结果分支；描述性预算匹配内部对照 | `v3-BM-MLP-KD` E_CF 8.2173/8.5934/9.4987，joint dual 更低，不得称增益；参数 7,340,032、960 步/seed、1,920 forward、训练 471.7–494.9 s、峰值 4608.6/4674.0 MiB 全披露；复现门 NOT PASSED |

`degenerate_only` = **NOT ESTIMABLE**（标签缺陷；归档缺逐 pair logits，CPU replay 不可执行，无 GPU 格）。E1/E2 的 L 双 CI 未重算（归档仅点估计；主终点成对 E_CF 双 CI 齐备）——均如实标注，未伪造。

## 3. 运行与失败入账

- 39 个 `reports/runs/v3_*` 目录：38 个有 `scores.jsonl`，1 个保留 ABORTED（`v3_E1_B_entity_disjoint_only_s0`，缺显式 input-change 授权）。
- 6 个 `_r2` 正式格带 `--allow-input-change-gpu-forward` 且 `data_task_change=true`；E2 one-shot：evaluator 进程 2 次（1 次评分前 REFUSED + 1 次权威），权威评分 pass = 1；两次 preflight 0 调用。
- E6 首个 smoke ABORTED 保留；所有失败/ABORTED run 均入账，不删不改。
- 全部 39 个权威 config `zero_re_prefill=true`；所有模型引用为 SHA 钉住链接（非裸 master 重解析）。

## 4. 不可变边界（再次确认）

当前 TMLR 稿件（`papers/readkv_v2_{draft,tmlr_anonymous,arxiv}/**`）只读且未改；v2.1–v2.9 冻结判据一字未回写；贡献(1)(2) 撤回、(3) withheld；P2/P3/P4 永久放弃；P4 对 E5 仍 NO-GO；E1 不称因果分解、E2 不称 sealed/独立 replicate/普遍泛化、E5 不称跨模型泛化、E6 不称 faithful baseline；不混入 SQuAD/ARC/HellaSwag/真实文档/AI 生成数据；agent 不代为投稿。

## 5. 结论

> **v3.0 新研究全部 agent 任务完成并签 off。** G0→G4 全部通过，39 个正式 GPU 格完成，统计由科学家双 CI 重算并绑定预承诺分支，独立审阅 CONDITIONAL PASS 且四项风险均经 PI 裁定关闭。所有结果仅属**另立的新研究**，不回写当前 TMLR 稿件、不触发其 P5 重新签 off、不改变投稿决策。后续若要把这些结果写入任何稿件，须另行立项、重新冻结措辞与判据并经完整审阅。

---

**签署：PI / 课题组长（v3.0 新研究最终签 off · 2026-11-25）**
