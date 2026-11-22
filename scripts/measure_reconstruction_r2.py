"""从已落盘的缓存重算 held-out R²（论文 2 表 4；不能从答案分数反推）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from readkv.cache.cache import CacheStore
from readkv.evaluate.diagnostics import r2_score
from readkv.mapper.representation import AffineMapper


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--calib-teacher", required=True)
    parser.add_argument("--calib-student", required=True)
    parser.add_argument("--heldout-teacher", required=True)
    parser.add_argument("--heldout-student", required=True)
    parser.add_argument("--lam", type=float, default=1e-3)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    store = CacheStore(args.cache_root)
    cal_t, cal_s = store.load(args.calib_teacher), store.load(args.calib_student)
    held_t, held_s = store.load(args.heldout_teacher), store.load(args.heldout_student)
    mapper = AffineMapper(lam=args.lam, channel="both").fit(cal_t, cal_s)
    mapped = mapper.transform(held_t)

    r2: dict[str, float] = {}
    k_vals, v_vals = [], []
    for layer in held_s.layers:
        mk, mv = mapped.layer(layer)
        sk, sv = held_s.layer(layer)
        k_vals.append(r2_score(mk, sk))
        v_vals.append(r2_score(mv, sv))
    r2["K"] = float(np.mean(k_vals))
    r2["V"] = float(np.mean(v_vals))
    out = Path(args.output) if args.output else Path("reports/reconstruction_r2.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r2, indent=2), encoding="utf-8")
    print(json.dumps(r2, indent=2))


if __name__ == "__main__":
    main()
