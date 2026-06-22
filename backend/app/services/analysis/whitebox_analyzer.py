"""
白盒分析器 - OutEye Edu 1.0

输出教师能看懂、能验证的透明指标，不输出黑盒分数。
每个指标附带"这意味着什么"的教学提示。

设计原则：
- 词汇：CEFR分布、AWL占比、超纲词列表（含单词+等级+出现次数）
- 句法：平均句长、最长句预览、长句数量
- 语篇：连接词密度、段落功能标记
- 学习者适配：课文等级 vs 学生等级差距
- 增强标签：基于规则自动生成
- 教学提示：可读的建议
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import re
import json
import os
import functools
from collections import Counter


# ============ 数据模型 ============

@dataclass
class DifficultWord:
    """超纲词条目"""
    word: str
    level: str          # CEFR等级：B2/C1/C2/unknown
    count: int          # 出现次数
    in_awl: bool        # 是否在学术词汇表中


@dataclass
class VocabAnalysis:
    """词汇分析结果"""
    total_words: int
    unique_words: int
    cefr_distribution: Dict[str, int]   # {"A1-A2": 156, "B1-B2": 134, "C1-C2": 52}
    awl_count: int                      # AWL词汇数
    awl_ratio: float                    # AWL占比
    difficult_words: List[DifficultWord]  # 超纲词列表（按出现次数降序）
    vocabulary_richness: float          # 词汇丰富度 (TTR)


@dataclass
class LongestSentence:
    """最长句信息"""
    preview: str        # 前100字符预览
    word_count: int     # 全句词数
    index: int          # 第几句（从0开始）


@dataclass
class SyntaxAnalysis:
    """句法分析结果"""
    total_sentences: int
    avg_sentence_length: float
    max_sentence: LongestSentence
    long_sentences_count: int           # >30词的句子数
    very_long_sentences_count: int      # >40词的句子数
    flesch_reading_ease: float


@dataclass
class ParagraphFunction:
    """段落功能"""
    index: int
    function: str       # introduction/body/conclusion/example/transition
    preview: str        # 前50字符


@dataclass
class DiscourseAnalysis:
    """语篇分析结果"""
    paragraph_count: int
    connective_density: float           # 连接词密度（每100词）
    paragraph_functions: List[ParagraphFunction]
    genre_hint: str                     # 体裁提示
    text_structure: str = ""            # 文本结构（如"问题-解决"、"因果"等）
    teaching_points: List[str] = field(default_factory=list)  # 教学要点


@dataclass
class LearnerGap:
    """学习者适配分析"""
    text_level: str                     # 系统判定的课文等级
    student_level: str                  # 用户设定的学生等级
    gap: str                            # "i+0" / "i+1" / "i+2"
    gap_description: str                # 人话描述


@dataclass
class TeachingInsight:
    """教学含义——将指标翻译为教师可理解的教学决策"""
    metric_name: str          # 指标名称（中文）
    metric_value: Any         # 指标值
    teaching_implication: str # 教学含义
    suggested_action: str     # 建议动作
    confidence: str           # high/medium/low


@dataclass
class CulturalElement:
    """文化元素"""
    category: str           # 类别：习俗/历史/社会/价值观/地理/文学
    keyword: str            # 关键词
    context: str            # 出现语境（原文片段）
    explanation: str        # 教学说明


@dataclass
class WhiteboxAnalysisResult:
    """白盒分析完整结果"""
    vocabulary: VocabAnalysis
    syntax: SyntaxAnalysis
    discourse: DiscourseAnalysis
    learner_gap: LearnerGap
    text_level: str                     # 综合判定的课文CEFR等级
    enhancement_tags: List[str]         # 保持向后兼容
    teaching_tips: List[str]
    tag_labels: Dict[str, str]          # {tag: 中文标签}
    teaching_insights: List[Dict[str, str]] # [{metric_name, metric_value, teaching_implication, suggested_action, confidence}]
    cultural_elements: List[CulturalElement] = field(default_factory=list)
    analysis_version: str = "whitebox-v1"
    language: str = "en"                # 检测到的语言代码
    language_name: str = "英语"         # 语言显示名称


# 增强标签中英文映射
TAG_DISPLAY = {
    "high_academic_vocab": "学术词汇密集",
    "very_high_academic_vocab": "学术词汇极密集",
    "many_difficult_words": "难点词较多",
    "moderate_difficult_words": "难点词中等",
    "very_long_sentences": "超长句频繁",
    "long_sentences_present": "存在长句",
    "dense_complex_syntax": "句法结构密集",
    "very_difficult_readability": "可读性极难",
    "difficult_readability": "可读性较难",
    "high_connective_density": "衔接词密集",
    "argumentative_text": "议论文体裁",
    "scientific_text": "科学说明体裁",
    "i_plus_2_risk": "难度超标风险",
    "i_plus_1_optimal": "最优学习区间",
    "high_lexical_diversity": "词汇多样性高",
}


# ============ CEFR词表加载 ============

@functools.lru_cache(maxsize=1)
def _load_cefr_wordlist() -> Dict[str, str]:
    """加载CEFR词表，返回 {word: level} 映射"""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    wordlist_path = os.path.join(data_dir, "cefr_wordlist.json")

    word_map: Dict[str, str] = {}
    level_order = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

    try:
        with open(wordlist_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            word = entry["word"].lower().strip()
            level = entry["level"]
            # 冲突处理：取最高等级
            if word in word_map:
                old_rank = level_order.get(word_map[word], 0)
                new_rank = level_order.get(level, 0)
                if new_rank > old_rank:
                    word_map[word] = level
            else:
                word_map[word] = level
    except FileNotFoundError:
        # 如果词表文件不存在，使用内置基础词表
        word_map = _builtin_cefr_fallback()

    return word_map


@functools.lru_cache(maxsize=1)
def _load_jlpt_wordlist() -> Dict[str, str]:
    """加载JLPT词表（日语），返回 {word: level} 映射"""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    wordlist_path = os.path.join(data_dir, "jlpt_wordlist.json")

    word_map: Dict[str, str] = {}
    try:
        with open(wordlist_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            word = entry["word"].strip()
            word_map[word] = entry["level"]
    except FileNotFoundError:
        pass

    return word_map


@functools.lru_cache(maxsize=1)
def _load_topik_wordlist() -> Dict[str, str]:
    """加载TOPIK词表（韩语），返回 {word: level} 映射"""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    wordlist_path = os.path.join(data_dir, "topik_wordlist.json")

    word_map: Dict[str, str] = {}
    try:
        with open(wordlist_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            word = entry["word"].strip()
            word_map[word] = entry["level"]
    except FileNotFoundError:
        pass

    return word_map


def _builtin_cefr_fallback() -> Dict[str, str]:
    """内置基础CEFR词表（约500词，仅用于fallback）"""
    a1 = [
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
        'should', 'may', 'might', 'can', 'could', 'must', 'need',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
        'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
        'this', 'that', 'these', 'those', 'what', 'which', 'who', 'where',
        'when', 'why', 'how', 'and', 'but', 'or', 'not', 'so', 'if',
        'good', 'bad', 'big', 'small', 'new', 'old', 'first', 'last',
        'long', 'great', 'little', 'right', 'high', 'different',
        'man', 'woman', 'child', 'person', 'people', 'time', 'year',
        'way', 'day', 'thing', 'world', 'life', 'hand', 'part', 'place',
        'case', 'week', 'work', 'number', 'night', 'point', 'home',
        'water', 'room', 'mother', 'area', 'money', 'story', 'fact',
        'month', 'lot', 'study', 'book', 'eye', 'job', 'word', 'name',
    ]
    a2 = [
        'about', 'above', 'after', 'again', 'against', 'ago', 'agree',
        'allow', 'almost', 'along', 'already', 'also', 'always', 'among',
        'another', 'answer', 'anyone', 'anything', 'around', 'away',
        'become', 'before', 'begin', 'behind', 'below', 'between',
        'both', 'bring', 'build', 'buy', 'call', 'carry', 'change',
        'city', 'close', 'come', 'company', 'country', 'cover', 'cross',
        'cut', 'develop', 'die', 'door', 'down', 'draw', 'drive',
        'drop', 'early', 'easy', 'eat', 'else', 'end', 'enough',
        'even', 'ever', 'every', 'example', 'experience', 'family',
        'far', 'feel', 'few', 'find', 'follow', 'food', 'foot',
        'form', 'free', 'front', 'full', 'game', 'get', 'give',
        'go', 'group', 'grow', 'half', 'happen', 'hard', 'head',
        'hear', 'help', 'here', 'hold', 'hope', 'house', 'hundred',
        'idea', 'important', 'include', 'interest', 'keep', 'kind',
        'know', 'land', 'language', 'large', 'later', 'lead', 'learn',
        'leave', 'let', 'level', 'line', 'live', 'local', 'lose',
        'love', 'main', 'make', 'mean', 'meet', 'mind', 'miss',
        'moment', 'move', 'much', 'music', 'name', 'near', 'need',
        'never', 'next', 'nice', 'nothing', 'offer', 'often',
    ]
    b1 = [
        'accept', 'achieve', 'act', 'add', 'admit', 'adult', 'advantage',
        'affect', 'afford', 'age', 'agent', 'agree', 'aim', 'amount',
        'announce', 'annual', 'apparently', 'approach', 'argue', 'arm',
        'article', 'attack', 'attention', 'available', 'average', 'avoid',
        'base', 'basic', 'beat', 'beauty', 'bed', 'believe', 'benefit',
        'beyond', 'bill', 'bit', 'black', 'blood', 'blow', 'board',
        'born', 'box', 'break', 'brother', 'budget', 'bus', 'business',
        'campaign', 'capital', 'care', 'career', 'cause', 'century',
        'certain', 'chair', 'challenge', 'chance', 'check', 'choice',
        'church', 'claim', 'class', 'clear', 'cold', 'college',
        'common', 'community', 'compare', 'computer', 'concern',
        'condition', 'conference', 'consider', 'consumer', 'contain',
        'continue', 'control', 'cost', 'couple', 'course', 'court',
        'create', 'crime', 'cultural', 'culture', 'cup', 'current',
        'customer', 'dark', 'data', 'daughter', 'dead', 'deal', 'death',
        'debate', 'decade', 'decide', 'decision', 'deep', 'defence',
        'degree', 'demand', 'democratic', 'describe', 'design', 'despite',
        'detail', 'determine', 'die', 'director', 'discover', 'discuss',
        'discussion', 'disease', 'doctor', 'dog', 'dream', 'drink',
        'drive', 'drop', 'drug', 'each', 'east', 'economic', 'economy',
        'edge', 'education', 'effect', 'effort', 'eight', 'either',
        'election', 'else', 'emerge', 'employee', 'environment',
        'especially', 'establish', 'evening', 'event', 'evidence',
        'exactly', 'executive', 'exist', 'expect', 'expense',
        'expert', 'explain', 'express', 'extend', 'external', 'extra',
    ]
    b2 = [
        'abstract', 'academic', 'accelerate', 'accommodate', 'accumulate',
        'accurate', 'acknowledge', 'acquire', 'adapt', 'adequate',
        'adjust', 'administration', 'adopt', 'advance', 'advocate',
        'agenda', 'aggressive', 'agriculture', 'aid', 'alternative',
        'ambiguous', 'amend', 'analyse', 'anticipate', 'apparent',
        'appeal', 'appreciate', 'appropriate', 'approve', 'arise',
        'artificial', 'assess', 'assign', 'assist', 'assume', 'assure',
        'atmosphere', 'attach', 'attain', 'attempt', 'attribute',
        'authority', 'automatic', 'aware', 'barrier', 'bias', 'brief',
        'broad', 'bulk', 'capable', 'capacity', 'capture', 'category',
        'cease', 'chain', 'channel', 'chapter', 'chart', 'chemical',
        'circumstance', 'civil', 'clarify', 'classic', 'climate',
        'clinical', 'coincide', 'collapse', 'colleague', 'combine',
        'comment', 'commission', 'commit', 'communicate', 'complex',
        'component', 'comprehensive', 'comprise', 'compromise',
        'concentrate', 'concept', 'conclude', 'conduct', 'confine',
        'confirm', 'conflict', 'conform', 'confront', 'congress',
        'connect', 'conscious', 'consensus', 'consequence', 'conservative',
        'considerable', 'consistent', 'constitute', 'construct',
        'consult', 'consume', 'contemporary', 'context', 'contract',
        'contradict', 'contribute', 'controversial', 'convention',
        'convert', 'convince', 'cooperate', 'core', 'corporate',
        'correspond', 'council', 'couple', 'creative', 'credit',
        'criminal', 'crisis', 'criteria', 'critical', 'crucial',
    ]
    c1 = [
        'abandon', 'abolish', 'absorb', 'abuse', 'accomplish', 'accord',
        'accountability', 'accumulate', 'acquisition', 'adhere',
        'adjacent', 'administer', 'adverse', 'advocate', 'aesthetic',
        'aggregate', 'albeit', 'allegation', 'allocate', 'alliance',
        'alter', 'amateur', 'ambiguous', 'amid', 'analogy', 'anchor',
        'annotate', 'apparatus', 'applicable', 'arbitrary', 'archive',
        'array', 'articulate', 'aspire', 'assert', 'asset', 'assimilate',
        'asylum', 'attorney', 'audit', 'autonomy', 'backdrop', 'bail',
        'bankruptcy', 'benchmark', 'benefactor', 'bestow', 'bizarre',
        'blueprint', 'bolster', 'bottleneck', 'breach', 'brochure',
        'broker', 'browse', 'brutal', 'bureaucracy', 'calibrate',
        'campaign', 'catalyst', 'cater', 'caution', 'census', 'ceremony',
        'charter', 'chronic', 'circulate', 'cite', 'civic', 'coalition',
        'coherent', 'coincide', 'collaborate', 'commemorate', 'commence',
        'commend', 'commentary', 'commission', 'commodity', 'communal',
        'compact', 'compatible', 'compel', 'compile', 'complement',
        'compliance', 'compulsory', 'compute', 'conceive', 'condemn',
        'confer', 'configuration', 'confiscate', 'conformity',
        'congregate', 'conjecture', 'conscience', 'consecutive',
        'consent', 'conserve', 'consolidate', 'conspiracy', 'constituent',
        'constraint', 'consul', 'contaminate', 'contempt', 'contend',
    ]
    c2 = [
        'aberration', 'abhor', 'abide', 'abject', 'ablaze', 'abnormal',
        'abode', 'abolition', 'abrupt', 'absolve', 'abstain', 'absurd',
        'abundance', 'acclaim', 'accolade', 'accord', 'accrue',
        'acquaint', 'acquit', 'acrimony', 'adamant', 'adept', 'adherent',
        'adjourn', 'admonish', 'advent', 'adversary', 'aegis', 'affable',
        'affinity', 'afflict', 'affluent', 'aftermath', 'aggravate',
        'aggrieve', 'agile', 'ailment', 'alacrity', 'alchemy', 'alibi',
        'alienate', 'allegiance', 'alleviate', 'allot', 'allude',
        'allure', 'aloof', 'altercation', 'amalgamate', 'amass',
        'ambivalent', 'ameliorate', 'amiable', 'ample', 'amplify',
        'anarchy', 'anecdotal', 'anguish', 'animosity', 'annex',
        'annihilate', 'anomaly', 'antagonize', 'anthology', 'antiquated',
        'apathy', 'apprehend', 'apprise', 'aptitude', 'arbitrary',
        'archaic', 'ardent', 'arduous', 'aristocracy', 'aroma',
        'arrogance', 'articulate', 'ascend', 'ascertain', 'ascribe',
        'aspersion', 'assiduous', 'astute', 'atrocity', 'attest',
        'audacious', 'auspicious', 'austere', 'autonomous', 'avarice',
    ]

    result = {}
    for w in a1: result[w] = "A1"
    for w in a2: result[w] = "A2"
    for w in b1: result[w] = "B1"
    for w in b2: result[w] = "B2"
    for w in c1: result[w] = "C1"
    for w in c2: result[w] = "C2"
    return result


# ============ AWL词表 ============

_awl_cache: Optional[set] = None


@functools.lru_cache(maxsize=1)
def _load_awl_wordlist() -> set:
    """加载学术词汇表（AWL）"""
    # AWL核心词表（570词族，这里列出高频词头）
    awl_words = {
        'abandon', 'abstract', 'accurate', 'achieve', 'acquire', 'adapt',
        'adequate', 'adjust', 'administrate', 'advocate', 'affect', 'aggregate',
        'allocate', 'alter', 'ambiguous', 'analogy', 'analyse', 'annual',
        'anticipate', 'apparent', 'append', 'appreciate', 'approach', 'appropriate',
        'approximate', 'arbitrary', 'aspect', 'assemble', 'assess', 'assign',
        'assist', 'associate', 'assume', 'assure', 'attach', 'attribute',
        'authority', 'available', 'aware', 'behalf', 'benefit', 'bias',
        'bond', 'brief', 'bulk', 'capable', 'capacity', 'category',
        'cease', 'challenge', 'channel', 'chapter', 'chart', 'chronic',
        'circumstance', 'cite', 'civil', 'clarify', 'classic', 'clause',
        'code', 'coherent', 'coincide', 'collapse', 'colleague', 'commence',
        'comment', 'commission', 'commit', 'commodity', 'communicate', 'community',
        'compatible', 'compensate', 'compile', 'complement', 'complex',
        'component', 'comprehensive', 'comprise', 'compromise', 'compute',
        'conceive', 'concentrate', 'concept', 'conclude', 'concurrent',
        'conduct', 'confer', 'configurate', 'confine', 'confirm', 'conflict',
        'conform', 'consent', 'consequence', 'considerable', 'consist',
        'constant', 'constitute', 'constrain', 'construct', 'consult',
        'consume', 'contact', 'contain', 'contemporary', 'context',
        'contract', 'contradict', 'contribute', 'controversy', 'convention',
        'convert', 'convince', 'cooperate', 'coordinate', 'core', 'corporate',
        'correspond', 'couple', 'create', 'credit', 'criteria', 'crucial',
        'currency', 'cycle', 'data', 'debate', 'decade', 'decline',
        'deduce', 'define', 'definite', 'demonstrate', 'denote', 'deny',
        'depress', 'derive', 'design', 'despite', 'detect', 'deviate',
        'device', 'devote', 'dimension', 'diminish', 'discrete', 'discriminate',
        'displace', 'display', 'dispose', 'distinct', 'distort', 'distribute',
        'diverse', 'document', 'domain', 'domestic', 'dominate', 'draft',
        'duration', 'dynamic', 'economy', 'edit', 'element', 'eliminate',
        'emerge', 'emphasis', 'empirical', 'enable', 'encounter', 'enhance',
        'enormous', 'ensure', 'entity', 'environment', 'equate', 'equip',
        'equivalent', 'erode', 'error', 'establish', 'estimate', 'evaluate',
        'eventual', 'evident', 'evolve', 'exceed', 'exclude', 'exhibit',
        'expand', 'expertise', 'explicit', 'exploit', 'export', 'expose',
        'external', 'extract', 'facilitate', 'factor', 'feature', 'federal',
        'finance', 'flexible', 'fluctuate', 'focus', 'formula', 'forthcoming',
        'foundation', 'framework', 'function', 'fund', 'fundamental',
        'generate', 'genus', 'globe', 'grade', 'grant', 'guarantee',
        'hierarchy', 'hypothesis', 'identical', 'identify', 'ideology',
        'illustrate', 'impact', 'implement', 'implicate', 'implicit',
        'imply', 'impose', 'incentive', 'incidence', 'incline', 'incorporate',
        'indicate', 'individual', 'induce', 'inevitable', 'infrastructure',
        'inherent', 'inhibit', 'initial', 'initiate', 'inject', 'innovate',
        'input', 'insert', 'insight', 'inspect', 'instance', 'institute',
        'integrate', 'integrity', 'intelligence', 'intense', 'interact',
        'intervene', 'intrinsic', 'investigate', 'invoke', 'isolate',
        'issue', 'justify', 'label', 'labour', 'layer', 'lecture',
        'legal', 'legislate', 'levy', 'liberal', 'likewise', 'link',
        'locate', 'logic', 'maintain', 'major', 'manipulate', 'mature',
        'maximise', 'mechanism', 'mediate', 'method', 'migrate', 'military',
        'minimise', 'minor', 'modify', 'monitor', 'motive', 'mutual',
        'negate', 'network', 'neutral', 'nonetheless', 'norm', 'notion',
        'nuclear', 'objective', 'oblige', 'obtain', 'obvious', 'occupy',
        'occur', 'offset', 'ongoing', 'option', 'orient', 'outcome',
        'output', 'overall', 'overlap', 'overseas', 'panel', 'parallel',
        'parameter', 'participate', 'partner', 'passive', 'perceive',
        'period', 'persist', 'perspective', 'phase', 'phenomenon',
        'philosophy', 'plus', 'policy', 'portion', 'pose', 'positive',
        'potential', 'practitioner', 'precede', 'precise', 'predict',
        'predominant', 'preliminary', 'presume', 'previous', 'primary',
        'principal', 'prior', 'priority', 'proceed', 'process', 'professional',
        'prohibit', 'project', 'promote', 'proportion', 'prospect',
        'protocol', 'psuchology', 'pursue', 'qualitative', 'quote',
        'radical', 'random', 'range', 'ratio', 'rational', 'react',
        'recover', 'refine', 'regime', 'region', 'register', 'regulate',
        'reinforce', 'reject', 'relevant', 'reluctance', 'rely',
        'remove', 'require', 'research', 'reside', 'resolve', 'resource',
        'respond', 'restore', 'restrict', 'retain', 'reveal', 'revenue',
        'reverse', 'revise', 'revolution', 'rigid', 'role', 'route',
        'scenario', 'schedule', 'scheme', 'scope', 'section', 'sector',
        'secure', 'seek', 'select', 'sequence', 'series', 'shift',
        'significant', 'similar', 'simulate', 'site', 'sole', 'somewhat',
        'source', 'specific', 'specify', 'sphere', 'stable', 'statistic',
        'status', 'stimulus', 'strategy', 'stress', 'structure', 'subordinate',
        'subsequent', 'subsidy', 'substitute', 'successor', 'sufficient',
        'sum', 'summary', 'supplement', 'survey', 'survive', 'suspend',
        'sustain', 'symbol', 'target', 'task', 'team', 'technical',
        'technique', 'technology', 'temporary', 'tense', 'terminate',
        'text', 'theme', 'theory', 'thereby', 'thesis', 'topic',
        'trace', 'tradition', 'transfer', 'transform', 'transit',
        'transport', 'trend', 'trigger', 'ultimate', 'undergo',
        'underlie', 'undertake', 'uniform', 'unify', 'unique',
        'utilise', 'valid', 'vary', 'vehicle', 'version', 'via',
        'violate', 'virtual', 'visible', 'vision', 'volume', 'voluntary',
        'welfare', 'whereas', 'whereby', 'widespread',
    }
    return awl_words


# ============ 分析器核心 ============

class WhiteboxAnalyzer:
    """白盒分析器"""

    # 连接词分类表（多语言）
    CONNECTIVES = {
        'en': {
            'addition': ['moreover', 'furthermore', 'in addition', 'besides', 'also', 'additionally'],
            'contrast': ['however', 'nevertheless', 'on the other hand', 'in contrast', 'although', 'though', 'whereas', 'despite', 'nonetheless'],
            'cause': ['therefore', 'thus', 'consequently', 'as a result', 'hence', 'because', 'since', 'due to'],
            'example': ['for example', 'for instance', 'such as', 'specifically', 'namely', 'in particular'],
            'sequence': ['first', 'second', 'third', 'finally', 'next', 'then', 'subsequently', 'firstly', 'secondly'],
            'summary': ['in conclusion', 'to summarize', 'in summary', 'overall', 'in short', 'to sum up'],
        },
        'ja': {
            'addition': ['さらに', 'また', 'それに', '加えて', 'そして'],
            'contrast': ['しかし', 'だが', 'ところが', '一方', 'けれども', 'とはいえ', 'にもかかわらず'],
            'cause': ['したがって', 'そのため', 'だから', 'なぜなら', 'ので', 'ゆえに'],
            'example': ['例えば', '具体的に', 'すなわち', 'たとえば'],
            'sequence': ['まず', '次に', 'そして', '最後に', '第一に', '第二に'],
            'summary': ['要するに', 'まとめると', '結局', 'つまり', '以上のように'],
        },
        'fr': {
            'addition': ['de plus', 'en outre', 'par ailleurs', 'également', 'aussi'],
            'contrast': ['cependant', 'toutefois', 'en revanche', 'néanmoins', 'pourtant', 'bien que'],
            'cause': ['donc', 'par conséquent', 'ainsi', 'c\'est pourquoi', 'car', 'puisque'],
            'example': ['par exemple', 'notamment', 'en particulier', 'à savoir'],
            'sequence': ['premièrement', 'deuxièmement', 'ensuite', 'puis', 'enfin'],
            'summary': ['en conclusion', 'pour résumer', 'en somme', 'bref'],
        },
        'de': {
            'addition': ['außerdem', 'zudem', 'darüber hinaus', 'auch', 'ferner'],
            'contrast': ['jedoch', 'allerdings', 'hingegen', 'dennoch', 'obwohl', 'trotzdem'],
            'cause': ['daher', 'deshalb', 'folglich', 'also', 'weil', 'da'],
            'example': ['zum Beispiel', 'insbesondere', 'nämlich', 'etwa'],
            'sequence': ['erstens', 'zweitens', 'drittens', 'zunächst', 'anschließend', 'schließlich'],
            'summary': ['zusammenfassend', 'abschließend', 'kurz gesagt', 'im Großen und Ganzen'],
        },
        'es': {
            'addition': ['además', 'también', 'asimismo', 'por otra parte'],
            'contrast': ['sin embargo', 'no obstante', 'por el contrario', 'aunque', 'a pesar de'],
            'cause': ['por lo tanto', 'así que', 'por consiguiente', 'porque', 'ya que'],
            'example': ['por ejemplo', 'en concreto', 'específicamente', 'es decir'],
            'sequence': ['primero', 'segundo', 'luego', 'después', 'finalmente', 'por último'],
            'summary': ['en conclusión', 'en resumen', 'en suma', 'para concluir'],
        },
        'ko': {
            'addition': ['또한', '그리고', '게다가', '더 나아가'],
            'contrast': ['그러나', '하지만', '반면에', '그럼에도', '오히려'],
            'cause': ['그래서', '따라서', '그러므로', '왜냐하면', '때문에'],
            'example': ['예를 들면', '구체적으로', '곧'],
            'sequence': ['첫째', '둘째', '셋째', '먼저', '다음으로', '마지막으로'],
            'summary': ['결론적으로', '요약하면', '정리하면'],
        },
    }

    # CEFR等级排序
    LEVEL_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
    LEVEL_NAMES = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2"}

    def __init__(self):
        self.cefr_vocab = _load_cefr_wordlist()
        self.awl_vocab = _load_awl_wordlist()
        self.jlpt_vocab = _load_jlpt_wordlist()
        self.topik_vocab = _load_topik_wordlist()
        self._language_detector = None
        self._tokenizers = {}

    def _get_language_detector(self):
        if self._language_detector is None:
            from app.services.analysis.language_detector import LanguageDetector
            self._language_detector = LanguageDetector()
        return self._language_detector

    def _get_tokenizer(self, language: str):
        if language not in self._tokenizers:
            from app.services.analysis.multilingual_tokenizer import get_tokenizer
            self._tokenizers[language] = get_tokenizer(language)
        return self._tokenizers[language]

    def analyze(self, text: str, student_level: str = "B1", language: Optional[str] = None) -> WhiteboxAnalysisResult:
        """执行白盒分析（支持多语言）"""
        # 语言检测
        detector = self._get_language_detector()
        if language:
            from app.services.analysis.language_detector import LANG_NAMES
            lang_info = {"language": language, "confidence": 1.0, "name": LANG_NAMES.get(language, language)}
        else:
            lang_info = detector.detect(text)
        lang = lang_info["language"]
        lang_name = lang_info.get("name", lang)

        # 获取语言专用分词器
        tokenizer = self._get_tokenizer(lang)

        # 是否为 CEFR 支持的欧洲语言
        is_european = lang in ("en", "fr", "de", "es", "it", "pt")

        vocab = self._analyze_vocabulary(text, student_level, tokenizer, is_european, lang)
        syntax = self._analyze_syntax(text, tokenizer, lang)
        discourse = self._analyze_discourse(text, tokenizer, lang)

        # 教学要点识别（依赖 discourse 结果）
        discourse.teaching_points = self._identify_teaching_points(vocab, syntax, discourse, lang)

        # 文化元素识别
        cultural_elements = self._analyze_cultural_elements(text, lang)

        text_level = self._estimate_text_level(vocab, syntax, is_european)
        learner_gap = self._analyze_learner_gap(text_level, student_level)
        tags = self._generate_tags(vocab, syntax, discourse, learner_gap)
        tips = self._generate_teaching_tips(vocab, syntax, learner_gap, tags, lang)
        insights = self._generate_teaching_insights(vocab, syntax, discourse, learner_gap, tags, lang)
        tag_labels = {tag: TAG_DISPLAY.get(tag, tag) for tag in tags}

        return WhiteboxAnalysisResult(
            vocabulary=vocab,
            syntax=syntax,
            discourse=discourse,
            learner_gap=learner_gap,
            enhancement_tags=tags,
            teaching_tips=tips,
            tag_labels=tag_labels,
            teaching_insights=insights,
            cultural_elements=cultural_elements,
            text_level=text_level,
            language=lang,
            language_name=lang_name,
        )

    def _tokenize(self, text: str, tokenizer=None) -> List[str]:
        """分词（委托给语言专用分词器）"""
        if tokenizer:
            return tokenizer.tokenize(text)
        return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())

    def _lemmatize(self, word: str, tokenizer=None) -> str:
        """词形还原（委托给语言专用分词器）"""
        if tokenizer:
            return tokenizer.lemmatize(word)
        w = word.lower().strip()
        if len(w) <= 3:
            return w
        # 先查词表，命中则直接返回
        if w in self.cefr_vocab:
            return w

        # 辅助：尝试候选词是否在词表中
        def _try(candidates):
            for c in candidates:
                if c in self.cefr_vocab:
                    return c
            return None

        # 1) -ies → -y: opportunities→opportunity, studies→study
        if w.endswith('ies') and len(w) > 4:
            r = _try([w[:-3] + 'y'])
            if r: return r

        # 1b) -es 结尾: approaches→approach, boxes→box
        if w.endswith('es') and len(w) > 4:
            stem = w[:-2]
            r = _try([stem, stem + 'e'])
            if r: return r

        # 2) -ized/-ised 结尾: personalized→personalize, memorized→memorize
        if (w.endswith('ized') or w.endswith('ised')) and len(w) > 6:
            stem = w[:-4]
            r = _try([stem + 'ize', stem + 'ise', stem])
            if r: return r

        # 2b) -ed 结尾: evolved→evolve, stopped→stop, assessed→assess
        if w.endswith('ed') and len(w) > 4:
            stem = w[:-2]
            r = _try([stem, stem + 'e', w[:-1]])  # stopped→stop, assessed→assess
            if r: return r
            # doubled consonant: running→run
            if len(stem) >= 2 and stem[-1] == stem[-2]:
                r = _try([stem[:-1]])
                if r: return r

        # 3) -ing 结尾: learning→learn, running→run
        if w.endswith('ing') and len(w) > 5:
            stem = w[:-3]
            r = _try([stem, stem + 'e', stem + 'y'])
            if r: return r
            # doubled consonant: running→run
            if len(stem) >= 2 and stem[-1] == stem[-2]:
                r = _try([stem[:-1]])
                if r: return r

        # 3b) -ization/-isation → -ize/-ise: memorization→memorize
        if (w.endswith('ization') or w.endswith('isation')) and len(w) > 9:
            stem = w[:-7]
            r = _try([stem + 'ize', stem + 'ise', stem])
            if r: return r

        # 4) -ation → -ate: translation→translate, integration→integrate
        if w.endswith('ation') and len(w) > 7:
            stem = w[:-5]
            r = _try([stem + 'ate', stem + 'ize', stem + 'ise', stem])
            if r: return r

        # 5) -ment: assessment→assess
        if w.endswith('ment') and len(w) > 6:
            stem = w[:-4]
            r = _try([stem, stem + 'e'])
            if r: return r

        # 6) -ness: meaningful→meaning
        if w.endswith('ness') and len(w) > 6:
            stem = w[:-4]
            r = _try([stem, stem + 'e'])
            if r: return r

        # 7) -tion: education→educate
        if w.endswith('tion') and len(w) > 6:
            stem = w[:-4]
            r = _try([stem + 'te', stem + 'e', stem])
            if r: return r

        # 8) -ity: competence→competent (not direct, but try)
        if w.endswith('ity') and len(w) > 5:
            stem = w[:-3]
            r = _try([stem, stem + 'e', stem + 'ous'])
            if r: return r

        # 9) -ous: various→various (usually same)
        if w.endswith('ous') and len(w) > 5:
            r = _try([w])
            if r: return r

        # 10) -ive: communicative→communicate
        if w.endswith('ive') and len(w) > 5:
            stem = w[:-3]
            r = _try([stem + 'e', stem])
            if r: return r

        # 11) -ful, -less, -ly, -er, -s: 简单剥离
        for suffix in ['ful', 'less', 'ly', 'er', 's']:
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                stem = w[:-len(suffix)]
                r = _try([stem, stem + 'e'])
                if r: return r

        return w

    def _split_sentences(self, text: str, tokenizer=None) -> List[str]:
        """分句（委托给语言专用分词器）"""
        if tokenizer:
            return tokenizer.split_sentences(text)
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def _analyze_vocabulary(self, text: str, student_level: str = "B1", tokenizer=None, is_european: bool = True, lang: str = "en") -> VocabAnalysis:
        """词汇分析（支持多语言）"""
        raw_words = self._tokenize(text, tokenizer)
        # 词形还原：inflected → base form
        words = [self._lemmatize(w, tokenizer) for w in raw_words]
        total = len(words)
        unique = len(set(words))
        word_counts = Counter(words)

        # CEFR分布 - 按大类分组
        cefr_dist = {"A1-A2": 0, "B1-B2": 0, "C1-C2": 0, "未分级": 0}
        difficult_words: List[DifficultWord] = []

        # 选择词表：日语用JLPT，韩语用TOPIK，欧洲语言用CEFR
        if lang == "ja" and self.jlpt_vocab:
            vocab_map = self.jlpt_vocab
            level_groups = {
                "A1-A2": ("N5", "N4"),
                "B1-B2": ("N3",),
                "C1-C2": ("N2", "N1"),
            }
        elif lang == "ko" and self.topik_vocab:
            vocab_map = self.topik_vocab
            level_groups = {
                "A1-A2": ("TOPIK1", "TOPIK2"),
                "B1-B2": ("TOPIK3", "TOPIK4"),
                "C1-C2": ("TOPIK5",),
            }
        elif is_european:
            vocab_map = self.cefr_vocab
            level_groups = {
                "A1-A2": ("A1", "A2"),
                "B1-B2": ("B1", "B2"),
                "C1-C2": ("C1", "C2"),
            }
        else:
            vocab_map = None
            level_groups = {}

        for word, count in word_counts.items():
            if vocab_map:
                level = vocab_map.get(word)
                if level is None:
                    cefr_dist["未分级"] += count
                    if count >= 1 and not self._is_stopword(word, tokenizer):
                        difficult_words.append(DifficultWord(
                            word=word, level="unknown", count=count, in_awl=word in self.awl_vocab if lang == "en" else False
                        ))
                else:
                    grouped = False
                    for group_name, group_levels in level_groups.items():
                        if level in group_levels:
                            cefr_dist[group_name] += count
                            grouped = True
                            # C1-C2级别视为难词
                            if group_name == "C1-C2":
                                difficult_words.append(DifficultWord(
                                    word=word, level=level, count=count, in_awl=word in self.awl_vocab if lang == "en" else False
                                ))
                            break
                    if not grouped:
                        cefr_dist["未分级"] += count
            else:
                # 无词表语言：所有词归入"未分级"，高频非停用词视为难词
                cefr_dist["未分级"] += count
                if count >= 2 and not self._is_stopword(word, tokenizer):
                    difficult_words.append(DifficultWord(
                        word=word, level="unknown", count=count, in_awl=False
                    ))

        # B2级别如果学生水平低于B2，也加入超纲词（仅欧洲语言）
        if is_european:
            student_rank = self.LEVEL_ORDER.get(student_level, 3)
            for word, count in word_counts.items():
                level = self.cefr_vocab.get(word)
                if level == "B2" and student_rank < 4:
                    if not any(d.word == word for d in difficult_words):
                        difficult_words.append(DifficultWord(
                            word=word, level="B2", count=count, in_awl=word in self.awl_vocab
                        ))

        # 按出现次数降序排列
        difficult_words.sort(key=lambda d: d.count, reverse=True)
        # 限制列表长度
        difficult_words = difficult_words[:30]

        # AWL统计（仅英语，AWL 是英语学术词表）
        awl_count = sum(1 for w in words if w in self.awl_vocab) if lang == "en" else 0
        awl_ratio = awl_count / total if total > 0 else 0.0

        # 词汇丰富度 (TTR)
        ttr = unique / total if total > 0 else 0.0

        return VocabAnalysis(
            total_words=total,
            unique_words=unique,
            cefr_distribution=cefr_dist,
            awl_count=awl_count,
            awl_ratio=round(awl_ratio, 4),
            difficult_words=difficult_words,
            vocabulary_richness=round(ttr, 4),
        )

    def _analyze_syntax(self, text: str, tokenizer=None, lang: str = "en") -> SyntaxAnalysis:
        """句法分析（支持多语言）"""
        sentences = self._split_sentences(text, tokenizer)
        words = self._tokenize(text, tokenizer)
        total_sentences = len(sentences)
        total_words = len(words)

        # 计算每句词数
        sentence_lengths = []
        for s in sentences:
            sw = self._tokenize(s, tokenizer)
            sentence_lengths.append(len(sw))

        avg_len = sum(sentence_lengths) / total_sentences if total_sentences > 0 else 0

        # 最长句
        max_idx = sentence_lengths.index(max(sentence_lengths)) if sentence_lengths else 0
        max_len = max(sentence_lengths) if sentence_lengths else 0
        max_preview = sentences[max_idx][:100] if sentences else ""

        # 长句统计
        long_count = sum(1 for l in sentence_lengths if l > 30)
        very_long_count = sum(1 for l in sentence_lengths if l > 40)

        # Flesch Reading Ease（仅英语有效，其他语言用平均句长估算）
        if lang == "en":
            total_syllables = sum(self._count_syllables(w, tokenizer) for w in words)
            if total_sentences > 0 and total_words > 0:
                fre = 206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
            else:
                fre = 0.0
        else:
            # 非英语：用平均句长粗略估算可读性（0-100，越高越易读）
            if avg_len <= 10:
                fre = 80.0
            elif avg_len <= 20:
                fre = 60.0
            elif avg_len <= 30:
                fre = 40.0
            elif avg_len <= 40:
                fre = 20.0
            else:
                fre = 10.0

        return SyntaxAnalysis(
            total_sentences=total_sentences,
            avg_sentence_length=round(avg_len, 1),
            max_sentence=LongestSentence(preview=max_preview, word_count=max_len, index=max_idx),
            long_sentences_count=long_count,
            very_long_sentences_count=very_long_count,
            flesch_reading_ease=round(fre, 1),
        )

    def _analyze_discourse(self, text: str, tokenizer=None, lang: str = "en") -> DiscourseAnalysis:
        """语篇分析（支持多语言）"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        words = self._tokenize(text, tokenizer)
        total_words = len(words)

        # 连接词密度（使用语言专用连接词表）
        connective_count = 0
        text_lower = text.lower()
        lang_connectives = self.CONNECTIVES.get(lang, self.CONNECTIVES.get("en", {}))
        for category, markers in lang_connectives.items():
            for marker in markers:
                connective_count += len(re.findall(r'\b' + re.escape(marker) + r'\b', text_lower))

        connective_density = (connective_count / total_words * 100) if total_words > 0 else 0

        # 段落功能标记
        para_functions = []
        for i, para in enumerate(paragraphs):
            func = self._classify_paragraph(para, i, len(paragraphs))
            para_functions.append(ParagraphFunction(
                index=i,
                function=func,
                preview=para[:50].replace('\n', ' '),
            ))

        # 体裁提示
        genre = self._detect_genre(text_lower)

        # 文本结构分析
        text_structure = self._analyze_text_structure(text, paragraphs, lang)

        return DiscourseAnalysis(
            paragraph_count=len(paragraphs),
            connective_density=round(connective_density, 2),
            paragraph_functions=para_functions,
            genre_hint=genre,
            text_structure=text_structure,
        )

    def _classify_paragraph(self, text: str, index: int, total: int) -> str:
        """判断段落功能"""
        text_lower = text.lower()
        first_words = ' '.join(text_lower.split()[:10])

        # 示例段落（优先检测，不论位置）
        if any(w in first_words for w in ['for example', 'for instance', 'such as', 'consider', 'case study']):
            return "example"

        # 过渡段落
        if any(w in first_words for w in ['however', 'nevertheless', 'on the other hand', 'in contrast']):
            return "transition"

        # 首段检测
        if index == 0:
            return "introduction"

        # 末段检测
        if index == total - 1:
            return "conclusion"

        return "body"

    def _detect_genre(self, text_lower: str) -> str:
        """检测体裁"""
        genre_scores = {
            "argumentative": 0,
            "expository": 0,
            "narrative": 0,
            "scientific": 0,
        }

        arg_markers = ['argue', 'claim', 'believe', 'opinion', 'however', 'although', 'despite', 'nevertheless', 'conversely']
        exp_markers = ['explain', 'describe', 'define', 'illustrate', 'for example', 'for instance', 'first', 'second', 'third']
        nar_markers = ['once upon', 'one day', 'suddenly', 'then', 'next', 'finally', 'meanwhile', 'later']
        sci_markers = ['hypothesis', 'experiment', 'theory', 'evidence', 'data', 'results', 'method', 'analysis', 'research']

        def _count_word(text: str, marker: str) -> int:
            """使用词边界匹配，避免子串误匹配"""
            return len(re.findall(r'\b' + re.escape(marker) + r'\b', text))

        for m in arg_markers: genre_scores["argumentative"] += _count_word(text_lower, m)
        for m in exp_markers: genre_scores["expository"] += _count_word(text_lower, m)
        for m in nar_markers: genre_scores["narrative"] += _count_word(text_lower, m)
        for m in sci_markers: genre_scores["scientific"] += _count_word(text_lower, m)

        best = max(genre_scores, key=genre_scores.get)
        if genre_scores[best] == 0:
            return "通用"
        return best

    def _analyze_text_structure(self, text: str, paragraphs: List[str], lang: str = "en") -> str:
        """分析文本结构（如问题-解决、因果、对比、时间顺序等）"""
        text_lower = text.lower()

        structure_markers = {
            "问题-解决": {
                "en": ["problem", "solution", "solve", "issue", "resolve", "address", "challenge", "overcome"],
                "ja": ["問題", "解決", "課題", "克服"],
                "fr": ["problème", "solution", "résoudre", "défi"],
                "de": ["Problem", "Lösung", "lösen", "Herausforderung"],
                "es": ["problema", "solución", "resolver", "desafío"],
                "ko": ["문제", "해결", "과제", "극복"],
            },
            "因果关系": {
                "en": ["because", "therefore", "consequently", "as a result", "lead to", "cause", "effect", "due to"],
                "ja": ["そのため", "だから", "原因", "結果", "理由"],
                "fr": ["parce que", "donc", "par conséquent", "à cause de", "effet"],
                "de": ["weil", "deshalb", "daher", "Ursache", "Wirkung", "Folge"],
                "es": ["porque", "por lo tanto", "como resultado", "causa", "efecto"],
                "ko": ["때문에", "그래서", "따라서", "원인", "결과"],
            },
            "对比-比较": {
                "en": ["however", "in contrast", "on the other hand", "similarly", "whereas", "unlike", "compare", "differ"],
                "ja": ["しかし", "一方", "比較", "違い", "対照"],
                "fr": ["cependant", "en revanche", "par contre", "contrairement", "comparer"],
                "de": ["jedoch", "hingegen", "im Gegensatz", "vergleichen", "unterscheiden"],
                "es": ["sin embargo", "en cambio", "por el contrario", "comparar", "diferir"],
                "ko": ["하지만", "반면", "비교", "다르다", "대조"],
            },
            "时间顺序": {
                "en": ["first", "then", "next", "finally", "before", "after", "while", "during", "subsequently"],
                "ja": ["最初", "次に", "最後", "その後", "前に", "後で"],
                "fr": ["d'abord", "ensuite", "enfin", "avant", "après", "pendant"],
                "de": ["zuerst", "dann", "schließlich", "vor", "nach", "während"],
                "es": ["primero", "luego", "finalmente", "antes", "después", "mientras"],
                "ko": ["먼저", "그 다음", "마지막", "전에", "후에", "동안"],
            },
        }

        # CJK语言使用子串匹配（无词边界），欧洲语言使用词边界匹配
        is_cjk = lang in ("ja", "ko", "zh")

        scores = {}
        for structure, lang_markers in structure_markers.items():
            markers = lang_markers.get(lang, lang_markers.get("en", []))
            if is_cjk:
                score = sum(text_lower.count(m) for m in markers)
            else:
                score = sum(len(re.findall(r'\b' + re.escape(m) + r'\b', text_lower)) for m in markers)
            scores[structure] = score

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "线性叙述"
        return best

    def _identify_teaching_points(
        self, vocab: VocabAnalysis, syntax: SyntaxAnalysis, discourse: DiscourseAnalysis, lang: str = "en"
    ) -> List[str]:
        """基于分析结果识别教学要点"""
        points = []

        # 词汇教学要点
        if vocab.difficult_words:
            top_words = [d.word for d in vocab.difficult_words[:5]]
            points.append(f"重点词汇教学：{', '.join(top_words)}")

        if lang == "en" and vocab.awl_ratio > 0.05:
            points.append(f"学术词汇渗透（AWL占比{vocab.awl_ratio*100:.1f}%），建议结合学科语境讲解")

        # 句法教学要点
        if syntax.long_sentences_count > 3:
            points.append(f"长句分析训练：课文含{syntax.long_sentences_count}个长句（>30词），建议拆分练习")

        if syntax.avg_sentence_length > 25:
            points.append("句法复杂度较高，建议进行句子结构图解")

        # 语篇教学要点
        if discourse.connective_density > 3:
            points.append("衔接词使用密集，适合进行语篇衔接分析教学")

        if discourse.genre_hint in ("argumentative", "scientific"):
            points.append(f"体裁为{discourse.genre_hint}，建议引入体裁分析框架（如CARS模型）")

        # 语篇结构教学
        if discourse.text_structure:
            points.append(f"文本结构为「{discourse.text_structure}」，可引导学生识别篇章组织模式")

        return points

    def _analyze_cultural_elements(self, text: str, lang: str = "en") -> List[CulturalElement]:
        """识别文本中的文化元素"""
        elements = []
        text_lower = text.lower()

        # 各语言的文化关键词库
        cultural_markers = {
            "en": {
                "习俗": ["christmas", "thanksgiving", "halloween", "easter", "wedding", "funeral", "birthday", "custom", "tradition"],
                "历史": ["war", "revolution", "independence", "colonial", "ancient", "medieval", "renaissance", "empire"],
                "社会": ["democracy", "equality", "freedom", "justice", "rights", "citizen", "government", "law"],
                "价值观": ["individualism", "collectivism", "honesty", "respect", "responsibility", "courage", "kindness"],
                "地理": ["continent", "ocean", "mountain", "river", "climate", "hemisphere", "tropical", "arctic"],
                "文学": ["novel", "poem", "drama", "fiction", "metaphor", "symbolism", "narrative", "protagonist"],
            },
            "ja": {
                "习俗": ["お正月", "花見", "お盆", "成人式", "入学式", "卒業式", "七五三", "初詣"],
                "历史": ["幕府", "明治", "大正", "昭和", "平成", "令和", "武士", "侍"],
                "社会": ["日本社会", "集団", "和", "謙遜", "礼儀", "マナー", "世間"],
                "价值观": ["武士道", "義理", "人情", "恩", "侘び", "寂び", "物の哀れ"],
                "地理": ["富士山", "京都", "東京", "北海道", "沖縄", "関東", "関西"],
                "文学": ["俳句", "川柳", "物語", "源氏", "枕草子", "徒然草", "万葉"],
            },
            "fr": {
                "习俗": ["Noël", "Pâques", "Bastille", "galette", "bûche", "foie gras", "champagne"],
                "历史": ["Révolution", "Napoléon", "monarchie", "république", "guerre", "siècle"],
                "社会": ["laïcité", "solidarité", "égalité", "fraternité", "citoyen", "démocratie"],
                "价值观": ["liberté", "égalité", "fraternité", "culture", "art de vivre", "savoir-vivre"],
                "地理": ["Paris", "Provence", "Alpes", "Méditerranée", "Atlantique", "Loire"],
                "文学": ["roman", "poésie", "théâtre", "essai", "Proust", "Hugo", "Camus"],
            },
            "de": {
                "习俗": ["Weihnachten", "Ostern", "Oktoberfest", "Karneval", "Silvester", "Advent"],
                "历史": ["Mauer", "Wiedervereinigung", "Kaiser", "Weimarer", "Drittes Reich", "Nachkrieg"],
                "社会": ["Sozialstaat", "Demokratie", "Grundgesetz", "Bundesrepublik", "Europa"],
                "价值观": ["Pflicht", "Ordnung", "Gründlichkeit", "Pünktlichkeit", "Bildung"],
                "地理": ["Rhein", "Donau", "Bayern", "Berlin", "Hamburg", "Schwarzwald"],
                "文学": ["Gedicht", "Drama", "Roman", "Goethe", "Schiller", "Kafka", "Thomas Mann"],
            },
            "es": {
                "习俗": ["Navidad", "Semana Santa", "toros", "flamenco", "fiesta", "siesta", "tapas"],
                "历史": ["conquista", "imperio", "república", "guerra civil", "franquismo", "democracia"],
                "社会": ["familia", "comunidad", "religión", "tradición", "cultura"],
                "价值观": ["honor", "familia", "religión", "pasión", "orgullo", "solidaridad"],
                "地理": ["Madrid", "Barcelona", "Andalucía", "Cataluña", "Mediterráneo", "Atlántico"],
                "文学": ["novela", "poesía", "teatro", "Cervantes", "García Márquez", "Borges"],
            },
            "ko": {
                "习俗": ["설날", "추석", "한가위", "대보름", "단오", "칠석", "혼례", "장례"],
                "历史": ["조선", "고려", "삼국", "일제", "해방", "분단", "민주화"],
                "社会": ["한국社会", "유교", "가족", "효", "체면", "눈치", "정"],
                "价值观": ["효도", "예의", "겸손", "근면", "집단주의", "한", "흥"],
                "地理": ["한강", "백두산", "제주", "서울", "부산", "경주", "전주"],
                "文学": ["시조", "가사", "소설", "판소리", "춘향전", "홍길동전"],
            },
        }

        markers = cultural_markers.get(lang, cultural_markers.get("en", {}))

        for category, keywords in markers.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # 提取上下文（关键词前后50字符）
                    idx = text_lower.find(keyword.lower())
                    start = max(0, idx - 30)
                    end = min(len(text), idx + len(keyword) + 30)
                    context = text[start:end].replace('\n', ' ').strip()

                    elements.append(CulturalElement(
                        category=category,
                        keyword=keyword,
                        context=f"...{context}...",
                        explanation=f"涉及{category}元素「{keyword}」，建议补充文化背景知识",
                    ))

        # 去重（同一关键词只保留第一个）
        seen = set()
        unique_elements = []
        for e in elements:
            if e.keyword not in seen:
                seen.add(e.keyword)
                unique_elements.append(e)

        return unique_elements[:10]  # 最多返回10个

    def _estimate_text_level(self, vocab: VocabAnalysis, syntax: SyntaxAnalysis, is_european: bool = True) -> str:
        """综合估计课文CEFR等级（非欧洲语言仅基于句法估算）"""
        score = 0.0

        # 难词比例（非欧洲语言在词汇和AWL两个维度都用到，提前计算）
        difficulty_ratio = len(vocab.difficult_words) / max(vocab.total_words, 1)

        if is_european:
            # 词汇维度 (权重 0.5)
            dist = vocab.cefr_distribution
            total = vocab.total_words
            if total > 0:
                a1a2_ratio = dist.get("A1-A2", 0) / total
                b1b2_ratio = dist.get("B1-B2", 0) / total
                c1c2_ratio = dist.get("C1-C2", 0) / total
                unknown_ratio = dist.get("未分级", 0) / total
                vocab_score = (a1a2_ratio * 1.5 + b1b2_ratio * 3.5 +
                              c1c2_ratio * 5.5 + unknown_ratio * 3.0)
                score += vocab_score * 0.5
        else:
            # 非欧洲语言：用词汇丰富度和难词比例估算
            richness_score = min(vocab.vocabulary_richness * 5, 5.0)
            difficulty_score = min(difficulty_ratio * 20, 5.0)
            score += (richness_score * 0.3 + difficulty_score * 0.7)

        # 句法维度 (权重 0.3)
        avg_len = syntax.avg_sentence_length
        if avg_len < 10:
            syn_score = 1.0
        elif avg_len < 12:
            syn_score = 1.5
        elif avg_len < 14:
            syn_score = 2.0
        elif avg_len < 16:
            syn_score = 2.5
        elif avg_len < 18:
            syn_score = 3.0
        elif avg_len < 20:
            syn_score = 3.5
        elif avg_len < 25:
            syn_score = 4.5
        elif avg_len < 30:
            syn_score = 5.5
        else:
            syn_score = 6.0
        score += syn_score * 0.3

        # AWL维度 (权重 0.2，仅欧洲语言)
        if is_european:
            awl_score = min(vocab.awl_ratio * 10, 6.0)
            score += awl_score * 0.2
        else:
            # 非欧洲语言：用难词比例替代 AWL（复用前面已计算的 difficulty_ratio）
            score += min(difficulty_ratio * 10, 6.0) * 0.2

        # 映射到CEFR等级
        if score < 1.5:
            return "A1"
        elif score < 2.0:
            return "A2"
        elif score < 2.8:
            return "B1"
        elif score < 3.8:
            return "B2"
        elif score < 4.8:
            return "C1"
        else:
            return "C2"

    def _analyze_learner_gap(self, text_level: str, student_level: str) -> LearnerGap:
        """分析学习者与课文的差距"""
        text_rank = self.LEVEL_ORDER.get(text_level, 3)
        student_rank = self.LEVEL_ORDER.get(student_level, 3)
        diff = text_rank - student_rank

        if diff <= 0:
            gap = "i+0"
            desc = f"课文难度（{text_level}）等于或低于学生水平（{student_level}），适合自主阅读"
        elif diff == 1:
            gap = "i+1"
            desc = f"课文难度（{text_level}）略高于学生水平（{student_level}），处于最近发展区，适合引导学习"
        else:
            gap = "i+2"
            desc = f"课文难度（{text_level}）显著高于学生水平（{student_level}），需要大量支架支持"

        return LearnerGap(
            text_level=text_level,
            student_level=student_level,
            gap=gap,
            gap_description=desc,
        )

    def _generate_tags(self, vocab: VocabAnalysis, syntax: SyntaxAnalysis,
                       discourse: DiscourseAnalysis, gap: LearnerGap) -> List[str]:
        """生成增强标签"""
        tags = []

        # 词汇标签
        if vocab.awl_ratio > 0.15:
            tags.append("high_academic_vocab")
        if vocab.awl_ratio > 0.25:
            tags.append("very_high_academic_vocab")

        difficult_count = len([d for d in vocab.difficult_words if d.level in ("C1", "C2", "unknown")])
        if difficult_count > 10:
            tags.append("many_difficult_words")
        elif difficult_count > 5:
            tags.append("moderate_difficult_words")

        # 句法标签
        if syntax.max_sentence.word_count > 40:
            tags.append("very_long_sentences")
        elif syntax.max_sentence.word_count > 30:
            tags.append("long_sentences_present")

        if syntax.long_sentences_count > 5:
            tags.append("dense_complex_syntax")

        if syntax.flesch_reading_ease < 30:
            tags.append("very_difficult_readability")
        elif syntax.flesch_reading_ease < 50:
            tags.append("difficult_readability")

        # 语篇标签
        if discourse.connective_density > 3.0:
            tags.append("high_connective_density")
        if discourse.genre_hint == "argumentative":
            tags.append("argumentative_text")
        elif discourse.genre_hint == "scientific":
            tags.append("scientific_text")

        # 学习者差距标签
        if gap.gap == "i+2":
            tags.append("i_plus_2_risk")
        elif gap.gap == "i+1":
            tags.append("i_plus_1_optimal")

        # 词汇丰富度标签
        if vocab.vocabulary_richness > 0.7:
            tags.append("high_lexical_diversity")

        return tags

    def _generate_teaching_tips(self, vocab: VocabAnalysis, syntax: SyntaxAnalysis,
                                 gap: LearnerGap, tags: List[str], lang: str = "en") -> List[str]:
        """生成教学提示（支持多语言）"""
        tips = []
        lang_label = {"ja": "日语", "fr": "法语", "de": "德语", "es": "西班牙语", "ko": "韩语"}.get(lang, "")

        # 基于词汇分析的提示
        if lang == "en" and ("high_academic_vocab" in tags or "very_high_academic_vocab" in tags):
            tips.append(f"课文包含{vocab.awl_count}个学术词汇（占比{vocab.awl_ratio*100:.1f}%），建议课前发放词汇预习单")

        if len(vocab.difficult_words) > 10:
            top_words = [d.word for d in vocab.difficult_words[:5]]
            tips.append(f"超纲词较多（{len(vocab.difficult_words)}个），重点预教：{', '.join(top_words)}")
        elif len(vocab.difficult_words) > 5 and lang != "en":
            top_words = [d.word for d in vocab.difficult_words[:3]]
            tips.append(f"高频词中包含{len(vocab.difficult_words)}个可能的难点词，建议预教：{', '.join(top_words)}")

        # 基于句法分析的提示
        if "long_sentences_present" in tags or "very_long_sentences" in tags:
            tips.append(f"课文含{syntax.long_sentences_count}个长句（>30词），建议选取最长句做句法拆分练习")

        if lang == "en" and syntax.flesch_reading_ease < 40:
            tips.append("课文可读性较低，建议先进行段落大意匹配活动再精读")
        elif lang != "en" and syntax.avg_sentence_length > 25:
            tips.append(f"{lang_label}课文句子较长，建议先进行段落大意匹配活动再精读")

        # 基于学习者差距的提示
        if gap.gap == "i+2":
            tips.append("课文难度显著高于学生水平，建议提供双语词汇表和结构化阅读支架")
        elif gap.gap == "i+0":
            tips.append("课文难度适合学生水平，可侧重深层理解与批判性思维训练")

        # 基于语篇的提示
        if "argumentative_text" in tags:
            tips.append("课文为议论文体裁，适合设计论点-论据分析活动")

        if not tips:
            tips.append("课文难度适中，可按常规教学流程进行")

        return tips

    def _generate_teaching_insights(
        self, vocab: VocabAnalysis, syntax: SyntaxAnalysis,
        discourse: DiscourseAnalysis, gap: LearnerGap,
        tags: List[str], lang: str = "en"
    ) -> List[Dict[str, str]]:
        """生成结构化教学含义——将指标翻译为教师可理解的教学决策"""
        insights = []

        # 加载基准数据
        benchmarks = self._load_benchmarks()
        level_key = gap.student_level if gap.student_level in benchmarks else "B1"
        bm = benchmarks.get(level_key, benchmarks.get("B1", {}))

        # 1. AWL 学术词汇
        if lang == "en" and vocab.awl_ratio > 0.05:
            bm_awl = bm.get("awl_ratio", {"low": 0.03, "high": 0.08})
            if vocab.awl_ratio > bm_awl["high"]:
                insights.append({
                    "metric_name": "学术词汇占比",
                    "metric_value": f"{vocab.awl_ratio*100:.1f}%",
                    "teaching_implication": f"课文学术词汇密度高（{vocab.awl_ratio*100:.1f}%），高于同级教材典型值（{bm_awl['low']*100:.0f}-{bm_awl['high']*100:.0f}%），接近大学学术文本水平",
                    "suggested_action": "建议课前发放学术词汇预习单，标注词族和常见搭配",
                    "confidence": "high",
                })
            elif vocab.awl_ratio > bm_awl["low"]:
                insights.append({
                    "metric_name": "学术词汇占比",
                    "metric_value": f"{vocab.awl_ratio*100:.1f}%",
                    "teaching_implication": f"课文包含适量学术词汇（{vocab.awl_ratio*100:.1f}%），在同级教材典型范围内",
                    "suggested_action": "可在阅读过程中随文讲解学术词汇",
                    "confidence": "medium",
                })

        # 2. 词汇丰富度 TTR
        bm_ttr = bm.get("vocabulary_richness", {"low": 0.4, "high": 0.65})
        if vocab.vocabulary_richness < bm_ttr["low"]:
            insights.append({
                "metric_name": "词汇丰富度",
                "metric_value": f"{vocab.vocabulary_richness:.2f}",
                "teaching_implication": f"词汇重复率较高（TTR={vocab.vocabulary_richness:.2f}），作者有意识地复现关键词汇，有利于词汇习得",
                "suggested_action": "适合做词汇强化活动：阅读后设计填空、配对、造句练习",
                "confidence": "high",
            })
        elif vocab.vocabulary_richness > bm_ttr["high"]:
            insights.append({
                "metric_name": "词汇丰富度",
                "metric_value": f"{vocab.vocabulary_richness:.2f}",
                "teaching_implication": f"词汇多样性极高（TTR={vocab.vocabulary_richness:.2f}），学生可能遇到大量不重复的生词",
                "suggested_action": "建议提供词汇表或边读边查工具，降低认知负荷",
                "confidence": "high",
            })

        # 3. 平均句长
        bm_sl = bm.get("avg_sentence_length", {"low": 12, "high": 22})
        if syntax.avg_sentence_length > bm_sl["high"]:
            insights.append({
                "metric_name": "平均句长",
                "metric_value": f"{syntax.avg_sentence_length:.1f}词",
                "teaching_implication": f"句法复杂度高（平均{syntax.avg_sentence_length:.1f}词/句），高于同级教材典型值（{bm_sl['low']}-{bm_sl['high']}词），含多层从句或嵌套结构",
                "suggested_action": "建议选取2-3个典型长句做句法拆分练习，引导学生识别主句和从句",
                "confidence": "high",
            })
        elif syntax.avg_sentence_length < bm_sl["low"]:
            insights.append({
                "metric_name": "平均句长",
                "metric_value": f"{syntax.avg_sentence_length:.1f}词",
                "teaching_implication": f"句子较短（平均{syntax.avg_sentence_length:.1f}词/句），结构简单，适合基础水平学生",
                "suggested_action": "可侧重词汇和语篇层面的教学，句法层面压力较小",
                "confidence": "medium",
            })

        # 4. 可读性
        if lang == "en":
            bm_flesch = bm.get("flesch_reading_ease", {"low": 40, "high": 65})
            if syntax.flesch_reading_ease < bm_flesch["low"]:
                insights.append({
                    "metric_name": "可读性指数",
                    "metric_value": f"{syntax.flesch_reading_ease:.0f}",
                    "teaching_implication": f"可读性较低（Flesch={syntax.flesch_reading_ease:.0f}），文本对目标学生而言偏难",
                    "suggested_action": "建议先进行段落大意匹配活动再精读，降低认知负荷",
                    "confidence": "high",
                })

        # 5. 学习者差距
        if gap.gap == "i+2":
            insights.append({
                "metric_name": "学习者差距",
                "metric_value": "i+2（难度超标）",
                "teaching_implication": f"课文难度远超学生水平（{gap.text_level} vs {gap.student_level}），可能导致认知过载",
                "suggested_action": "建议降低任务复杂度：先做整体理解，再做细节分析；提供双语词汇表和结构化阅读支架",
                "confidence": "high",
            })
        elif gap.gap == "i+0":
            insights.append({
                "metric_name": "学习者差距",
                "metric_value": "i+0（水平匹配）",
                "teaching_implication": f"课文难度与学生水平匹配（{gap.text_level} vs {gap.student_level}），学生可自主阅读",
                "suggested_action": "可侧重深层理解与批判性思维训练，如推断、评价、创意写作",
                "confidence": "high",
            })

        # 6. 连接词密度
        bm_cd = bm.get("connective_density", {"low": 1.0, "high": 3.0})
        if discourse.connective_density > bm_cd["high"]:
            insights.append({
                "metric_name": "衔接词密度",
                "metric_value": f"{discourse.connective_density:.1f}/百词",
                "teaching_implication": f"语篇衔接紧密（{discourse.connective_density:.1f}/百词），逻辑关系密集，对学生的语篇理解能力要求较高",
                "suggested_action": "适合做语篇标记词识别训练，提升学生的语篇意识和逻辑推理能力",
                "confidence": "medium",
            })

        # 7. 超纲词
        c1c2_count = len([d for d in vocab.difficult_words if d.level in ("C1", "C2", "unknown")])
        if c1c2_count > 5:
            top_words = [d.word for d in vocab.difficult_words[:5]]
            insights.append({
                "metric_name": "难点词数量",
                "metric_value": f"{c1c2_count}个",
                "teaching_implication": f"课文包含{c1c2_count}个高难度词汇（C1-C2级），可能影响阅读流畅性",
                "suggested_action": f"建议课前预教以下高频难点词：{', '.join(top_words)}",
                "confidence": "high",
            })

        return insights

    def _load_benchmarks(self) -> Dict[str, Any]:
        """加载各级别教材的指标基准值"""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
        bm_path = os.path.join(data_dir, "benchmarks.json")
        try:
            with open(bm_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # 内置默认基准值
            return {
                "A1": {"awl_ratio": {"low": 0.0, "high": 0.02}, "vocabulary_richness": {"low": 0.3, "high": 0.5}, "avg_sentence_length": {"low": 6, "high": 12}, "flesch_reading_ease": {"low": 70, "high": 90}, "connective_density": {"low": 0.5, "high": 1.5}},
                "A2": {"awl_ratio": {"low": 0.01, "high": 0.04}, "vocabulary_richness": {"low": 0.35, "high": 0.55}, "avg_sentence_length": {"low": 8, "high": 15}, "flesch_reading_ease": {"low": 60, "high": 80}, "connective_density": {"low": 0.8, "high": 2.0}},
                "B1": {"awl_ratio": {"low": 0.03, "high": 0.08}, "vocabulary_richness": {"low": 0.4, "high": 0.65}, "avg_sentence_length": {"low": 12, "high": 22}, "flesch_reading_ease": {"low": 40, "high": 65}, "connective_density": {"low": 1.0, "high": 3.0}},
                "B2": {"awl_ratio": {"low": 0.05, "high": 0.12}, "vocabulary_richness": {"low": 0.45, "high": 0.7}, "avg_sentence_length": {"low": 15, "high": 25}, "flesch_reading_ease": {"low": 30, "high": 55}, "connective_density": {"low": 1.5, "high": 3.5}},
                "C1": {"awl_ratio": {"low": 0.08, "high": 0.18}, "vocabulary_richness": {"low": 0.5, "high": 0.75}, "avg_sentence_length": {"low": 18, "high": 28}, "flesch_reading_ease": {"low": 20, "high": 45}, "connective_density": {"low": 2.0, "high": 4.0}},
                "C2": {"awl_ratio": {"low": 0.1, "high": 0.25}, "vocabulary_richness": {"low": 0.55, "high": 0.8}, "avg_sentence_length": {"low": 20, "high": 32}, "flesch_reading_ease": {"low": 10, "high": 35}, "connective_density": {"low": 2.5, "high": 5.0}},
            }

    def _count_syllables(self, word: str, tokenizer=None) -> int:
        """估算音节数（委托给语言专用分词器）"""
        if tokenizer:
            return tokenizer.count_syllables(word)
        word = word.lower().strip()
        if len(word) <= 3:
            return 1
        count = 0
        vowels = 'aeiouy'
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith('e') and count > 1:
            count -= 1
        return max(count, 1)

    def _is_stopword(self, word: str, tokenizer=None) -> bool:
        """判断是否为停用词（委托给语言专用分词器）"""
        if tokenizer:
            return tokenizer.is_stopword(word)
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
            'should', 'may', 'might', 'can', 'could', 'must', 'need', 'dare',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'this', 'that', 'these', 'those', 'what', 'which', 'who', 'where',
            'when', 'why', 'how', 'and', 'but', 'or', 'not', 'so', 'if',
            'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
            'as', 'into', 'about', 'between', 'through', 'during', 'before',
            'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there',
        }
        return word in stopwords
