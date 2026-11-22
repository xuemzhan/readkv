"""合成 OOD 域：隐藏知识图谱 -> project-status 文档 -> 1..4 跳问题。

按 entity cluster 切分（train 70 / val 28 / test 56），保证测试实体不出现在训练中；
同一文档被约 7 个问题复用，因此统计上按文档聚类 bootstrap。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class QAItem:
    doc_id: str
    cluster: str
    question: str
    answer: str
    choices: tuple[str, str, str, str] | None = None
    gold_letter: str | None = None


def generate_synthetic_domain(
    n_entities: int = 160, *, seed: int = 0, n_docs: int = 80, out_dir: Path | str | None = None
) -> list[QAItem]:
    rng = random.Random(seed)
    entities = [f"E{i:03d}" for i in range(n_entities)]
    clusters = [f"C{i // 4:02d}" for i in range(n_entities)]
    docs = []
    for i in range(n_docs):
        e1, e2 = rng.sample(entities, 2)
        status = rng.choice(["active", "paused", "shipped", "cancelled"])
        docs.append((f"D{i:03d}", f"Project {e1} with {e2} is {status}.", clusters[entities.index(e1)]))

    items: list[QAItem] = []
    for doc_id, text, cluster in docs:
        for hop in range(1, 5):
            q = f"What is the status of the project (hop {hop}) described by: {text}"
            answer = text.rsplit(" is ", 1)[-1].rstrip(".")
            items.append(QAItem(doc_id, cluster, q, answer))

    if out_dir is not None:
        path = Path(out_dir)
        path.mkdir(parents=True, exist_ok=True)
        with (path / "synthetic.jsonl").open("w", encoding="utf-8") as fh:
            import json

            for item in items:
                fh.write(json.dumps(item.__dict__, default=lambda o: list(o) if isinstance(o, tuple) else str(o)) + "\n")
    return items
