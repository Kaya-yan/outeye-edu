from dataclasses import dataclass, field
from typing import List


TAG_TO_WIKI_QUERY = {
    "high_academic_vocab": "学术词汇教学 AWL 词汇习得策略",
    "very_high_academic_vocab": "高密度学术词汇 词汇教学法",
    "many_difficult_words": "超纲词处理 词汇支架 scaffolding",
    "moderate_difficult_words": "词汇预教学 pre-teaching",
    "very_long_sentences": "长难句分析 句法拆分 sentence parsing",
    "long_sentences_present": "复杂句教学 阅读理解策略",
    "dense_complex_syntax": "句法复杂度 句子简化策略",
    "very_difficult_readability": "可读性 readability Flesch 分级阅读",
    "difficult_readability": "文本难度评估 阅读支架",
    "high_connective_density": "连接词 语篇标记 cohesive devices",
    "argumentative_text": "议论文教学 argumentation 论证分析",
    "scientific_text": "学术语篇 科学文本阅读 EAP",
    "i_plus_2_risk": "Krashen 输入假说 i+1 最近发展区 ZPD 支架教学",
    "i_plus_1_optimal": "最近发展区 ZPD 支架教学",
    "high_lexical_diversity": "词汇丰富度 TTR 词汇多样性教学",
}

TAG_TO_RAG_QUERY = {
    "high_academic_vocab": "学术词汇预习单 词汇教学活动设计",
    "very_high_academic_vocab": "词汇分层教学 差异化词汇任务",
    "many_difficult_words": "词汇支架活动 预教学词汇 词汇表设计",
    "moderate_difficult_words": "词汇练习 语境猜词策略",
    "very_long_sentences": "长句拆分练习 句法分析活动",
    "long_sentences_present": "句子成分分析 复杂句教学策略",
    "dense_complex_syntax": "句法简化 逐层理解活动",
    "very_difficult_readability": "段落大意匹配 预读活动 scaffolding",
    "difficult_readability": "引导式阅读 阅读理解支架",
    "high_connective_density": "连接词识别活动 语篇分析练习",
    "argumentative_text": "论点论据分析 议论文写作教学",
    "scientific_text": "学术文本阅读策略 研究论文教学",
    "i_plus_2_risk": "双语词汇表 结构化阅读支架 差异化教学",
    "i_plus_1_optimal": "深层理解活动 批判性思维训练",
    "high_lexical_diversity": "词汇扩展活动 同义词替换练习",
}


@dataclass
class RetrievalPlan:
    wiki_query: str
    rag_query: str
    strategy: str
    risk_flags: List[str] = field(default_factory=list)
    primary_focus: List[str] = field(default_factory=list)


class RetrievalPlanner:
    def build(
        self,
        wiki_tags: List[str],
        rag_tags: List[str],
        enhancement_tags: List[str],
        text_title: str = "",
    ) -> RetrievalPlan:
        all_tags = self._unique(wiki_tags + rag_tags + enhancement_tags)
        risk_flags = [tag for tag in all_tags if tag in {
            "i_plus_2_risk",
            "very_difficult_readability",
            "many_difficult_words",
            "very_long_sentences",
        }]

        primary_focus = []
        if any(tag in all_tags for tag in ["high_academic_vocab", "very_high_academic_vocab", "many_difficult_words"]):
            primary_focus.append("vocabulary")
        if any(tag in all_tags for tag in ["very_long_sentences", "dense_complex_syntax"]):
            primary_focus.append("syntax")
        if any(tag in all_tags for tag in ["argumentative_text", "high_connective_density", "scientific_text"]):
            primary_focus.append("discourse")
        if "i_plus_2_risk" in all_tags:
            primary_focus.insert(0, "support")

        strategy = "support_first" if "i_plus_2_risk" in risk_flags else "balanced"

        wiki_query = self._build_query(wiki_tags, enhancement_tags, TAG_TO_WIKI_QUERY, strategy)
        rag_query = self._build_query(rag_tags, enhancement_tags, TAG_TO_RAG_QUERY, strategy)

        if not wiki_query and text_title:
            wiki_query = text_title
        if not rag_query and text_title:
            rag_query = text_title

        return RetrievalPlan(
            wiki_query=wiki_query,
            rag_query=rag_query,
            strategy=strategy,
            risk_flags=risk_flags,
            primary_focus=self._unique(primary_focus),
        )

    def _build_query(self, primary_tags: List[str], enhancement_tags: List[str], mapping: dict, strategy: str) -> str:
        ordered_tags = self._prioritize_tags(primary_tags, enhancement_tags, strategy)
        queries = []
        for tag in ordered_tags:
            if tag in mapping:
                queries.append(mapping[tag])
            else:
                queries.append(tag.replace("_", " "))
        return " ".join(self._unique(queries)[:3])

    def _prioritize_tags(self, primary_tags: List[str], enhancement_tags: List[str], strategy: str) -> List[str]:
        tags = self._unique(primary_tags + enhancement_tags)
        if strategy != "support_first":
            return tags

        priority_order = [
            "i_plus_2_risk",
            "many_difficult_words",
            "very_difficult_readability",
            "very_long_sentences",
        ]
        prioritized = [tag for tag in priority_order if tag in tags]
        remaining = [tag for tag in tags if tag not in prioritized]
        return prioritized + remaining

    def _unique(self, items: List[str]) -> List[str]:
        return list(dict.fromkeys([item for item in items if item]))
