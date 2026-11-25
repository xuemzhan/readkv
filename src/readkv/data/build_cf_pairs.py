"""反事实文档对构造（V2.1 修正版，修复 M1/M2/M3）。

最小评测单元 ``u=(q, d_A, d_B, a, b, m)``：同一问题 q，两份仅在关键事实位点
不同的文档 d_A/d_B，互斥可验证答案 a/b，元数据 m。六类切片 F1—F6：

    F1 直接事实替换 / F2 推理链变化 / F3 关系方向·否定 / F4 干扰与指向 /
    F5 表层等价（非翻转负控）/ F6 长度·位置控制

V2.1 相对 V2.0 的修正（依据 docs/decisions/data_readiness_ruling.md）：
  * M1：F1—F4/F6 的候选强制相异（``_distinct``），并对 must_flip 样本断言
    ``candidate_A != candidate_B`` 且 ``correct_A != correct_B`` 且两文档不同；
    F5 候选相同是设计使然且 must_flip=false，保留。
  * M2：姓名/项目/城市/日期/编号/角色/团队/策略实体池按 split 不相交分配；
    生成期做全局签名去重，确保跨 split 无逐字相同的 context/query/edited_span。
  * M3：新增 16 个**句式结构不同**的未见模板（U-*），专供 test/probe；
    train/val 使用 S-* 模板。train 与 test 的模板骨架不重合。
  * M7′：flip 分母口径固定为排除 [F5, F6]（stats_convention_v2.3.yaml），
    由 ``quality_report`` 如实重算并写入 manifest。

本模块只生成结构化 pair 表，不做模型推理。所有生成完全由 ``seed`` 决定。
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SLICES = ("F1", "F2", "F3", "F4", "F5", "F6")
SEMANTIC_SLICES = ("F1", "F2", "F3", "F4")  # 必须翻转
NEGATIVE_CONTROL_SLICES = ("F5",)            # 不应翻转
CONDITION_SLICES = ("F6",)                   # 条件扰动（长度/位置），语义非翻转
FLIP_DENOMINATOR_EXCLUDES = ("F5", "F6")     # stats_convention_v2.3.yaml 口径

SPLITS = ("probe", "train", "val", "test", "real")

# 每个 split 使用的模板族变体后缀；模板*结构*分组见 _templates_for_split
SPLIT_VARIANTS: dict[str, tuple[str, ...]] = {
    "probe": ("P",),
    "train": ("A", "B"),
    "val": ("C",),
    "test": ("D",),
    "real": ("R",),
}

DEFAULT_SIZES: dict[str, int] = {
    "probe": 40,
    "train": 120,
    "val": 60,
    "test": 300,
    "real": 0,
}

# ---- M2：按 split 不相交的实体池（每个 split 一段，5 splits） -----------------
NAME_POOL: tuple[str, ...] = (
    "张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十",
    "冯一", "陈二", "褚三", "卫四", "蒋五", "沈六", "韩七", "杨八",
    "朱一", "秦二", "尤三", "许四", "何五", "吕六", "施七", "张八",
    "孔一", "曹二", "严三", "华四", "金五", "魏六", "陶七", "姜八",
    "戚一", "谢二", "邹三", "喻四", "柏五", "水六", "窦七", "章八",
)
PROJECT_POOL: tuple[str, ...] = (
    "星河", "远航", "灯塔", "磐石", "青云", "赤兔", "黑马", "白鹭",
    "长风", "破晓", "惊鸿", "流云", "奔雷", "烈焰", "苍穹", "碧海",
    "孤帆", "飞雪", "秋水", "寒星", "落日", "春山", "夜雨", "晨曦",
    "银河", "极光",  "晨星", "暮云", "松涛", "竹韵", "梅香", "兰亭",
    "赤壁", "黄山", "泰山", "华山", "嵩山", "衡山", "恒山", "雁荡",
)
CITY_POOL: tuple[str, ...] = (
    "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京",
    "西安", "重庆", "天津", "苏州", "郑州", "长沙", "青岛", "沈阳",
    "大连", "厦门", "宁波", "济南", "合肥", "福州", "昆明", "南昌",
    "贵阳", "太原", "石家庄", "哈尔滨", "长春", "呼和浩特", "乌鲁木齐", "兰州",
    "银川", "西宁", "海口", "三亚", "珠海", "无锡", "温州", "洛阳",
)
# 每个 split 的 6 个角色长度互不相同（2—7 字），确保 F5 同义改写时
# token 长度必然不等 → length_mismatch 被显式标注而非静默吞掉（既有测试 auto4）。
ROLE_POOL: tuple[str, ...] = (
    # probe
    "主管", "负责人", "项目经理", "技术负责人", "高级项目经理", "项目首席负责人",
    # train
    "总管", "统筹人", "执行经理", "高级协调员", "质量监督管理", "项目运营负责人",
    # val
    "主事", "召集人", "记录专员", "文档管理员", "项目联络专员", "首席运营负责人",
    # test
    "牵头", "策划人", "评估专员", "培训管理员", "采购管理专员", "项目审计负责人",
    # real
    "主责", "设计师", "分析专员", "研究协调专员", "测试管理员", "项目发布负责人",
)
POLICY_POOL: tuple[str, ...] = (
    "准予", "不准",        # probe
    "允许", "禁止",        # train
    "许可", "谢绝",        # val
    "放行", "拒绝",        # test
    "开通", "关闭",        # real
)
TEAM_PREFIX: dict[str, str] = {
    "probe": "甲", "train": "乙", "val": "丙", "test": "丁", "real": "戊",
}
DATE_POOL: tuple[str, ...] = tuple(
    f"{2010 + (i // 8)}-{1 + (i % 8):02d}-{5 + (i % 7):02d}" for i in range(40)
)
NUMBER_POOL: tuple[str, ...] = tuple(str(10 + 2 * i) for i in range(40))


def entity_bundle(split: str) -> dict[str, list[str]]:
    """返回该 split 专属的、与其它 split 完全不相交的实体池。"""
    if split not in SPLITS:
        raise ValueError(f"unknown split: {split}")
    idx = SPLITS.index(split)
    prefix = TEAM_PREFIX[split]
    return {
        "names": list(NAME_POOL[idx * 8:(idx + 1) * 8]),
        "projects": list(PROJECT_POOL[idx * 8:(idx + 1) * 8]),
        "cities": list(CITY_POOL[idx * 8:(idx + 1) * 8]),
        "dates": list(DATE_POOL[idx * 8:(idx + 1) * 8]),
        "numbers": list(NUMBER_POOL[idx * 8:(idx + 1) * 8]),
        "roles": list(ROLE_POOL[idx * 6:(idx + 1) * 6]),
        "policies": list(POLICY_POOL[idx * 2:(idx + 1) * 2]),
        # 团队带 split 专属汉字前缀，保证跨 split 不重合
        "teams": [f"组{prefix}{c}" for c in "ABCDEFGHIJKLMNOP"],
    }


ALL_ENTITY_VALUES: tuple[str, ...] = tuple(
    sorted(
        {v for sp in SPLITS for vals in entity_bundle(sp).values() for v in vals},
        key=len, reverse=True,
    )
)

# ---------------------------------------------------------------------------
# 核心数据结构（方案附录 A）
# ---------------------------------------------------------------------------


@dataclass
class CFPair:
    """一条反事实文档对记录；字段与方案附录 A 对齐（schema 保持不变）。"""

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

    slice_id: str = "F1"
    fact_type: str = "person"
    cluster: str = ""
    swap_candidates: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def must_flip(self) -> bool:
        """是否属于“必须翻转”集合；按 v2.3 口径排除 F5 与 F6。"""
        return self.slice_id not in FLIP_DENOMINATOR_EXCLUDES

    @property
    def length_matched(self) -> bool:
        return self.token_count_A == self.token_count_B

    def as_record(self) -> dict[str, Any]:
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
        for k in ("must_flip", "length_matched", "token_count_A/B"):
            data.pop(k, None)
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
    editor: str
    variant: str = ""


# 已见模板（train/val）——8 个结构
SEEN_TEMPLATES: tuple[Template, ...] = (
    Template("S-F1-person", "F1", "person",
             "项目{p}的负责人是谁？",
             "项目{p}的{role}是{name}。该项目已于{date}完成评审。", "person"),
    Template("S-F2-alias", "F2", "alias",
             "与{p}合作的团队负责人是谁？",
             "{p}由团队{team_a}支持，{team_a}的负责人是{name_a}。团队{team_b}负责审计。", "alias"),
    Template("S-F3-direction", "F3", "direction",
             "{p}相关的汇报关系是怎样的？",
             "{name_a}向{name_b}汇报。项目{p}由{name_b}审批。", "direction"),
    Template("S-F4-distractor", "F4", "distractor",
             "项目{p}（编号{num}）当前负责人是谁？",
             "项目{p}早期由{name_a}跟进。编号{num}的项目现由{name_b}负责。另有{name_c}负责归档。", "distractor"),
    Template("S-F5-paraphrase", "F5", "surface",
             "项目{p}此次调整后由谁接任职务？",
             "通报：{p}项目近日完成调整，{role_a}一职由{name}接任，相关文件编号为{num}。", "same"),
    Template("S-F6-position", "F6", "position",
             "项目{p}的负责人是谁？",
             "前置说明：项目{p}启动于{date}。负责人是{name}。补充说明见附件{num}。", "person"),
    Template("S-F1-city", "F1", "city",
             "项目{p}的落地城市是哪里？",
             "项目{p}的{role}是{name}，落地城市是{city}。项目预算为{num}万元。", "city"),
    Template("S-F3-negation", "F3", "negation",
             "项目{p}是否允许外部访问？",
             "项目{p}{policy}，由{name}负责。文档版本{num}。", "negation"),
)

# 未见模板（test/probe）——16 个**句式结构不同**的新模板（M3）
UNSEEN_TEMPLATES: tuple[Template, ...] = (
    # F1 直接事实替换（3）
    Template("U-F1-register", "F1", "person",
             "负责{p}项目的是哪位？",
             "在{p}项目组的登记表中，牵头人写作{name}，登记日期为{date}。", "person"),
    Template("U-F1-minutes", "F1", "person",
             "{p}的牵头人姓名是？",
             "会议纪要（{date}）记载：{p}由{name}牵头，预算{num}万元。", "person"),
    Template("U-F1-annex", "F1", "person",
             "谁被列为{p}的负责人？",
             "附件{num}：{p}——负责人栏填写为{name}，复核于{date}。", "person"),
    # F2 推理链变化（3）
    Template("U-F2-dossier", "F2", "alias",
             "支持{p}的小组由谁带队？",
             "档案显示：{team_a}为{p}提供支持；该组由{name_a}带队，另有{team_b}承担评审。", "alias"),
    Template("U-F2-filing", "F2", "alias",
             "{p}项目中支援组的负责人是？",
             "在{num}号备案里，{p}的支援方是{team_a}，其代表为{name_a}；{team_b}负责监督。", "alias"),
    Template("U-F2-log", "F2", "alias",
             "为{p}提供支撑的团队领导者是谁？",
             "记录（{date}）：{team_a}向{p}提供支撑，团队领导者为{name_a}；{team_b}参与审计。", "alias"),
    # F3 关系方向/否定（3）
    Template("U-F3-request", "F3", "direction",
             "在{p}的记录中谁向谁请示？",
             "{name_a}向{name_b}请示，{p}事项由{name_b}裁定。", "direction"),
    Template("U-F3-flow", "F3", "direction",
             "{p}的请示关系如何表述？",
             "依据{date}的流程，{name_a}需向{name_b}请示，{p}由其批准。", "direction"),
    Template("U-F3-token", "F3", "negation",
             "{p}对外口令是否处于开启状态？",
             "系统配置（版本{num}）：{p}的对外口令为{policy}，维护人为{name}。", "negation"),
    # F4 干扰与指向（3）
    Template("U-F4-change", "F4", "distractor",
             "编号{num}对应事项现在的责任人是？",
             "早年{p}由{name_a}负责；直至编号{num}的变更下达，该事项转由{name_b}承接，{name_c}仅负责抄送。", "distractor"),
    Template("U-F4-entry", "F4", "distractor",
             "在{p}的近期记录里谁负责编号{num}？",
             "历史档案：{p}最初由{name_a}跟进。最新条目编号{num}，责任人为{name_b}。{name_c}负责留档。", "distractor"),
    Template("U-F4-beforeafter", "F4", "distractor",
             "编号{num}的新负责人是谁？",
             "变更前：{p}由{name_a}负责；变更后（编号{num}）：由{name_b}负责。{name_c}为见证人。", "distractor"),
    # F5 表层等价（2，非翻转）
    Template("U-F5-brief", "F5", "surface",
             "在{p}的记录中由谁承担统筹？",
             "简报：{p}项目于{date}调整，{role_a}事务由{name}承担，编号{num}。", "same"),
    Template("U-F5-notice", "F5", "surface",
             "谁在{p}的通报里被指派职务？",
             "通告第{num}期：{p}的{role_a}由{name}出任，日期{date}。", "same"),
    # F6 长度/位置控制（2）
    Template("U-F6-background", "F6", "position",
             "项目{p}当前的负责人是谁？",
             "背景：{p}立项于{date}。当前负责人：{name}。后续安排见编号{num}。", "person"),
    Template("U-F6-index", "F6", "position",
             "项目{p}由谁负责？",
             "索引{num}｜{p}：启动时间{date}；负责人{name}；备注见附件。", "person"),
)

# API 兼容：TEMPLATES 为全部基础模板（24 个结构）
TEMPLATES: tuple[Template, ...] = SEEN_TEMPLATES + UNSEEN_TEMPLATES


def _templates_for_split(split: str) -> list[Template]:
    """按 split  selecting 已见/未见模板结构并加变体后缀。"""
    if split in ("train", "val"):
        base = SEEN_TEMPLATES
    elif split in ("probe", "test"):
        base = UNSEEN_TEMPLATES
    else:  # real：默认无数据
        base = ()
    out: list[Template] = []
    for t in base:
        for v in SPLIT_VARIANTS.get(split, ()):
            out.append(Template(t.family + f"-{v}", t.slice_id, t.fact_type,
                                t.query_fmt, t.context_fmt, t.editor, v))
    return out


# ---------------------------------------------------------------------------
# 构造工具
# ---------------------------------------------------------------------------


def _tokens(text: str) -> int:
    """确定性 token 长度代理（中文按字，空白分词）。"""
    return len([c for c in text if not c.isspace()])


def _fact_slots(entities: Mapping[str, list[str]], rng: random.Random) -> dict[str, str]:
    return {
        "p": rng.choice(entities["projects"]),
        "role": rng.choice(entities["roles"]),
        "name": rng.choice(entities["names"]),
        "name_a": rng.choice(entities["names"]),
        "name_b": rng.choice(entities["names"]),
        "name_c": rng.choice(entities["names"]),
        "city": rng.choice(entities["cities"]),
        "date": rng.choice(entities["dates"]),
        "num": rng.choice(entities["numbers"]),
        "team_a": rng.choice(entities["teams"][:8]),
        "team_b": rng.choice(entities["teams"][8:]),
        "policy": rng.choice(entities["policies"]),
    }


def _distinct(primary: str, pool: Sequence[str], rng: random.Random) -> str:
    choices = [x for x in pool if x != primary]
    return rng.choice(choices) if choices else primary


def _build_one(template: Template, entities: Mapping[str, list[str]], rng: random.Random,
               pair_id: str, split: str, model_pair: str, seed: int) -> CFPair:
    slots = _fact_slots(entities, rng)
    s = dict(slots)
    sl = template.slice_id

    if sl == "F1":
        a = s["name"]
        b = _distinct(a, entities["names"], rng)
        s["name"] = a
        context_A = template.context_fmt.format(**s)
        context_B = template.context_fmt.format(**dict(s, name=b))
        candidate_A, candidate_B = a, b
        edited = f"{template.fact_type}: {a} -> {b} ({s['p']})"

    elif sl == "F2":
        a = s["name_a"]
        b = _distinct(a, entities["names"], rng)
        ta = s["team_a"]
        tb = _distinct(ta, entities["teams"][:8], rng)
        s["name_a"], s["team_a"] = a, ta
        context_A = template.context_fmt.format(**s)
        context_B = template.context_fmt.format(**dict(s, team_a=tb, name_a=b))
        candidate_A, candidate_B = a, b
        edited = f"alias: {ta}/{a} -> {tb}/{b}"

    elif sl == "F3":
        if template.fact_type == "direction":
            a = s["name_a"]
            b = _distinct(a, entities["names"], rng)
            s["name_a"] = a
            context_A = template.context_fmt.format(**s)
            context_B = template.context_fmt.format(**dict(s, name_a=b, name_b=a))
            candidate_A, candidate_B = a, b
            edited = f"direction: {a} -> {b} ({s['p']})"
        else:  # negation
            pa, pb = entities["policies"][0], entities["policies"][1]
            a = s["policy"]
            b = pb if a == pa else pa
            s["policy"] = a
            context_A = template.context_fmt.format(**s)
            context_B = template.context_fmt.format(**dict(s, policy=b))
            candidate_A, candidate_B = a, b
            edited = f"negation: {a} -> {b} ({s['p']})"
        query = template.query_fmt.format(**s)

    elif sl == "F4":
        a = s["name_a"]
        b = _distinct(a, entities["names"], rng)
        c = _distinct(a, entities["names"], rng)
        if c == b:
            c = _distinct(b, entities["names"], rng)
        s["name_c"] = c
        context_A = template.context_fmt.format(**dict(s, name_a=a, name_b=a))
        context_B = template.context_fmt.format(**dict(s, name_a=b, name_b=b))
        candidate_A, candidate_B = a, b
        edited = f"distractor target: {a} -> {b} ({s['p']}, {s['num']})"

    elif sl == "F5":
        ra = s["role"]
        rb = _distinct(ra, entities["roles"], rng)
        s["role_a"] = ra
        context_A = template.context_fmt.format(**s)
        context_B = template.context_fmt.format(**dict(s, role_a=rb))
        candidate_A = candidate_B = s["name"]
        edited = f"surface: {ra} -> {rb} (same answer, {s['p']})"

    elif sl == "F6":
        a = s["name"]
        b = _distinct(a, entities["names"], rng)
        s["name"] = a
        context_A = template.context_fmt.format(**s)
        context_B = template.context_fmt.format(**dict(s, name=b))
        candidate_A, candidate_B = a, b
        edited = f"position: {a} -> {b} ({s['p']})"
    else:  # pragma: no cover
        raise ValueError(f"unknown slice: {sl}")

    if sl != "F3":
        query = template.query_fmt.format(**s)

    # 随机交换候选顺序（控制答案位置偏差）
    swap = rng.random() < 0.5
    if swap:
        candidate_A, candidate_B = candidate_B, candidate_A
        correct_A, correct_B = ("B", "A") if sl != "F5" else ("A/B", "A/B")
    else:
        correct_A, correct_B = ("A", "B") if sl != "F5" else ("A/B", "A/B")

    # ---- M1 断言：must_flip 样本必须真的可翻转 -----------------------------
    if sl == "F5":
        assert candidate_A == candidate_B and correct_A == correct_B == "A/B", pair_id
    else:
        assert candidate_A != candidate_B, f"degenerate candidates: {pair_id}"
        assert correct_A != correct_B, f"answer position not different: {pair_id}"
        assert context_A != context_B, f"identical documents: {pair_id}"

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
        metadata={"template": template.family, "fact_type": template.fact_type,
                  "template_group": "unseen" if template.family.startswith("U-") else "seen"},
    )


def build_cf_pairs(
    *,
    sizes: Mapping[str, int] | None = None,
    seed: int = 0,
    model_pair: str = "qwen3-1.7b-to-0.6b",
    templates: Sequence[Template] | None = None,
) -> list[CFPair]:
    """按 split 规模生成反事实文档对（确定性）。

    ``sizes`` 可覆盖默认规模；未列出的 split 使用 ``DEFAULT_SIZES``。
    ``templates`` 若提供则作为所有 split 的共享基础模板（旧 API 兼容，
    会禁用 M2/M3 的分组隔离，仅用于本地测试；主导出路径不使用）。
    """
    sizes = dict(DEFAULT_SIZES) | dict(sizes or {})
    pairs: list[CFPair] = []
    seen_signatures: set[tuple[str, str, str, str]] = set()

    for split in SPLITS:
        n = int(sizes.get(split, 0))
        if n <= 0:
            continue
        pool = ([Template(t.family, t.slice_id, t.fact_type, t.query_fmt,
                          t.context_fmt, t.editor) for t in templates]
                if templates is not None else _templates_for_split(split))
        if not pool:
            continue
        entities = entity_bundle(split)
        rng = random.Random(f"{seed}-{split}")
        for i in range(n):
            template = pool[i % len(pool)]
            pid = f"{split}-{template.slice_id}-{i:04d}"
            # 确定性去重重试：签名全局唯一，跨 split 因实体池不相交而天然唯一
            for attempt in range(80):
                pair = _build_one(template, entities, rng, pid, split, model_pair, seed)
                sig = (pair.context_A, pair.context_B, pair.query, pair.edited_span)
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    break
            else:  # pragma: no cover
                raise AssertionError(f"cannot find unique signature for {pid}")
            pairs.append(pair)
    return pairs


def split_pairs(pairs: Sequence[CFPair], split: str) -> list[CFPair]:
    return [p for p in pairs if p.split == split]


# ---------------------------------------------------------------------------
# 质量门禁与隔离校验
# ---------------------------------------------------------------------------


def skeleton(text: str) -> str:
    """把实体值替换为占位符后的句式骨架（用于 train/test 模板结构隔离检查）。"""
    s = text
    for value in ALL_ENTITY_VALUES:
        s = s.replace(value, "<E>")
    s = re.sub(r"\d{4}-\d{2}-\d{2}", "<DATE>", s)
    s = re.sub(r"\d+", "<NUM>", s)
    return s


def _cross_split_overlaps(pairs: Sequence[CFPair], fields: Sequence[str]) -> dict[str, int]:
    by_split: dict[str, list[CFPair]] = {}
    for p in pairs:
        by_split.setdefault(p.split, []).append(p)
    result: dict[str, int] = {}
    for f in fields:
        sets = {sp: {str(getattr(p, f)) for p in ps} for sp, ps in by_split.items()}
        keys = list(sets)
        total = 0
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                total += len(sets[keys[i]] & sets[keys[j]])
        result[f] = total
    return result


def quality_report(pairs: Sequence[CFPair]) -> dict[str, Any]:
    """方案 §4.4 数据质量门禁的可执行摘要（V2.1 强化版）。"""
    total = len(pairs)
    by_slice: dict[str, int] = {}
    by_split: dict[str, int] = {}
    length_mismatch = 0
    length_by_slice: dict[str, int] = {}
    length_by_split: dict[str, int] = {}
    f5_count = 0
    flip_denominator = 0
    degenerate = 0
    for p in pairs:
        by_slice[p.slice_id] = by_slice.get(p.slice_id, 0) + 1
        by_split[p.split] = by_split.get(p.split, 0) + 1
        if not p.length_matched:
            length_mismatch += 1
            length_by_slice[p.slice_id] = length_by_slice.get(p.slice_id, 0) + 1
            length_by_split[p.split] = length_by_split.get(p.split, 0) + 1
        if p.slice_id in NEGATIVE_CONTROL_SLICES:
            f5_count += 1
        if p.must_flip:
            flip_denominator += 1
        # 退化对复核（应为 0）
        if p.must_flip and (p.candidate_A == p.candidate_B
                            or p.context_A == p.context_B
                            or p.correct_A == p.correct_B):
            degenerate += 1

    train_templates = {p.template_family for p in pairs if p.split == "train"}
    eval_templates = {p.template_family for p in pairs if p.split in ("test", "val")}
    overlap = sorted(train_templates & eval_templates)

    # 模板骨架 train∩test 必须为空（M3）
    sk_train = {skeleton(p.context_A) for p in pairs if p.split == "train"}
    sk_test = {skeleton(p.context_A) for p in pairs if p.split == "test"}
    sk_overlap = sorted(sk_train & sk_test)
    sk_query_train = {skeleton(p.query) for p in pairs if p.split == "train"}
    sk_query_test = {skeleton(p.query) for p in pairs if p.split == "test"}
    sk_query_overlap = sorted(sk_query_train & sk_query_test)

    # 跨 split 逐字重叠（M2）
    xs = _cross_split_overlaps(
        pairs, ("context_A", "context_B", "query", "edited_span", "source_doc_id", "cluster"))

    # 实体池不相交（M2）
    pools = {sp: entity_bundle(sp) for sp in SPLITS}
    entity_overlap: dict[str, int] = {}
    for kind in pools["probe"]:
        sets = {sp: set(pools[sp][kind]) for sp in SPLITS}
        n = 0
        for i, a in enumerate(SPLITS):
            for b in SPLITS[i + 1:]:
                n += len(sets[a] & sets[b])
        entity_overlap[kind] = n

    unseen_families = sorted({p.template_family for p in pairs
                              if p.split in ("test", "probe") and p.template_family.startswith("U-")})
    train_families = sorted(train_templates)
    all_structures = sorted({t.family for t in TEMPLATES})

    gate = (
        total > 0
        and not overlap
        and not sk_overlap
        and not sk_query_overlap
        and degenerate == 0
        and all(v == 0 for v in xs.values())
        and all(v == 0 for v in entity_overlap.values())
    )
    return {
        "total": total,
        "by_slice": by_slice,
        "by_split": by_split,
        "length_mismatch": length_mismatch,
        "length_mismatch_by_slice": length_by_slice,
        "length_mismatch_by_split": length_by_split,
        "f5_negative_controls": f5_count,
        "flip_denominator": flip_denominator,
        "flip_denominator_excludes": list(FLIP_DENOMINATOR_EXCLUDES),
        "degenerate_must_flip_pairs": degenerate,
        "cross_split_overlap": xs,
        "entity_pool_overlap": entity_overlap,
        "template_overlap_train_eval": overlap,
        "template_skeleton_overlap_train_test": sk_overlap,
        "query_skeleton_overlap_train_test": sk_query_overlap,
        "template_family_count_by_split": {sp: len({p.template_family for p in pairs if p.split == sp})
                                           for sp in by_split},
        "total_template_families": len({p.template_family for p in pairs}),
        "structural_template_count": len(all_structures),
        "unseen_template_subset": {
            "splits": ["probe", "test"],
            "family_count": len(unseen_families),
            "structural_template_count": len(UNSEEN_TEMPLATES),
            "family_names": unseen_families,
        },
        "seen_template_families": train_families,
        "quality_gate": "pass" if gate else "fail",
        "note": (
            "v2.1 修正版：退化对=0；跨 split 逐字重叠=0；实体池不相交；"
            "train/test 模板骨架不重合；flip 分母排除 F5+F6（stats_convention_v2.3.yaml）；"
            "length_mismatch 分层报告。"
        ),
    }


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


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
