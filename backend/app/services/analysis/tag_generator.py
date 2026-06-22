"""
增强标签生成器

基于白盒分析结果，通过硬编码规则生成增强标签。
标签用于驱动双源检索：Wiki理论摘要 + RAG专家案例。

设计原则：
- 标签是轻量的字符串标识，不是复杂的Pydantic模型
- 规则基于阈值，透明可调试
- 每个标签关联wiki_tags和rag_tags，用于检索
"""

from typing import Dict, List, Any, Callable
from dataclasses import dataclass


@dataclass
class TagRule:
    """标签规则"""
    condition: Callable[[Any], bool]  # 接收WhiteboxAnalysisResult
    wiki_tags: List[str]              # 用于Wiki检索的标签
    rag_tags: List[str]               # 用于RAG检索的标签
    description: str                  # 标签描述


# ============ 标签规则映射表 ============

TAG_RULES: Dict[str, TagRule] = {
    "high_academic_vocab": TagRule(
        condition=lambda r: r.vocabulary.awl_ratio > 0.15,
        wiki_tags=["academic-word-list", "awl-teaching", "vocabulary-scaffolding"],
        rag_tags=["academic-vocabulary", "awl-scaffolding", "word-list-teaching"],
        description="学术词汇占比高（>15%）"
    ),
    "very_high_academic_vocab": TagRule(
        condition=lambda r: r.vocabulary.awl_ratio > 0.25,
        wiki_tags=["academic-word-list", "specialized-vocabulary"],
        rag_tags=["high-density-academic-vocab", "technical-vocabulary-teaching"],
        description="学术词汇占比极高（>25%）"
    ),
    "many_difficult_words": TagRule(
        condition=lambda r: len([d for d in r.vocabulary.difficult_words if d.level in ("C1", "C2", "unknown")]) > 10,
        wiki_tags=["vocabulary-difficulty", "lexical-threshold"],
        rag_tags=["vocabulary-scaffolding", "pre-teaching-vocabulary"],
        description="超纲词数量多（>10个C1/C2/未分级词）"
    ),
    "long_sentences_present": TagRule(
        condition=lambda r: r.syntax.max_sentence.word_count > 30,
        wiki_tags=["syntactic-complexity", "sentence-processing"],
        rag_tags=["long-sentence-teaching", "syntax-visualization", "sentence-parsing"],
        description="包含超长句（>30词）"
    ),
    "very_long_sentences": TagRule(
        condition=lambda r: r.syntax.max_sentence.word_count > 40,
        wiki_tags=["syntactic-complexity", "sentence-processing", "working-memory"],
        rag_tags=["sentence-parsing", "chunking-strategy"],
        description="包含极长句（>40词）"
    ),
    "dense_complex_syntax": TagRule(
        condition=lambda r: r.syntax.long_sentences_count > 5,
        wiki_tags=["syntactic-complexity", "clause-analysis"],
        rag_tags=["grammar-visualiation", "sentence-simplification"],
        description="长句密集（>5个超过30词的句子）"
    ),
    "very_difficult_readability": TagRule(
        condition=lambda r: r.syntax.flesch_reading_ease < 30,
        wiki_tags=["readability", "text-difficulty"],
        rag_tags=["scaffolding-activity", "graded-reading"],
        description="可读性极低（Flesch<30）"
    ),
    "difficult_readability": TagRule(
        condition=lambda r: r.syntax.flesch_reading_ease < 50,
        wiki_tags=["readability", "comprehension-strategies"],
        rag_tags=["pre-reading-activity", "guided-reading"],
        description="可读性较低（Flesch<50）"
    ),
    "high_connective_density": TagRule(
        condition=lambda r: r.discourse.connective_density > 3.0,
        wiki_tags=["cohesion", "discourse-markers"],
        rag_tags=["connective-teaching", "discourse-analysis-activity"],
        description="连接词密度高（>3/百词）"
    ),
    "argumentative_text": TagRule(
        condition=lambda r: r.discourse.genre_hint == "argumentative",
        wiki_tags=["genre-analysis", "rhetorical-structure"],
        rag_tags=["argumentative-writing", "critical-thinking-activity"],
        description="议论文体裁"
    ),
    "scientific_text": TagRule(
        condition=lambda r: r.discourse.genre_hint == "scientific",
        wiki_tags=["genre-analysis", "academic-discourse"],
        rag_tags=["scientific-reading", "research-article-teaching"],
        description="科学/学术体裁"
    ),
    "i_plus_2_risk": TagRule(
        condition=lambda r: r.learner_gap.gap == "i+2",
        wiki_tags=["krashen-input-hypothesis", "i-plus-1", "scaffolding-theory"],
        rag_tags=["scaffolding-activity", "below-level-students", "differentiated-instruction"],
        description="课文难度远超学生水平（i+2风险）"
    ),
    "i_plus_1_optimal": TagRule(
        condition=lambda r: r.learner_gap.gap == "i+1",
        wiki_tags=["krashen-input-hypothesis", "i-plus-1", "comprehensible-input"],
        rag_tags=["optimal-challenge", "zone-of-proximal-development"],
        description="课文难度处于最近发展区（i+1最佳）"
    ),
    "high_lexical_diversity": TagRule(
        condition=lambda r: r.vocabulary.vocabulary_richness > 0.7,
        wiki_tags=["lexical-diversity", "vocabulary-range"],
        rag_tags=["vocabulary-expansion", "word-variation-activity"],
        description="词汇丰富度高（TTR>0.7）"
    ),
}


def generate_tag_details(analysis_result) -> Dict[str, Dict]:
    """
    生成标签详情，包含wiki_tags和rag_tags映射

    Args:
        analysis_result: WhiteboxAnalysisResult实例

    Returns:
        {
            "high_academic_vocab": {
                "description": "...",
                "wiki_tags": [...],
                "rag_tags": [...]
            },
            ...
        }
    """
    result = {}
    for tag_name, rule in TAG_RULES.items():
        try:
            if rule.condition(analysis_result):
                result[tag_name] = {
                    "description": rule.description,
                    "wiki_tags": rule.wiki_tags,
                    "rag_tags": rule.rag_tags,
                }
        except (AttributeError, TypeError):
            # 如果分析结果缺少某个字段，跳过该规则
            continue
    return result


def get_wiki_tags_for_retrieval(tag_details: Dict[str, Dict]) -> List[str]:
    """从标签详情中提取所有wiki_tags（去重）"""
    tags = set()
    for detail in tag_details.values():
        tags.update(detail.get("wiki_tags", []))
    return sorted(tags)


def get_rag_tags_for_retrieval(tag_details: Dict[str, Dict]) -> List[str]:
    """从标签详情中提取所有rag_tags（去重）"""
    tags = set()
    for detail in tag_details.values():
        tags.update(detail.get("rag_tags", []))
    return sorted(tags)
