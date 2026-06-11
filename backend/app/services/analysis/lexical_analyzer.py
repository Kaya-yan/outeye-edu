"""
词汇分析器

基于Lexile框架、CEFR和AWL进行词汇分析
"""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
import re
import math


@dataclass
class LexicalAnalysisResult:
    """词汇分析结果"""
    total_words: int
    unique_words: int
    vocabulary_richness: float
    academic_word_count: int
    academic_words: List[str]
    unknown_words: List[str]
    cefr_distribution: Dict[str, int]
    difficulty_score: float
    word_frequency: Dict[str, int]


class LexicalAnalyzer:
    """词汇分析器"""

    def __init__(self):
        # 加载CEFR词汇表
        self.cefr_vocab = self._load_cefr_vocab()

        # 加载学术词汇表（AWL）
        self.academic_vocab = self._load_academic_vocab()

        # 停用词
        self.stop_words = self._load_stop_words()

    def _load_cefr_vocab(self) -> Dict[str, str]:
        """加载CEFR词汇表"""
        # 简化版：实际应加载完整CEFR词汇表
        cefr_vocab = {}

        # A1级别词汇
        a1_words = [
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
            'should', 'may', 'might', 'can', 'could', 'must', 'need', 'dare',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their', 'mine',
            'yours', 'hers', 'ours', 'theirs', 'this', 'that', 'these', 'those',
            'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
            'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'only', 'own', 'same', 'than',
            'too', 'very', 'just', 'because', 'as', 'until', 'while', 'of',
            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'through',
            'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up',
            'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'can', 'will', 'just', 'don',
            'should', 'now', 'good', 'new', 'first', 'last', 'long', 'great',
            'little', 'own', 'other', 'old', 'right', 'big', 'high', 'different',
            'small', 'large', 'next', 'early', 'young', 'important', 'few',
            'public', 'bad', 'same', 'able', 'man', 'woman', 'child', 'person',
            'people', 'time', 'year', 'way', 'day', 'thing', 'world', 'life',
            'hand', 'part', 'place', 'case', 'week', 'company', 'system',
            'program', 'question', 'work', 'government', 'number', 'night',
            'point', 'home', 'water', 'room', 'mother', 'area', 'money',
            'story', 'fact', 'month', 'lot', 'right', 'study', 'book',
            'eye', 'job', 'word', 'business', 'issue', 'side', 'kind',
            'head', 'house', 'service', 'friend', 'father', 'power',
            'hour', 'game', 'line', 'end', 'member', 'city', 'community',
            'name', 'president', 'team', 'minute', 'idea', 'body', 'information',
            'back', 'parent', 'face', 'others', 'level', 'office', 'door',
            'health', 'person', 'art', 'war', 'history', 'party', 'result',
            'change', 'morning', 'reason', 'research', 'girl', 'guy', 'moment',
            'air', 'teacher', 'force', 'education'
        ]

        for word in a1_words:
            cefr_vocab[word.lower()] = 'A1'

        # A2级别词汇
        a2_words = [
            'able', 'accept', 'add', 'agree', 'allow', 'almost', 'along',
            'already', 'always', 'among', 'answer', 'ask', 'become', 'begin',
            'believe', 'bring', 'build', 'buy', 'call', 'carry', 'catch',
            'cause', 'certain', 'change', 'check', 'choose', 'claim', 'class',
            'close', 'come', 'consider', 'continue', 'control', 'cost',
            'create', 'cut', 'dark', 'decide', 'develop', 'die', 'drive',
            'drop', 'eat', 'enough', 'establish', 'even', 'ever', 'example',
            'exist', 'experience', 'fall', 'feel', 'find', 'finish', 'follow',
            'get', 'give', 'go', 'grow', 'happen', 'help', 'hold', 'hope',
            'include', 'increase', 'interest', 'keep', 'kill', 'know', 'land',
            'large', 'last', 'late', 'lead', 'leave', 'let', 'lie', 'like',
            'listen', 'live', 'lose', 'love', 'make', 'mean', 'meet', 'might',
            'move', 'must', 'need', 'never', 'offer', 'open', 'order', 'pay',
            'play', 'possible', 'present', 'produce', 'provide', 'put',
            'rather', 'read', 'real', 'receive', 'remain', 'remember',
            'report', 'run', 'say', 'see', 'seem', 'sell', 'send', 'set',
            'show', 'sit', 'sleep', 'speak', 'spend', 'stand', 'start',
            'stay', 'stop', 'suggest', 'take', 'talk', 'tell', 'think',
            'try', 'turn', 'understand', 'use', 'wait', 'walk', 'want',
            'watch', 'win', 'wish', 'without', 'work', 'write', 'young'
        ]

        for word in a2_words:
            if word.lower() not in cefr_vocab:
                cefr_vocab[word.lower()] = 'A2'

        # B1级别词汇
        b1_words = [
            'achieve', 'act', 'admit', 'advantage', 'affect', 'afford',
            'age', 'agency', 'agent', 'agree', 'amount', 'animal', 'appear',
            'apply', 'approach', 'argue', 'arm', 'around', 'arrange', 'art',
            'attack', 'attention', 'available', 'avoid', 'base', 'beat',
            'behavior', 'believe', 'benefit', 'bit', 'black', 'blood',
            'blow', 'board', 'born', 'box', 'break', 'brother', 'budget',
            'build', 'burn', 'bus', 'campaign', 'capital', 'care', 'career',
            'case', 'catch', 'cause', 'center', 'chance', 'charge', 'church',
            'citizen', 'civil', 'claim', 'clear', 'climb', 'close', 'coach',
            'cold', 'collection', 'college', 'comment', 'common', 'community',
            'compare', 'computer', 'concern', 'condition', 'conference',
            'congress', 'connect', 'consider', 'consumer', 'contain',
            'context', 'continue', 'contract', 'contribute', 'conversation',
            'cool', 'couple', 'course', 'court', 'cover', 'crime', 'cultural',
            'culture', 'cup', 'current', 'customer', 'daughter', 'dead',
            'deal', 'death', 'debate', 'decade', 'decide', 'decision',
            'deep', 'defense', 'degree', 'democrat', 'depend', 'describe',
            'design', 'despite', 'detail', 'determine', 'develop', 'device',
            'difference', 'difficult', 'dinner', 'direction', 'director',
            'discover', 'discuss', 'discussion', 'disease', 'doctor',
            'dog', 'draw', 'dream', 'drive', 'drop', 'drug', 'during',
            'east', 'easy', 'economic', 'economy', 'edge', 'effect',
            'effort', 'eight', 'either', 'election', 'else', 'emotional',
            'energy', 'enjoy', 'enter', 'entire', 'environment', 'especially',
            'establish', 'event', 'evidence', 'exactly', 'executive',
            'expect', 'expert', 'explain', 'factor', 'fail', 'fall',
            'family', 'far', 'fast', 'fear', 'federal', 'feel', 'field',
            'fight', 'fill', 'film', 'final', 'finally', 'financial',
            'find', 'finger', 'fire', 'fish', 'floor', 'fly', 'focus',
            'food', 'force', 'foreign', 'forget', 'form', 'former',
            'forward', 'four', 'free', 'friend', 'front', 'full',
            'fund', 'future', 'garden', 'general', 'generation', 'girl',
            'glass', 'goal', 'green', 'ground', 'growth', 'guess',
            'gun', 'guy', 'hair', 'half', 'hang', 'happen', 'happy',
            'hard', 'heart', 'heat', 'heavy', 'help', 'here', 'high',
            'himself', 'hit', 'hold', 'hope', 'huge', 'hundred',
            'husband', 'idea', 'identify', 'image', 'imagine', 'impact',
            'important', 'improve', 'include', 'increase', 'indeed',
            'indicate', 'individual', 'industry', 'inform', 'inside',
            'instead', 'institution', 'interest', 'interview', 'involve',
            'issue', 'item', 'itself', 'join', 'just', 'key', 'kid',
            'kill', 'kitchen', 'know', 'labor', 'language', 'large',
            'later', 'laugh', 'lawyer', 'lay', 'lead', 'leader', 'learn',
            'least', 'left', 'legal', 'less', 'letter', 'level', 'lie',
            'life', 'light', 'like', 'likely', 'list', 'listen', 'little',
            'local', 'long', 'look', 'lose', 'love', 'machine', 'main',
            'maintain', 'major', 'manage', 'manager', 'many', 'market',
            'marriage', 'material', 'matter', 'may', 'maybe', 'mean',
            'measure', 'media', 'medical', 'meeting', 'memory', 'mention',
            'message', 'method', 'middle', 'might', 'military', 'million',
            'mind', 'minute', 'miss', 'mission', 'model', 'modern',
            'moment', 'money', 'month', 'morning', 'most', 'mother',
            'mouth', 'move', 'movement', 'movie', 'music', 'must',
            'myself', 'name', 'nation', 'national', 'natural', 'nature',
            'near', 'nearly', 'necessary', 'network', 'news', 'newspaper',
            'nice', 'none', 'north', 'nothing', 'note', 'notice',
            'number', 'occur', 'officer', 'official', 'often', 'oil',
            'option', 'order', 'organization', 'others', 'outside',
            'owner', 'page', 'pain', 'painting', 'paper', 'parent',
            'part', 'particular', 'partner', 'party', 'pass', 'past',
            'patient', 'pattern', 'peace', 'people', 'per', 'perform',
            'performance', 'perhaps', 'period', 'person', 'personal',
            'phone', 'physical', 'pick', 'picture', 'piece', 'place',
            'plan', 'plant', 'play', 'player', 'please', 'point',
            'police', 'policy', 'political', 'politics', 'poor',
            'popular', 'population', 'position', 'positive', 'possible',
            'power', 'practice', 'prepare', 'present', 'president',
            'pressure', 'pretty', 'prevent', 'price', 'private',
            'probably', 'problem', 'process', 'produce', 'product',
            'production', 'professional', 'program', 'project',
            'property', 'protect', 'prove', 'provide', 'public',
            'pull', 'purpose', 'push', 'quality', 'question',
            'quickly', 'quite', 'race', 'radio', 'raise', 'range',
            'rate', 'rather', 'reach', 'read', 'ready', 'real',
            'reality', 'realize', 'reason', 'receive', 'recent',
            'recently', 'record', 'reduce', 'reflect', 'region',
            'relate', 'relationship', 'religious', 'remain', 'remember',
            'remove', 'report', 'represent', 'republican', 'require',
            'research', 'resource', 'respond', 'response', 'result',
            'return', 'reveal', 'right', 'rise', 'risk', 'road',
            'rock', 'role', 'room', 'rule', 'run', 'safe', 'scene',
            'season', 'seat', 'second', 'section', 'security', 'seek',
            'seem', 'sell', 'senior', 'sense', 'series', 'serious',
            'serve', 'service', 'set', 'seven', 'several', 'shake',
            'share', 'she', 'shoot', 'short', 'shot', 'shoulder',
            'show', 'side', 'sign', 'significant', 'similar', 'simple',
            'simply', 'since', 'sing', 'single', 'sister', 'sit',
            'site', 'situation', 'skill', 'skin', 'small', 'smile',
            'social', 'society', 'soldier', 'some', 'somebody', 'someone',
            'something', 'sometimes', 'son', 'song', 'soon', 'sort',
            'sound', 'source', 'south', 'southern', 'space', 'speak',
            'special', 'specific', 'speech', 'spend', 'sport', 'spring',
            'staff', 'stage', 'stand', 'standard', 'star', 'start',
            'state', 'statement', 'station', 'stay', 'step', 'still',
            'stock', 'stop', 'store', 'story', 'strategy', 'street',
            'strong', 'structure', 'student', 'study', 'stuff', 'style',
            'subject', 'success', 'successful', 'such', 'suddenly',
            'suffer', 'suggest', 'summer', 'support', 'sure', 'surface',
            'system', 'table', 'talk', 'task', 'tax', 'teach', 'teacher',
            'team', 'technology', 'television', 'tell', 'ten', 'tend',
            'term', 'test', 'than', 'thank', 'that', 'their', 'them',
            'themselves', 'then', 'theory', 'these', 'they', 'thing',
            'think', 'third', 'this', 'those', 'though', 'thought',
            'thousand', 'threat', 'three', 'through', 'throughout',
            'throw', 'thus', 'today', 'together', 'tonight', 'total',
            'tough', 'toward', 'town', 'trade', 'traditional', 'training',
            'travel', 'treat', 'treatment', 'tree', 'trial', 'trip',
            'trouble', 'true', 'truth', 'try', 'turn', 'tv', 'type',
            'under', 'understand', 'unit', 'until', 'upon', 'usually',
            'value', 'various', 'very', 'victim', 'view', 'violence',
            'visit', 'voice', 'vote', 'wait', 'walk', 'wall', 'want',
            'war', 'watch', 'water', 'weapon', 'wear', 'week', 'weight',
            'west', 'western', 'what', 'whatever', 'when', 'where',
            'whereas', 'wherever', 'whether', 'which', 'while', 'white',
            'whole', 'whom', 'whose', 'why', 'wide', 'wife', 'will',
            'win', 'wind', 'window', 'wish', 'with', 'within', 'without',
            'woman', 'wonder', 'word', 'work', 'worker', 'world',
            'worry', 'would', 'write', 'writer', 'wrong', 'yard',
            'yeah', 'year', 'yes', 'yet', 'you', 'young', 'your',
            'yourself', 'youth'
        ]

        for word in b1_words:
            if word.lower() not in cefr_vocab:
                cefr_vocab[word.lower()] = 'B1'

        return cefr_vocab

    def _load_academic_vocab(self) -> Set[str]:
        """加载学术词汇表（AWL）"""
        return {
            'abstract', 'academic', 'accelerate', 'accommodate', 'accumulate',
            'accurate', 'achieve', 'acknowledge', 'acquire', 'adapt', 'adequate',
            'adjacent', 'adjust', 'administrate', 'adult', 'advocate', 'affect',
            'aggregate', 'allocate', 'alter', 'alternative', 'ambiguous',
            'amend', 'analogy', 'analyse', 'annual', 'anticipate', 'apparent',
            'append', 'appreciate', 'approach', 'appropriate', 'approximate',
            'arbitrary', 'assemble', 'assess', 'assign', 'assist', 'assume',
            'assure', 'attach', 'attain', 'attribute', 'author', 'authority',
            'automate', 'available', 'aware', 'behalf', 'benefit', 'bias',
            'bond', 'brief', 'bulk', 'capable', 'capacity', 'category',
            'cease', 'challenge', 'channel', 'chapter', 'chart', 'chemical',
            'chronological', 'circumstance', 'civil', 'clarify', 'classic',
            'clause', 'code', 'coherent', 'coincide', 'collapse', 'colleague',
            'commence', 'comment', 'commission', 'commit', 'commodity',
            'communicate', 'community', 'compatible', 'compensate', 'compile',
            'complement', 'complex', 'component', 'comprehensive', 'comprise',
            'compromise', 'compute', 'conceive', 'concentrate', 'concept',
            'conclude', 'concurrent', 'conduct', 'conference', 'confine',
            'confirm', 'conflict', 'conform', 'consent', 'consequence',
            'considerable', 'consist', 'constant', 'constitute', 'construct',
            'consult', 'consume', 'contact', 'contain', 'contemporary',
            'context', 'contract', 'contradict', 'contrary', 'contrast',
            'contribute', 'controversy', 'convene', 'convention', 'converse',
            'convert', 'convince', 'cooperate', 'coordinate', 'core',
            'corporate', 'correspond', 'couple', 'create', 'credit',
            'criterion', 'crucial', 'culture', 'currency', 'cycle', 'data',
            'debate', 'decade', 'decline', 'deduce', 'define', 'definite',
            'demonstrate', 'denote', 'deny', 'depress', 'derive', 'design',
            'despite', 'detect', 'deviate', 'device', 'devote', 'dimension',
            'diminish', 'displace', 'display', 'dispose', 'distinct',
            'distribute', 'diverse', 'document', 'domain', 'domestic',
            'dominate', 'draft', 'duration', 'dynamic', 'economy', 'edit',
            'element', 'eliminate', 'emerge', 'emphasis', 'empirical',
            'enable', 'encounter', 'enhance', 'enormous', 'ensure', 'entity',
            'environment', 'equate', 'equip', 'equivalent', 'erode', 'error',
            'establish', 'estimate', 'evaluate', 'evident', 'evolve',
            'exceed', 'exclude', 'exhibit', 'expand', 'expert', 'explicit',
            'exploit', 'export', 'expose', 'external', 'extract', 'facilitate',
            'factor', 'feature', 'federal', 'finance', 'flexible', 'fluctuate',
            'focus', 'formulate', 'foundation', 'framework', 'function',
            'fund', 'fundamental', 'generate', 'genre', 'globe', 'grade',
            'grant', 'guarantee', 'guideline', 'hence', 'hierarchy',
            'hypothesis', 'identical', 'identify', 'ideology', 'ignorant',
            'illustrate', 'image', 'immigrate', 'impact', 'implement',
            'implicate', 'implicit', 'imply', 'impose', 'incentive',
            'incident', 'incorporate', 'index', 'indicate', 'individual',
            'induce', 'inevitable', 'infrastructure', 'inherent', 'inhibit',
            'initial', 'initiate', 'inject', 'innovate', 'input', 'insert',
            'insight', 'inspect', 'instance', 'institute', 'integrate',
            'integrity', 'intelligence', 'intense', 'interact', 'interim',
            'internal', 'interpret', 'interval', 'intervene', 'intrinsic',
            'invest', 'investigate', 'invoke', 'involve', 'isolate', 'issue',
            'item', 'journal', 'justify', 'label', 'layer', 'lecture',
            'legal', 'legislate', 'levy', 'liberal', 'license', 'likewise',
            'link', 'locate', 'logic', 'maintain', 'major', 'manipulate',
            'margin', 'mature', 'maximise', 'mechanism', 'media', 'mediate',
            'method', 'migrate', 'military', 'minimise', 'minor', 'modify',
            'monitor', 'motive', 'mutual', 'negate', 'network', 'neutral',
            'nonetheless', 'norm', 'notion', 'nuclear', 'objective', 'oblige',
            'obtain', 'obvious', 'occupy', 'occur', 'offset', 'ongoing',
            'option', 'orient', 'outcome', 'output', 'overall', 'overlap',
            'overseas', 'panel', 'parallel', 'parameter', 'participate',
            'partner', 'passive', 'perceive', 'period', 'persist', 'perspective',
            'phase', 'phenomenon', 'philosophy', 'physical', 'plus', 'policy',
            'portion', 'pose', 'positive', 'potential', 'practitioner', 'precede',
            'precise', 'predict', 'predominant', 'preliminary', 'presume',
            'previous', 'primary', 'principal', 'prior', 'priority', 'proceed',
            'process', 'professional', 'prohibit', 'project', 'promote',
            'proportion', 'prospect', 'protocol', 'psychology', 'publication',
            'purchase', 'pursue', 'qualitative', 'quote', 'radical', 'range',
            'ratio', 'rational', 'react', 'recover', 'refine', 'reform',
            'region', 'register', 'regulate', 'reinforce', 'reject', 'relax',
            'release', 'relevant', 'reluctant', 'rely', 'remove', 'require',
            'research', 'reside', 'resolve', 'resource', 'respond', 'restore',
            'restrict', 'retain', 'reveal', 'revenue', 'reverse', 'revise',
            'revolution', 'rigid', 'role', 'route', 'scenario', 'schedule',
            'scheme', 'scope', 'section', 'sector', 'secure', 'seek',
            'select', 'sequence', 'series', 'shift', 'significant', 'similar',
            'simulate', 'site', 'so-called', 'sole', 'somewhat', 'source',
            'specific', 'specify', 'sphere', 'stable', 'statistic', 'status',
            'stimulus', 'strategy', 'structure', 'subordinate', 'submit',
            'subsequent', 'subsidy', 'substitute', 'successor', 'sufficient',
            'summarise', 'supplement', 'survey', 'survive', 'suspend',
            'sustain', 'symbol', 'target', 'task', 'team', 'technical',
            'technique', 'technology', 'temporary', 'tense', 'terminate',
            'theme', 'theory', 'thereby', 'thesis', 'topic', 'trace',
            'tradition', 'transfer', 'transform', 'transit', 'transmit',
            'transport', 'trend', 'trigger', 'ultimate', 'undergo',
            'underlie', 'undertake', 'uniform', 'unique', 'utilise',
            'valid', 'vary', 'vehicle', 'version', 'via', 'violate',
            'virtual', 'visible', 'vision', 'volume', 'voluntary',
            'welfare', 'whereas', 'whereby'
        }

    def _load_stop_words(self) -> Set[str]:
        """加载停用词"""
        return {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
            'should', 'may', 'might', 'can', 'could', 'must', 'need', 'dare',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'only', 'own', 'same', 'than',
            'too', 'very', 'just', 'because', 'as', 'until', 'while', 'of',
            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'through',
            'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up',
            'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'what', 'which', 'who', 'whom', 'whose'
        }

    def analyze(self, text: str, student_level: str = "B1") -> LexicalAnalysisResult:
        """
        分析词汇

        Args:
            text: 文本内容
            student_level: 学生水平

        Returns:
            词汇分析结果
        """
        # 分词
        words = self._tokenize(text)

        # 统计词频
        word_freq = {}
        for word in words:
            word_lower = word.lower()
            word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

        # 计算基本统计
        total_words = len(words)
        unique_words = len(word_freq)

        # 计算词汇丰富度（TTR）
        vocabulary_richness = unique_words / max(total_words, 1)

        # 识别学术词汇
        academic_words = [word for word in word_freq.keys() if word in self.academic_vocab]
        academic_word_count = len(academic_words)

        # 识别生词（不在学生水平词汇表中的词）
        student_vocab_level = self._get_level_threshold(student_level)
        unknown_words = []
        for word in word_freq.keys():
            if word not in self.stop_words and len(word) > 2:
                word_level = self.cefr_vocab.get(word)
                if word_level and self._level_to_value(word_level) > student_vocab_level:
                    unknown_words.append(word)
                elif not word_level and word not in self.academic_vocab:
                    # 未知词汇，可能是生词
                    if word_freq[word] <= 2:  # 低频词更可能是生词
                        unknown_words.append(word)

        # CEFR分布
        cefr_distribution = {"A1": 0, "A2": 0, "B1": 0, "B2": 0, "C1": 0, "C2": 0, "unknown": 0}
        for word in word_freq.keys():
            level = self.cefr_vocab.get(word)
            if level:
                cefr_distribution[level] += 1
            else:
                cefr_distribution["unknown"] += 1

        # 计算难度评分
        difficulty_score = self._calculate_difficulty_score(
            word_freq, student_level, vocabulary_richness
        )

        return LexicalAnalysisResult(
            total_words=total_words,
            unique_words=unique_words,
            vocabulary_richness=vocabulary_richness,
            academic_word_count=academic_word_count,
            academic_words=academic_words[:20],
            unknown_words=unknown_words[:30],
            cefr_distribution=cefr_distribution,
            difficulty_score=difficulty_score,
            word_frequency=dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50])
        )

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 移除标点符号，保留单词
        text = text.lower()
        words = re.findall(r'[a-z]+', text)
        return [w for w in words if len(w) > 1]

    def _get_level_threshold(self, level: str) -> int:
        """获取水平阈值"""
        levels = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
        return levels.get(level, 3)

    def _level_to_value(self, level: str) -> int:
        """将水平转换为数值"""
        levels = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
        return levels.get(level, 3)

    def _calculate_difficulty_score(
        self,
        word_freq: Dict[str, int],
        student_level: str,
        vocabulary_richness: float
    ) -> float:
        """计算难度评分"""
        student_value = self._get_level_threshold(student_level)

        # 计算词汇水平分布
        level_sum = 0
        count = 0
        for word in word_freq.keys():
            level = self.cefr_vocab.get(word)
            if level:
                level_sum += self._level_to_value(level)
                count += 1

        avg_level = level_sum / max(count, 1)

        # 难度评分（基于平均词汇水平和学生水平的差异）
        level_diff = avg_level - student_value
        difficulty = 5 + level_diff * 1.5

        # 调整因素
        # 词汇丰富度越高，难度越大
        difficulty += (vocabulary_richness - 0.5) * 2

        return round(min(max(difficulty, 1), 10), 1)
