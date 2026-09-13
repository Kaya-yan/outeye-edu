"""
白盒分析指标术语表（任务F1）：指标 key → 通俗名称 / 一句话解释 / 数值分档解读 / 教学含义。

后端统一出口：/analysis/whitebox 响应带 metric_glossary 字段，
interpretation 已按本文实际数值实例化（如「本文 1.4% 属日常叙事类」）。
前端 TermTooltip 优先展示后端条目，响应缺失时回退前端内置字典。
"""

from typing import Any, Callable, Dict, Optional, Tuple


class MetricSpec:
    """单个指标的术语条目。bands 为升序阈值表：取第一个 value < threshold 的档。"""

    def __init__(
        self,
        name: str,
        definition: str,
        teaching: str,
        bands: Tuple[Tuple[float, str], ...] = (),
        fmt: Callable[[Any], str] = lambda v: f"{v}",
    ):
        self.name = name
        self.definition = definition
        self.teaching = teaching
        self.bands = bands
        self.fmt = fmt

    def interpret(self, value: Any) -> Optional[str]:
        if not self.bands or not isinstance(value, (int, float)):
            return None
        shown = self.fmt(value)
        for threshold, desc in self.bands:
            if value < threshold:
                return desc.format(value=shown)
        return self.bands[-1][1].format(value=shown)


_pct = lambda v: f"{v * 100:.1f}%"  # noqa: E731
_two = lambda v: f"{v:.2f}"  # noqa: E731

GENRE_LABELS = {
    "argumentative": "议论文",
    "expository": "说明文",
    "narrative": "记叙文",
    "scientific": "科学说明文",
    "通用": "通用文本",
}

METRICS: Dict[str, MetricSpec] = {
    "总词数": MetricSpec(
        name="总词数",
        definition="课文中所有可识别词的总数量（含重复）。",
        teaching="词数决定课堂节奏：长课文要切片处理，避免学生疲劳。",
        bands=(
            (120, "本文 {value} 词：短文本，适合单课时精讲与整篇处理"),
            (300, "本文 {value} 词：单课时精读的典型长度"),
            (600, "本文 {value} 词：中长文本，建议分段处理或安排两课时"),
            (float("inf"), "本文 {value} 词：长文本，建议泛读加节选精读"),
        ),
    ),
    "平均句长": MetricSpec(
        name="平均句长",
        definition="课文每句的平均词数。",
        teaching="句长影响解码负荷，长句多时建议预拆从句。",
        bands=(
            (12, "本文平均 {value} 词：句子短，解码负荷低，可加快节奏"),
            (19, "本文平均 {value} 词：中等句长，按课堂常规处理"),
            (26, "本文平均 {value} 词：偏学术句法，需长句拆分支架"),
            (float("inf"), "本文平均 {value} 词：句法负荷重，建议逐句结构图解"),
        ),
    ),
    "连接密度": MetricSpec(
        name="连接密度",
        definition="每百词中逻辑连接词（however/therefore/因此/所以等）的数量。",
        teaching="密度低需补连接词教学；密度高需帮学生梳理逻辑链。",
        bands=(
            (3, "本文 {value}/百词：衔接稀疏，可补连接词识别练习"),
            (8, "本文 {value}/百词：衔接适中，随文点拨即可"),
            (12, "本文 {value}/百词：逻辑密集，适合语篇标记词专项训练"),
            (float("inf"), "本文 {value}/百词：逻辑链极密，需帮学生梳理句际关系"),
        ),
    ),
    "AWL 占比": MetricSpec(
        name="AWL 占比",
        definition="Academic Word List 学术词汇表（Coxhead 编制，570 词族）覆盖比例。",
        teaching="占比高意味着学生需要先建立学术词汇图，再进入课文。",
        bands=(
            (0.03, "本文 {value}：属日常叙事类文本，学术色彩弱"),
            (0.08, "本文 {value}：一般学术文本水平，可随文讲解"),
            (0.15, "本文 {value}：高阶学术文本，建议课前发词汇预习单"),
            (float("inf"), "本文 {value}：专业/科研语篇密度，需系统学术词汇支架"),
        ),
        fmt=_pct,
    ),
    "可读性指数": MetricSpec(
        name="可读性指数",
        definition="Flesch Reading Ease 指数，0-100 分制，越高越易读。",
        teaching="指数低需提前设计支架，否则课堂推进会卡。",
        bands=(
            (30, "本文 {value}：很难，需支架先行"),
            (50, "本文 {value}：偏难，建议先做段落大意匹配"),
            (60, "本文 {value}：中等难度，常规引导即可"),
            (70, "本文 {value}：较易，可直接进入任务"),
            (float("inf"), "本文 {value}：极易进入课堂"),
        ),
    ),
    "词汇丰富度": MetricSpec(
        name="词汇丰富度",
        definition="Type-Token Ratio（TTR），= 不重复词 / 总词数，值越高词汇越多样。",
        teaching="值高要预留词汇预习时间；值低可做词汇强化操练。",
        bands=(
            (0.4, "本文 TTR {value}：词汇重复率高，适合词汇强化操练"),
            (0.65, "本文 TTR {value}：词汇多样性适中"),
            (float("inf"), "本文 TTR {value}：词汇多样性高，需预留预习与查词时间"),
        ),
        fmt=_two,
    ),
    "难词数": MetricSpec(
        name="难词数",
        definition="超出目标学习者水平（C1-C2 级或未分级生僻词）的词数。",
        teaching="难词数高要先做词汇预热，再进入课文。",
        bands=(
            (6, "本文 {value} 个：超纲负荷可控，可随文处理"),
            (15, "本文 {value} 个：建议课前预教高频难点词"),
            (float("inf"), "本文 {value} 个：超纲词密集，需词汇表与分层任务"),
        ),
    ),
    "长句": MetricSpec(
        name="长句",
        definition="词数大于 30 的句子。",
        teaching="长句多时要在课件上做从句拆分图示。",
        bands=(
            (4, "本文 {value} 句：零星长句，可个别处理"),
            (10, "本文 {value} 句：长句较多，建议选典型句做拆分练习"),
            (float("inf"), "本文 {value} 句：长句密集，句法教学要前置"),
        ),
    ),
    "超长句": MetricSpec(
        name="超长句",
        definition="词数大于 40 的句子，认知负荷显著。",
        teaching="超长句要在课堂上慢速处理并板书结构。",
        bands=(
            (3, "本文 {value} 句：个别超长句"),
            (float("inf"), "本文 {value} 句：超长句频繁，认知负荷显著"),
        ),
    ),
    "不重复词": MetricSpec(
        name="不重复词",
        definition="课文去重后的独立词数，反映词汇分布广度。",
        teaching="与总词数对比可看重复率；重复率低说明需更多预习时间。",
    ),
    "AWL 学术词": MetricSpec(
        name="AWL 学术词",
        definition="课文中命中 AWL 学术词表的不重复词数。",
        teaching="可作为重点词汇教学的优先级依据。",
    ),
    "句子数": MetricSpec(
        name="句子数",
        definition="课文被自动切分出的句子总数。",
        teaching="切分异常时（句子数过少）需人工校对课文断句。",
    ),
    "段落数": MetricSpec(
        name="段落数",
        definition="课文按空行切出的段落总数。",
        teaching="用于设计课堂分段阅读节奏。",
    ),
    "体裁": MetricSpec(
        name="体裁",
        definition="课文的语篇类型（议论/说明/记叙/科学说明等），由连接词分布与句法特征推断。",
        teaching="体裁决定教学重点：议论抓论点链，叙述抓情节链。",
    ),
    "文本结构": MetricSpec(
        name="文本结构",
        definition="课文的宏观组织模式（如总-分、问题-解决、对比等）。",
        teaching="可在课堂开头画结构图，让学生预期信息走向。",
    ),
    "CEFR 词汇分布": MetricSpec(
        name="CEFR 词汇分布",
        definition="课文词汇按欧洲共同语言参考标准（A1-C2）分级后的占比。",
        teaching="基础词覆盖率高说明课文易；未分级词多为低频生僻词，多数已由 AI 定级。",
    ),
    "六维分析雷达": MetricSpec(
        name="六维分析雷达",
        definition="从词汇、句法、语篇、可读性、连接度、学术度六个维度归一化打分，雷达图呈现。",
        teaching="用于一眼判断课文的课堂组织成本。",
    ),
}


def _entry(spec: MetricSpec, value: Any, override: Optional[str] = None) -> Dict[str, str]:
    interpretation = override if override is not None else spec.interpret(value)
    entry: Dict[str, str] = {
        "name": spec.name,
        "definition": spec.definition,
        "teaching": spec.teaching,
    }
    if interpretation:
        entry["interpretation"] = interpretation
    return entry


def build_glossary(result) -> Dict[str, Dict[str, str]]:
    """按白盒分析结果实例化术语表：interpretation 带本文实际数值。"""
    v, s, d = result.vocabulary, result.syntax, result.discourse
    total = v.total_words or 1

    dist = v.cefr_distribution
    base_pct = dist.get("A1-A2", 0) / total * 100
    adv_pct = dist.get("C1-C2", 0) / total * 100
    cefr_override = (
        f"本文基础词（A1-A2）占 {base_pct:.0f}%，高阶词（C1-C2）占 {adv_pct:.0f}%"
        + ("，整体偏易进入课堂" if base_pct > 60 else "，整体难度中等或偏难")
    )

    genre_label = GENRE_LABELS.get(d.genre_hint, d.genre_hint)
    genre_override = f"本文判定为{genre_label}。{_spec_genre_advice(d.genre_hint)}" if d.genre_hint else None
    structure_override = f"本文宏观结构为「{d.text_structure}」，可引导学生识别篇章组织模式" if d.text_structure else None

    glossary: Dict[str, Dict[str, str]] = {
        "总词数": _entry(METRICS["总词数"], v.total_words),
        "不重复词": _entry(METRICS["不重复词"], v.unique_words),
        "词汇丰富度": _entry(METRICS["词汇丰富度"], v.vocabulary_richness),
        "AWL 学术词": _entry(METRICS["AWL 学术词"], v.awl_count),
        "AWL 占比": _entry(METRICS["AWL 占比"], v.awl_ratio),
        "难词数": _entry(METRICS["难词数"], len(v.difficult_words)),
        "CEFR 词汇分布": _entry(METRICS["CEFR 词汇分布"], None, override=cefr_override),
        "句子数": _entry(METRICS["句子数"], s.total_sentences),
        "平均句长": _entry(METRICS["平均句长"], s.avg_sentence_length),
        "长句": _entry(METRICS["长句"], s.long_sentences_count),
        "超长句": _entry(METRICS["超长句"], s.very_long_sentences_count),
        "可读性指数": _entry(METRICS["可读性指数"], s.flesch_reading_ease),
        "Flesch": _entry(METRICS["可读性指数"], s.flesch_reading_ease),
        "可读性": _entry(METRICS["可读性指数"], s.flesch_reading_ease),
        "段落数": _entry(METRICS["段落数"], d.paragraph_count),
        "连接密度": _entry(METRICS["连接密度"], d.connective_density),
        "体裁": _entry(METRICS["体裁"], d.genre_hint, override=genre_override),
        "文本结构": _entry(METRICS["文本结构"], d.text_structure, override=structure_override),
        "六维分析雷达": _entry(METRICS["六维分析雷达"], None),
    }
    return glossary


def _spec_genre_advice(genre: str) -> str:
    return {
        "argumentative": "议论类课文适合论点-论据链分析活动。",
        "expository": "说明类课文适合段落大意匹配与信息结构图。",
        "narrative": "记叙类课文适合情节链梳理与人物动机讨论。",
        "scientific": "科学说明类课文适合引入体裁分析框架（如 CARS 模型）。",
    }.get(genre, "")
