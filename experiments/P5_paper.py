"""P5 成稿：运行耗时/显存核算，统一图表与投稿文本骨架。

是否投稿取决于结果质量；若仅贡献(1)成立，应改写为边界/实证研究论文。
"""

from __future__ import annotations

import argparse
import json

from readkv.data.build_cf_pairs import build_cf_pairs, quality_report
from readkv.evaluate.diagnostics import mapper_cost
from readkv.models.loader import load_model_and_tokenizer  # noqa: F401  (GPU 端使用)
from readkv.cache.cache import estimate_bytes_per_token

from experiments._common_v2 import add_v2_args, build_v2_mock, new_ctx, require_gpu


FIGURES = {
    "图1": "两篇已有工作→第三篇科学问题的关系图",
    "图2": "严格零 Prefill 流程与 Self/Identity/Joint/Oracle 诊断分界",
    "图3": "反事实成对文档构造与正/负控制示例（含位置匹配）",
    "图4": "原生 vs 迁移响应差散点/分布（分色 K/V/Joint）",
    "图5": "层/Head 反事实误差热图与 Oracle 修复效果",
    "图6": "方法消融：KD/CF/机制约束对 E_CF 与任务准确率的影响",
    "图7": "非等深及跨任务泛化、成本—收益 Pareto",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_v2_args(parser, default_stage="P5")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "figures": list(FIGURES)}, indent=2, ensure_ascii=False))
        return
    require_gpu(args)

    backend, cfg = build_v2_mock(args)
    pairs = build_cf_pairs(sizes=cfg.sizes, seed=cfg.seed)
    ctx = new_ctx(args, "P5", {"kind": "paper_artifacts"})
    cost = mapper_cost({"n_layers": 28, "n_kv_heads": 8, "head_dim": 128},
                       bytes_per_token=estimate_bytes_per_token(
                           {"n_layers": 28, "n_kv_heads": 8, "head_dim": 128}))
    payload = {
        "figures": FIGURES,
        "tables": ["表1 数据切片与主结果", "表2 控制实验", "表3 统计显著性与训练成本"],
        "contribution_template": [
            "We identify a reproducible gap between standard transfer utility and counterfactual response fidelity in cross-model KV handoff.",
            "We localize the gap to receiver-side routing and consumption effects under controlled cache interventions.",
            "We present a mechanism-constrained mapper that reduces this gap against matched behavioral baselines without target-side re-prefill at inference.",
        ],
        "conditional_note": "仅当贡献(1)(2)(3)均被实验支持时保留全部措辞；否则改写为边界/实证研究论文",
        "cost_estimate": cost,
        "data_quality": quality_report(pairs),
        "note": "图表必须直接读取冻结结果文件生成；mock 数字不得进入论文",
    }
    ctx.write_metrics("paper_artifacts.json", payload)
    ctx.finalize()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
