"""真实基准加载器：HellaSwag/ARC 四选一与 SQuAD。

数据从本地 jsonl 读取，字段约定见 docstring；不在此处下载，避免污染可复现性。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FourChoiceItem:
    item_id: str
    context: str
    question: str
    choices: tuple[str, str, str, str]
    gold_letter: str   # A/B/C/D
    cluster: str = "default"


@dataclass(frozen=True)
class SquadItem:
    item_id: str
    context: str
    question: str
    answer: str
    cluster: str = "default"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_four_choice(name: str, split: str, data_root: Path | str) -> list[FourChoiceItem]:
    """读取 <data_root>/<name>/<split>.jsonl；
    每行：{item_id, context, question, choices:[4], gold_letter}。"""
    path = Path(data_root) / name / f"{split}.jsonl"
    items = []
    for row in _read_jsonl(path):
        choices = tuple(row["choices"])
        if len(choices) != 4:
            raise ValueError(f"{path}: expected 4 choices")
        items.append(
            FourChoiceItem(
                str(row["item_id"]), str(row.get("context", "")), str(row["question"]),
                choices, str(row["gold_letter"]), str(row.get("cluster", "default"))
            )
        )
    return items


def load_squad(split: str, data_root: Path | str) -> list[SquadItem]:
    path = Path(data_root) / "squad" / f"{split}.jsonl"
    return [
        SquadItem(str(r["item_id"]), str(r["context"]), str(r["question"]), str(r["answer"]), str(r.get("cluster", "default")))
        for r in _read_jsonl(path)
    ]
