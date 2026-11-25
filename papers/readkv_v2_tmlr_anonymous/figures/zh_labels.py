"""Chinese labels for the six figures.

The geometry lives in the six `gen_fig*.py` scripts and is shared by both
languages. This module only rewrites the strings a reader sees: every Text
artist, tick label and legend entry passes through `translate`, so switching
language cannot move a box, a marker or an axis.

Anything not in the table is a number, a unit symbol or a LaTeX maths fragment
and is left untouched.
"""
from __future__ import annotations

EN2ZH = {
    # ---- figure 1: pipeline and design grid -------------------------------
    "Joint arm transports the sender's keys and values.  "
    "Self arm substitutes the receiver's own cache of the same document.":
        "Joint 臂传输发送端的键与值；Self 臂改用接收端自己对同一文档的缓存。",
    "document\n$d_A$ / $d_B$": "文档\n$d_A$ / $d_B$",
    "sender\nQwen3-1.7B": "发送端\nQwen3-1.7B",
    "affine ridge map\nper layer, K and V\n$\\lambda=10^{-3}$":
        "仿射岭回归映射\n逐层逐头，K 与 V\n$\\lambda=10^{-3}$",
    "receiver\nQwen3-0.6B\n(frozen)": "接收端\nQwen3-0.6B\n（权重冻结）",
    "candidate score\n$s(c;C,q)$": "候选打分\n$s(c;C,q)$",
    "document": "文档",
    "keys / values": "键 / 值",
    "transported\ncache": "迁移后的\n缓存",
    "query $q$ + candidate prefix\n(first token, or teacher-forced)":
        "查询 $q$ + 候选前缀\n（首 token，或教师强制）",
    "positions read\noff the cache": "位置取自\n注入的缓存",
    "Self arm": "Self 臂",
    "seed 0 / 1 / 2": "种子 0 / 1 / 2",
    "original": "原始",
    "rebuilt": "重建",
    "validation corpus": "验证语料",
    "calibration corpus": "校准语料",
    "$L$ in points, one per seed": "每格三颗种子，$L$ 以百分点计",

    # ---- figure 2: corpus audit ------------------------------------------
    "pairs": "对数",
    "strings": "条数",
    "original corpus": "原始语料",
    "rebuilt corpus": "重建语料",
    "seed 0": "种子 0",
    "seed 1": "种子 1",
    "seed 2": "种子 2",

    # ---- figure 3: factorial result --------------------------------------
    "$L$ = Self $-$ Joint dual correctness (points)":
        "$L$ = 原生减迁移的双侧正确率（百分点）",
    "dual correctness (\\%)": "双侧正确率（\\%）",
    "Self level": "原生水平",
    "Joint level": "迁移水平",

    # ---- figure 4: scoring sensitivity -----------------------------------
    "First token": "首 token",
    "Full sequence": "整串对数概率",
    "Length-normalised": "长度归一",
    "$L$ (points)": "$L$（百分点）",
    "$L_{\\mathrm{A11}}-L_{\\mathrm{A00}}$ (points)":
        "$L_{\\mathrm{A11}}-L_{\\mathrm{A00}}$（百分点）",

    # ---- figure 5: counterfactual error ----------------------------------
    "$E_{\\mathrm{CF}}$ (first token, nats)": "$E_{\\mathrm{CF}}$（首 token，nat）",
    "Joint": "Joint 映射",
    "Mismatched": "错配缓存",
    "Zero": "零缓存",
    "Randomised": "随机缓存",
    "sign agreement\nseed 0:  34/45\nseed 1:  35/46\nseed 2:  34/46":
        "符号一致\n种子 0： 34/45\n种子 1： 35/46\n种子 2： 34/46",
    "sign flip": "符号翻转",

    # ---- figure 6: slices and mappers ------------------------------------
    "semantic slices": "语义切片",
    "controls": "对照切片",
    "Affine": "仿射映射",
    "Distillation": "蒸馏基线",
}

# Rows and readouts are built from f-strings, so their combinations are expanded.
for _cell in ("A00", "A01", "A10", "A11"):
    for _seed in range(3):
        EN2ZH[f"{_cell} $\\cdot$ s{_seed}"] = f"{_cell}·种子{_seed}"
for _seed in range(3):
    for _short, _zh in (("first", "首 token"), ("full", "整串"), ("length-norm", "长度归一")):
        EN2ZH[f"{_short}  s{_seed}"] = f"{_zh}·种{_seed}"

CJK_FAMILIES = ["Microsoft YaHei", "SimHei", "Source Han Sans SC", "Noto Sans CJK SC"]


def translate(value):
    """Map one drawn string to Chinese; numbers and maths pass through."""
    if not isinstance(value, str):
        return value
    return EN2ZH.get(value, value)


def install() -> None:
    """Route every string matplotlib draws through `translate`."""
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.text import Text

    original_set_text = Text.set_text

    def set_text(self, value):
        return original_set_text(self, translate(value))

    Text.set_text = set_text

    for name in ("set_xticks", "set_yticks"):
        original = getattr(Axes, name)

        def make(original):
            def wrapper(self, ticks, labels=None, *args, **kwargs):
                if isinstance(labels, (list, tuple)):
                    labels = [translate(str(value)) for value in labels]
                return original(self, ticks, labels, *args, **kwargs)
            return wrapper

        setattr(Axes, name, make(original))

    for cls in (Axes, Figure):
        original = cls.legend

        def make(original):
            def wrapper(self, *args, **kwargs):
                if len(args) >= 2 and isinstance(args[1], (list, tuple)):
                    args = (args[0], [translate(str(value)) for value in args[1]]) + args[2:]
                return original(self, *args, **kwargs)
            return wrapper

        cls.legend = make(original)
