"""阶段 3：带对比负样本的行为目标 mapper 与 adapter 对照（mock 后端）。

mock 中“学生 forward + CE”由 MockBackend.logits_from_mapped 提供；
GPU 机器上应把它换成冻结学生的真实前向，并保留同样的对比负样本与审计门。
"""

from __future__ import annotations

import argparse
import copy
import json

import numpy as np
import torch
from torch import nn

from readkv.config import load_config
from readkv.evaluate.pipeline import fit_mapper, make_items, run_pipeline
from readkv.mapper.behavioral import AffineMapperModule, BehavioralMapper, contrastive_loss
from readkv.runtime import RunContext

from experiments._common import add_backend_args, build_mock, clone_pipeline, require_gpu_backend


def train_behavioral(backend, cal, *, epochs: int = 20, lr: float = 1e-3, margin: float = 0.1):
    init = fit_mapper(backend, cal, "consumer").state_dict()
    module = AffineMapperModule(init)
    optimizer = torch.optim.Adam(module.parameters(), lr=lr)

    def score_fn(doc):
        gold = backend.gold_letter(doc)

        def fn(mapped):
            logits = backend.logits_from_mapped(mapped, gold, doc)
            target = torch.tensor([gold], dtype=torch.long)
            return nn.functional.cross_entropy(logits.reshape(1, -1), target)

        return fn

    module.train()
    for _ in range(epochs):
        for i, doc in enumerate(cal):
            wrong = cal[(i + 1) % len(cal)]
            optimizer.zero_grad()
            right_loss = score_fn(doc)(module.map_cache(backend.teacher_cache(doc)))
            wrong_loss = score_fn(wrong)(module.map_cache(backend.teacher_cache(wrong))).detach()
            loss = contrastive_loss(right_loss, wrong_loss, margin)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
            optimizer.step()
    module.eval()
    mapper = BehavioralMapper()
    mapper.module = module
    return mapper


def train_readout_adapter(backend, cal, *, rank: int = 8, epochs: int = 20, lr: float = 1e-3):
    """mock adapter：对每层的 readout 做低秩修正，训练于 teacher-state 分布。"""
    adapted = copy.deepcopy(backend)
    for key, base in adapted.w["read"].items():
        layer, head = key
        base_t = torch.as_tensor(base, dtype=torch.float32)
        a = nn.Parameter(torch.randn(base.shape[0], rank) * 0.01)
        b = nn.Parameter(torch.zeros(rank, base.shape[1]))
        opt = torch.optim.Adam([a, b], lr=lr)
        for _ in range(epochs):
            for doc in cal:
                v = torch.as_tensor(adapted.teacher_cache(doc).values[layer][head], dtype=torch.float32)
                gold = adapted.gold_letter(doc)
                logits = v.mean(axis=0) @ (base_t + a @ b)
                loss = nn.functional.cross_entropy(logits.reshape(1, -1), torch.tensor([gold]))
                opt.zero_grad()
                loss.backward()
                opt.step()
        adapted.w["read"][key] = (base_t + a.detach() @ b.detach()).numpy()
    return adapted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_args(parser, default_stage="stage3")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        cfg = load_config("stage3_behavioral")
        print(json.dumps({"status": "dry-run-ok", "controls": cfg["controls"]}, indent=2))
        return
    require_gpu_backend(args)

    backend, base_pipeline = build_mock(args)
    items = make_items(backend, base_pipeline.n_docs, base_pipeline.seed)
    cal = items[: base_pipeline.n_calibration]

    closed = fit_mapper(backend, cal, "consumer")
    behavioral = train_behavioral(backend, cal)
    adapted_backend = train_readout_adapter(backend, cal)

    results = {}
    configurations = {
        "closed_form": (backend, closed),
        "behavioral": (backend, behavioral),
        "adapter": (adapted_backend, fit_mapper(adapted_backend, cal, "affine")),
    }
    for name, (be, mapper) in configurations.items():
        pipeline = clone_pipeline(base_pipeline, value_mapper="affine", key_mapper="affine")
        ctx = RunContext(f"{args.run_id}_{name}", {"stage": 3, "condition": name, "backend": args.backend})
        results[name] = run_pipeline(ctx, be, pipeline, value_mapper_obj=mapper)

    summary = {
        "stage": 3,
        "backend": args.backend,
        "joint_em": {name: r["arms"]["joint"]["corrected_em"]["mean"] for name, r in results.items()},
        "v_only_em": {name: r["arms"]["v_only"]["corrected_em"]["mean"] for name, r in results.items()},
        "self_em": {name: r["arms"]["self"]["corrected_em"]["mean"] for name, r in results.items()},
        "note": "mock 结果仅用于训练/对照接线验证，不是科学结论",
    }
    ctx = RunContext(f"{args.run_id}_summary", {"stage": 3})
    ctx.write_metrics("summary.json", summary)
    ctx.finalize()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
