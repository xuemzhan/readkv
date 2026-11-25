"""修正评测器（论文 1 第 3.4 节）。

两个已修复的历史缺陷：
  1. 不能在已推进 query 与 gold answer 的 cache 上再算 greedy EM；
  2. 不能把最后一个 query token 重新当作首个生成输入。
runner 必须用 fresh cache，首 token 取自 prefill logits。本模块只负责指标计算
与 validator 的一致性统计。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence

import numpy as np


_ARTICLES = {"a", "an", "the"}
_PUNCT = re.compile(r"[\W_]+", re.UNICODE)


def normalize_answer(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).lower()
    tokens = [t for t in _PUNCT.sub(" ", text).split() if t and t not in _ARTICLES]
    return " ".join(tokens)


def corrected_em(generated: str, gold: str) -> float:
    """normalize 后精确匹配；1.0 为正确，0.0 为错误。"""
    return float(normalize_answer(generated) == normalize_answer(gold))


def answer_probability(logits: np.ndarray) -> np.ndarray:
    """四选项 softmax 概率（letter 顺序由 runner 固定为 A/B/C/D）。"""
    arr = np.asarray(logits, dtype=float).reshape(-1)[:4]
    if arr.size != 4:
        raise ValueError("answer_probability needs exactly 4 logits")
    shift = arr - arr.max()
    exp = np.exp(shift)
    return exp / exp.sum()


def gold_letter_prob(logits: np.ndarray, letter_ids: Sequence[int]) -> float:
    """四个答案 letter logits 的 softmax，取 gold letter 对应概率。"""
    arr = np.asarray(logits, dtype=float).reshape(-1)[:4]
    if arr.size != 4 or len(letter_ids) != 4:
        raise ValueError("gold_letter_prob needs exactly 4 logits and 4 letter ids")
    return float(answer_probability(arr)[letter_ids[0]])  # runner 固定顺序 [A,B,C,D]


def first_token_top1(logits: np.ndarray, tokenizer: object | None = None) -> int:
    """首生成 token 取自 prefill logits 的 argmax。"""
    return int(np.argmax(np.asarray(logits)))


def teacher_forced_ll(logits: np.ndarray, target_ids: Sequence[int]) -> float:
    """teacher-forced 答案 token 对数概率和；明确不是 transfer 指标。"""
    arr = np.asarray(logits, dtype=float)
    if arr.ndim == 1:
        arr = arr[None, :]
    log_probs = arr - np.log(np.exp(arr - arr.max(axis=-1, keepdims=True)).sum(axis=-1, keepdims=True))
    return float(sum(log_probs[i, int(t)] for i, t in enumerate(target_ids)))


def validator_agreement(records_a: Sequence[Mapping], records_b: Sequence[Mapping]) -> dict[str, float]:
    """两条路径（注入 vs 全 prefill）的一致性，复现论文 1 图 2。"""
    if len(records_a) != len(records_b) or not records_a:
        raise ValueError("validator needs aligned non-empty record lists")
    em = np.mean([corrected_em(str(a["generated"]), str(b["generated"])) for a, b in zip(records_a, records_b)])
    top1 = np.mean([a["first_token"] == b["first_token"] for a, b in zip(records_a, records_b)])
    kls = []
    for a, b in zip(records_a, records_b):
        p, q = np.asarray(a["token_probs"], float), np.asarray(b["token_probs"], float)
        p, q = p / p.sum(), q / q.sum()
        kls.append(float(np.sum(p * np.log((p + 1e-12) / (q + 1e-12)))))
    return {"normalized_em_agreement": float(em), "top1_agreement": float(top1), "median_kl": float(np.median(kls))}


def summarize_em(rows: Sequence[Mapping], arm: str) -> dict[str, float]:
    values = [float(r["corrected_em"]) for r in rows if r.get("arm") == arm]
    return {"n": len(values), "mean": float(np.mean(values))} if values else {"n": 0, "mean": 0.0}
