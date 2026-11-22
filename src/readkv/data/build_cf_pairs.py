"""反事实文档对构造（V2.0 方案 §4）。

最小评测单元 ``u=(q, d_A, d_B, a, b, m)``：同一问题 q，两份仅在关键事实位点
不同的文档 d_A/d_B，互斥可验证答案 a/b，元数据 m。六类切片 F1—F6：

    F1 直接事实替换 / F2 推理链变化 / F3 关系方向·否定 / F4 干扰与指向 /
    F5 表层等价（非翻转负控）/ F6 长度·位置控制

关键约束：
  * 教师必须对 d_A、d_B **分别独立** Prefill，不得篡改缓存字节伪造另一文档；
  * 候选 A/B 在每对文档内一致，随机交换候选顺序以控制答案位置偏差；
  * F5 是非翻转负控制，不计入“必须翻转”的成功率分母；
  * 同一评测对两份缓存 token 长度尽量匹配，无法匹配须显式分层报告；
  * 按实体 / 原始来源 / 模板族做训练·评估隔离。

本模块只生成结构化 pair 表（对应方案附录 A schema），不做模型推理。
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SLICES = ("F1", "F2", "F3", "F4", "F5", "F6")
SEMANTIC_SLICES = ("F1", "F2", "F3", "F4")  # 必须翻转
NEGATIVE_CONTROL_SLICES = ("F5",)            # 不应翻转
CONDITION_SLICES = ("F6",)                   # 条件扰动

SPLITS = ("probe", "train", "val", "test", "real")

# 每个 split 使用的模板族变体；不同 split 的变体不重叠，保证训练/评估隔离
SPLIT_VARIANTS: dict[str, tuple[str, ...]] = {
    "probe": ("P",),
    "train": ("A", "B"),
    "val": ("C",),
    "test": ("D",),
    "real": ("R",),
}

# 建议规模（方案 §4.3；非功效保证）
DEFAULT_SIZES: dict[str, int] = {
    "probe": 40,
    "train": 120,
    "val": 60,
    "test": 300,
    "real": 0,
}

NAMES = ["张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十"]
CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
DATES = ["2021-03-15", "2022-07-20", "2023-11-05", "2024-01-12",
         "2020-09-30", "2025-06-18", "2019-12-25", "2026-02-08"]
NUMBERS = ["12", "34", "56", "78", "90", "23", "45", "67"]
PROJECTS = ["星河", "远航", "灯塔", "磐石", "青云", "赤兔", "黑马", "白鹭"]
ROLES = ["负责人", "技术负责人", "项目经理", "主导人", "联络人", "归档人"]


# ---------------------------------------------------------------------------
# 核心数据结构（方案附录 A）
# ---------------------------------------------------------------------------

@dataclass
class CFPair:
    """一条反事实文档对记录；字段与方案附录 A 对齐。"""

    pair_id: str
    split: str
    template_family: str
    source_doc_id: str
    context_A: str
    context_B: str
    query: str
    candidate_A: str
    candidate_B: str
    correct_A: str
    correct_B: str
    edited_span: str
    token_count_A: int
    token_count_B: int
    position_gap: int
    model_pair: str = ""
    mapper_id: str = ""
    model_revision: str = ""
    dtype: str = ""
    kernel: str = ""
    seed: int = 0

    # 额外字段（生成阶段元信息；不写入附录 A 主结果）
    slice_id: str = "F1"
    fact_type: str = "person"
    cluster: str = ""
    swap_candidates: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def must_flip(self) -> bool:
        """是否属于“必须翻转”集合；F5 不计入分母。"""
        return self.slice_id in SEMANTIC_SLICES

    @property
    def length_matched(self) -> bool:
        return self.token_count_A == self.token_count_B

    def as_record(self) -> dict[str, Any]:
        """转为附录 A 风格的扁平记录（供 scores.jsonl / 结果表使用）。"""
        record = asdict(self)
        record["must_flip"] = self.must_flip
        record["length_matched"] = self.length_matched
        record["token_count_A/B"] = f"{self.token_count_A}/{self.token_count_B}"
        record.pop("metadata", None)
        return record

    def to_json(self) -> str:
        return json.dumps(self.as_record(), ensure_ascii=False)

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "CFPair":
        data = dict(record)
        data.pop("must_flip", None)
        data.pop("length_matched", None)
        data.pop("token_count_A/B", None)
        # 只保留 CFPair 已声明的字段，忽略结果列
        allowed = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in allowed})


# ---------------------------------------------------------------------------
# 模板族与事实类型
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Template:
    family: str
    slice_id: str
    fact_type: str
    query_fmt: str
    context_fmt: str
    editor: str  # A 文档取 fact_a，B 文档取 fact_b
    variant: str = ""  # 用于训练/评估模板族隔离（见 build_cf_pairs）


TEMPLATES: tuple[Template, ...] = (
    # 注意：前 6 个模板覆盖全部 6 个切片，保证小规模 eval split 也含 F5/F6
    # F1 直接事实替换
    Template("T-F1-person", "F1", "person",
             "项目{p}的负责人是谁？",
             "项目{p}的{role}是{name}。该项目已于{date}完成评审。",
             "person"),
    # F2 推理链变化：中间别名/隶属关系变化，答案在另一个句段
    Template("T-F2-alias", "F2", "alias",
             "与{p}合作的团队负责人是谁？",
             "{p}由团队{team_a}支持，{team_a}的负责人是{name_a}。团队{team_b}负责审计。",
             "alias"),
    # F3 关系方向/否定
    Template("T-F3-direction", "F3", "direction",
             "谁向谁汇报？",
             "{name_a}向{name_b}汇报。项目{p}由{name_b}审批。",
             "direction"),
    # F4 干扰与指向
    Template("T-F4-distractor", "F4", "distractor",
             "项目{p}（编号{num}）当前负责人是谁？",
             "项目{p}早期由{name_a}跟进。编号{num}的项目现由{name_b}负责。另有{name_c}负责归档。",
             "distractor"),
    # F5 表层等价（非翻转）
    Template("T-F5-paraphrase", "F5", "surface",
             "项目{p}的负责人是谁？",
             "项目{p}的{role}是{name}。该项目已于{date}完成评审。",
             "same"),
    # F6 长度/位置控制
    Template("T-F6-position", "F6", "position",
             "项目{p}的负责人是谁？",
             "前置说明：项目{p}启动于{date}。负责人是{name}。补充说明见附件{num}。",
             "person"),
    # 附加模板（扩大族数，用于更大 split）
    Template("T-F1-city", "F1", "city",
             "项目{p}的落地城市是哪里？",
             "项目{p}的{role}是{name}，落地城市是{city}。项目预算为{num}万元。",
             "city"),
    Template("T-F3-negation", "F3", "negation",
             "项目{p}是否允许外部访问？",
             "项目{p}{policy}，由{name}负责。文档版本{num}。",
             "negation"),
)


# ---------------------------------------------------------------------------
# 构造工具
# ---------------------------------------------------------------------------

def _tokens(text: str) -> int:
    """确定性 token 长度代理（中文按字，空白分词）；用于长度匹配检查。"""
    return len([c for c in text if not c.isspace()])


def _fact_slots(rng: random.Random) -> dict[str, str]:
    return {
        "p": rng.choice(PROJECTS),
        "role": rng.choice(ROLES),
        "name": rng.choice(NAMES),
        "name_a": rng.choice(NAMES),
        "name_b": rng.choice(NAMES),
        "name_c": rng.choice(NAMES),
        "city": rng.choice(CITIES),
        "date": rng.choice(DATES),
        "num": rng.choice(NUMBERS),
        "team_a": f"组{chr(65 + rng.randint(0, 7))}",
        "team_b": f"组{chr(65 + rng.randint(8, 15))}",
        "policy": rng.choice(["允许", "禁止"]),
    }


def _distinct(primary: str, pool: Sequence[str], rng: random.Random) -> str:
    choices = [x for x in pool if x != primary]
    return rng.choice(choices) if choices else primary


def _build_one(template: Template, rng: random.Random, pair_id: str, split: str,
               model_pair: str, seed: int) -> CFPair:
    slots = _fact_slots(rng)
    s = dict(slots)

    if template.slice_id == "F1":
        if template.fact_type == "person":
            a = s["name"]; b = _distinct(a, NAMES, rng); s["name"] = a
            ctx_b = dict(s, name=b)
        elif template.fact_type == "city":
            a = s["city"]; b = _distinct(a, CITIES, rng); s["city"] = a
            ctx_b = dict(s, city=b)
        else:
            a = s["num"]; b = _distinct(a, NUMBERS, rng); s["num"] = a
            ctx_b = dict(s, num=b)
        context_A = template.context_fmt.format(**s)
        context_B = template.context_fmt.format(**ctx_b)
        query = template.query_fmt.format(**s)
        candidate_A, candidate_B = a, b
        edited = f"{template.fact_type}: {a} -> {b}"

    elif template.slice_id == "F2":
        # 中间别名变化：A 中由 team_a 的 name_a 负责，B 中改为 team_b 的 name_b
        context_A = template.context_fmt.format(**s)
        ctx_b = dict(s, team_a=s["team_b"], name_a=s["name_b"])
        context_B = template.context_fmt.format(**ctx_b)
        query = template.query_fmt.format(**s)
        candidate_A, candidate_B = s["name_a"], s["name_b"]
        edited = f"alias: {s['team_a']}/{s['name_a']} -> {s['team_b']}/{s['name_b']}"

    elif template.slice_id == "F3":
        if template.fact_type == "direction":
            context_A = template.context_fmt.format(**s)
            ctx_b = dict(s, name_a=s["name_b"], name_b=s["name_a"])
            context_B = template.context_fmt.format(**ctx_b)
            query = template.query_fmt.format(**s)
            # 问题“谁向谁汇报”答案随方向翻转：A=name_a 向 name_b，B=name_b 向 name_a
            candidate_A, candidate_B = s["name_a"], s["name_b"]
        else:  # negation
            a = s["policy"]; b = "禁止" if a == "允许" else "允许"
            context_A = template.context_fmt.format(**dict(s, policy=a))
            context_B = template.context_fmt.format(**dict(s, policy=b))
            query = template.query_fmt.format(**s)
            candidate_A, candidate_B = a, b
        edited = f"{template.fact_type}: flipped"

    elif template.slice_id == "F4":
        # A 中编号 num 的项目由 name_b 负责；B 中改为 name_a，干扰项保持
        context_A = template.context_fmt.format(**dict(s, name_b=s["name_a"]))
        context_B = template.context_fmt.format(**dict(s, name_a=s["name_b"]))
        query = template.query_fmt.format(**s)
        candidate_A, candidate_B = s["name_a"], s["name_b"]
        edited = f"distractor target: {candidate_A} -> {candidate_B}"

    elif template.slice_id == "F5":
        # 表层等价：同一事实的同义改写；两份文档答案一致（非翻转）
        context_A = template.context_fmt.format(**s)
        ctx_b = dict(s, role=_distinct(s["role"], ROLES, rng))
        context_B = template.context_fmt.format(**ctx_b)
        query = template.query_fmt.format(**s)
        candidate_A = candidate_B = s["name"]
        edited = f"surface: {s['role']} -> {ctx_b['role']} (same answer)"

    elif template.slice_id == "F6":
        # 长度/位置控制：编辑 token 长度匹配，但事实位置移动
        a = s["name"]; b = _distinct(a, NAMES, rng)
        context_A = template.context_fmt.format(**dict(s, name=a))
        context_B = template.context_fmt.format(**dict(s, name=b))
        query = template.query_fmt.format(**s)
        candidate_A, candidate_B = a, b
        edited = f"position: {a} -> {b}"

    else:  # pragma: no cover
        raise ValueError(f"unknown slice: {template.slice_id}")

    # 随机交换候选顺序（控制答案位置偏差）
    swap = rng.random() < 0.5
    if swap:
        candidate_A, candidate_B = candidate_B, candidate_A
        correct_A = "B" if template.slice_id != "F5" else "A/B"
        correct_B = "A" if template.slice_id != "F5" else "A/B"
    else:
        correct_A = "A"
        correct_B = "B" if template.slice_id != "F5" else "A/B"

    # F5 两份都“正确”（不应翻转）
    if template.slice_id == "F5":
        correct_A = correct_B = "A/B"

    cluster = f"{split}-{template.family}-{pair_id[-3:]}"
    return CFPair(
        pair_id=pair_id,
        split=split,
        template_family=template.family,
        source_doc_id=f"{pair_id}-doc",
        context_A=context_A,
        context_B=context_B,
        query=query,
        candidate_A=str(candidate_A),
        candidate_B=str(candidate_B),
        correct_A=str(correct_A),
        correct_B=str(correct_B),
        edited_span=edited,
        token_count_A=_tokens(context_A),
        token_count_B=_tokens(context_B),
        position_gap=abs(_tokens(context_A) - _tokens(context_B)),
        model_pair=model_pair,
        seed=seed,
        slice_id=template.slice_id,
        fact_type=template.fact_type,
        cluster=cluster,
        swap_candidates=swap,
        metadata={"template": template.family, "fact_type": template.fact_type},
    )


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def build_cf_pairs(
    *,
    sizes: Mapping[str, int] | None = None,
    seed: int = 0,
    model_pair: str = "qwen3-1.7b-to-0.6b",
    templates: Sequence[Template] | None = None,
) -> list[CFPair]:
    """按 split 规模生成反事实文档对。

    ``sizes`` 可覆盖默认规模；未列出的 split 使用 ``DEFAULT_SIZES``。
    ``real`` split 默认为 0（需要人工核验的真实文档另行注入）。
    """
    sizes = dict(DEFAULT_SIZES) | dict(sizes or {})
    base = list(templates or TEMPLATES)

    # 为每个基础模板派生各 split 的专属变体（仅 family 名不同），
    # 确保 train/eval 不共享模板族（方案 §4.4 / §3.4 隔离要求）。
    variants = SPLIT_VARIANTS if templates is None else {"all": ("",)}
    expanded: dict[str, list[Template]] = {s: [] for s in variants}
    for t in base:
        for split_key, vs in variants.items():
            for v in vs:
                expanded[split_key].append(
                    Template(t.family + (f"-{v}" if v else ""), t.slice_id, t.fact_type,
                             t.query_fmt, t.context_fmt, t.editor, v)
                )

    pairs: list[CFPair] = []
    for split in SPLITS:
        n = int(sizes.get(split, 0))
        if n <= 0:
            continue
        key = split if split in expanded else ("all" if "all" in expanded else split)
        pool = expanded.get(key, [])
        if not pool:
            continue
        rng = random.Random(f"{seed}-{split}")
        for i in range(n):
            template = pool[i % len(pool)]
            pid = f"{split}-{template.slice_id}-{i:04d}"
            pairs.append(_build_one(template, rng, pid, split, model_pair, seed))
    return pairs


def split_pairs(pairs: Sequence[CFPair], split: str) -> list[CFPair]:
    return [p for p in pairs if p.split == split]


def quality_report(pairs: Sequence[CFPair]) -> dict[str, Any]:
    """方案 §4.4 数据质量门禁的可执行摘要。"""
    total = len(pairs)
    by_slice: dict[str, int] = {}
    by_split: dict[str, int] = {}
    length_mismatch = 0
    f5_count = 0
    flip_denominator = 0
    for p in pairs:
        by_slice[p.slice_id] = by_slice.get(p.slice_id, 0) + 1
        by_split[p.split] = by_split.get(p.split, 0) + 1
        if not p.length_matched:
            length_mismatch += 1
        if p.slice_id in NEGATIVE_CONTROL_SLICES:
            f5_count += 1
        if p.must_flip:
            flip_denominator += 1
    # 按簇隔离检查（同一 template_family 不跨 train/test）
    train_templates = {p.template_family for p in pairs if p.split == "train"}
    test_templates = {p.template_family for p in pairs if p.split in ("test", "val")}
    overlap = sorted(train_templates & test_templates)
    return {
        "total": total,
        "by_slice": by_slice,
        "by_split": by_split,
        "length_mismatch": length_mismatch,
        "f5_negative_controls": f5_count,
        "flip_denominator": flip_denominator,
        "template_overlap_train_eval": overlap,
        "quality_gate": (
            "pass" if not overlap and total > 0 else "fail"
        ),
        "note": (
            "length_mismatch 需分层报告；F5 不计入必须翻转分母；"
            "template_overlap_train_eval 必须为空（否则违反训练/评估隔离）"
        ),
    }


def save_pairs(pairs: Iterable[CFPair], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(p.to_json() + "\n")
    return path


def load_pairs(path: Path | str) -> list[CFPair]:
    out: list[CFPair] = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(CFPair.from_record(json.loads(line)))
    return out


def stable_hash(pair: CFPair) -> str:
    """pair 内容指纹（用于缓存哈希无交叉检查）。"""
    payload = f"{pair.query}|{pair.context_A}|{pair.context_B}|{pair.candidate_A}|{pair.candidate_B}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
