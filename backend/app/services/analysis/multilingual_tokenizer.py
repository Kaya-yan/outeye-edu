"""
多语言分词器

按语言选择分词/分句/音节计数/停用词策略。
每种语言实现 BaseTokenizer 的 5 个方法，接口统一。
"""

import re
from abc import ABC, abstractmethod
from typing import List, Set


class BaseTokenizer(ABC):
    """分词器基类"""

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """分词，返回小写词列表"""

    @abstractmethod
    def split_sentences(self, text: str) -> List[str]:
        """分句"""

    @abstractmethod
    def count_syllables(self, word: str) -> int:
        """估算音节数"""

    @abstractmethod
    def get_stopwords(self) -> Set[str]:
        """停用词表"""

    @abstractmethod
    def lemmatize(self, word: str) -> str:
        """词形还原（简单规则）"""

    def is_stopword(self, word: str) -> bool:
        return word.lower() in self.get_stopwords()


# ============ 英语 ============

class EnglishTokenizer(BaseTokenizer):
    """英语分词器（复用现有逻辑）"""

    def tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def count_syllables(self, word: str) -> int:
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

    def get_stopwords(self) -> Set[str]:
        return {
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

    def lemmatize(self, word: str) -> str:
        # 简易后缀剥离（完整版在 whitebox_analyzer.py 中，这里提供基础版本）
        w = word.lower().strip()
        if len(w) <= 3:
            return w
        for suffix in ['ing', 'tion', 'ment', 'ness', 'ive', 'ful', 'less', 'ly', 'er', 'ed', 'es', 's']:
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                return w[:-len(suffix)]
        return w


# ============ 日语 ============

class JapaneseTokenizer(BaseTokenizer):
    """日语分词器（字符级分析）"""

    # 平假名 + 片假名 + 汉字 + 拉丁字母（外来语）
    _TOKEN_RE = re.compile(r'[一-鿿ぁ-ゟ゠-ヿ]+|[a-zA-Z]+')

    def tokenize(self, text: str) -> List[str]:
        # 日语分词：按假名/汉字/外来语切分
        # 不做形态素解析，用正则粗切
        tokens = self._TOKEN_RE.findall(text)
        # 过滤纯标点和过短的
        return [t.lower() for t in tokens if len(t) >= 1]

    def split_sentences(self, text: str) -> List[str]:
        # 日语句末标点：。！？
        sentences = re.split(r'[。！？]\s*', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    def count_syllables(self, word: str) -> int:
        # 日语音节 ≈ 假名数量（每个假名 = 1 音节）
        hiragana = len(re.findall(r'[ぁ-ゟ]', word))
        katakana = len(re.findall(r'[゠-ヿ]', word))
        # 汉字每个算 2 音节（音读）
        kanji = len(re.findall(r'[一-鿿]', word)) * 2
        # 外来语按英文字母估算
        latin = max(1, len(re.findall(r'[a-zA-Z]', word)) // 3)
        return max(hiragana + katakana + kanji + latin, 1)

    def get_stopwords(self) -> Set[str]:
        return {
            'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ',
            'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として', 'い', 'や',
            'れる', 'など', 'なっ', 'ない', 'この', 'ため', 'その', 'あっ', 'よう',
            'また', 'もの', 'という', 'あり', 'まで', 'られ', 'なる', 'へ', 'か',
            'だ', 'これ', 'によって', 'により', 'おり', 'より', 'による', 'ず', 'なり',
            'られる', 'において', 'ば', 'なかっ', 'なく', 'しかし', 'について', 'せ', 'だっ',
        }

    def lemmatize(self, word: str) -> str:
        # 日语不做词形还原（动词活用复杂，留给 LLM）
        return word


# ============ 法语 ============

class FrenchTokenizer(BaseTokenizer):
    """法语分词器"""

    _TOKEN_RE = re.compile(r"\b[a-zA-ZÀ-ÿ]+(?:'[a-zA-ZÀ-ÿ]+)?\b")

    def tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in self._TOKEN_RE.findall(text)]

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def count_syllables(self, word: str) -> int:
        word = word.lower().strip()
        if len(word) <= 2:
            return 1
        count = 0
        vowels = 'aeiouyàâæéèêëîïôœùûüÿ'
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith('e') and count > 1:
            count -= 1
        return max(count, 1)

    def get_stopwords(self) -> Set[str]:
        return {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'au', 'aux',
            'et', 'ou', 'mais', 'donc', 'car', 'ni', 'que', 'qui', 'dont',
            'où', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
            'me', 'te', 'se', 'lui', 'leur', 'ce', 'cette', 'ces', 'mon',
            'ton', 'son', 'notre', 'votre', 'leur', 'ma', 'ta', 'sa',
            'est', 'sont', 'était', 'être', 'avoir', 'a', 'ont', 'avait',
            'dans', 'par', 'pour', 'sur', 'avec', 'sans', 'sous', 'entre',
            'en', 'y', 'ne', 'pas', 'plus', 'aussi', 'très', 'bien',
        }

    def lemmatize(self, word: str) -> str:
        w = word.lower().strip()
        if len(w) <= 3:
            return w
        # 法语常见后缀
        for suffix in ['issement', 'ement', 'tion', 'ment', 'euse', 'eux', 'ive', 'ique', 'ent', 'er', 'ez', 'es', 's']:
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                return w[:-len(suffix)]
        return w


# ============ 德语 ============

class GermanTokenizer(BaseTokenizer):
    """德语分词器"""

    _TOKEN_RE = re.compile(r"\b[a-zA-ZÀ-ÿÄÖÜäöüß]+(?:'[a-zA-ZÀ-ÿÄÖÜäöüß]+)?\b")

    def tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in self._TOKEN_RE.findall(text)]

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def count_syllables(self, word: str) -> int:
        word = word.lower().strip()
        if len(word) <= 3:
            return 1
        count = 0
        vowels = 'aeiouyäöü'
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        return max(count, 1)

    def get_stopwords(self) -> Set[str]:
        return {
            'der', 'die', 'das', 'ein', 'eine', 'einer', 'eines', 'einem', 'einen',
            'und', 'oder', 'aber', 'denn', 'doch', 'dass', 'weil', 'wenn', 'als',
            'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'sie', 'mich', 'dich',
            'sich', 'uns', 'euch', 'mir', 'dir', 'ihm', 'ihnen', 'mein', 'dein',
            'sein', 'ihr', 'unser', 'euer', 'ist', 'sind', 'war', 'hat', 'haben',
            'werden', 'wird', 'wurde', 'worden', 'sein', 'gewesen', 'kann', 'muss',
            'in', 'an', 'auf', 'mit', 'für', 'von', 'zu', 'bei', 'nach', 'über',
            'unter', 'vor', 'hinter', 'neben', 'zwischen', 'durch', 'gegen', 'ohne',
            'nicht', 'auch', 'noch', 'schon', 'nur', 'sehr', 'hier', 'dort', 'da',
        }

    def lemmatize(self, word: str) -> str:
        w = word.lower().strip()
        if len(w) <= 3:
            return w
        # 德语复合词和后缀（简化）
        for suffix in ['ung', 'heit', 'keit', 'lich', 'isch', 'bar', 'sam', 'los', 'en', 'er', 'e', 's', 'n']:
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                return w[:-len(suffix)]
        return w


# ============ 西班牙语 ============

class SpanishTokenizer(BaseTokenizer):
    """西班牙语分词器"""

    _TOKEN_RE = re.compile(r"\b[a-zA-ZÀ-ÿÑñÜü]+(?:'[a-zA-ZÀ-ÿÑñÜü]+)?\b")

    def tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in self._TOKEN_RE.findall(text)]

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?¡¿])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def count_syllables(self, word: str) -> int:
        word = word.lower().strip()
        if len(word) <= 2:
            return 1
        count = 0
        vowels = 'aeiouáéíóúü'
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith('e') and count > 1:
            count -= 1
        return max(count, 1)

    def get_stopwords(self) -> Set[str]:
        return {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del',
            'al', 'y', 'o', 'pero', 'sino', 'que', 'quien', 'cual', 'donde',
            'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
            'me', 'te', 'se', 'nos', 'os', 'le', 'les', 'lo', 'mi', 'tu', 'su',
            'es', 'son', 'está', 'están', 'ser', 'estar', 'haber', 'hay', 'tiene',
            'en', 'con', 'por', 'para', 'sin', 'sobre', 'entre', 'hasta', 'desde',
            'no', 'también', 'muy', 'más', 'menos', 'ya', 'aún', 'siempre', 'nunca',
        }

    def lemmatize(self, word: str) -> str:
        w = word.lower().strip()
        if len(w) <= 3:
            return w
        for suffix in ['mente', 'ción', 'sión', 'idad', 'oso', 'osa', 'ivo', 'iva', 'ar', 'er', 'ir', 'as', 'es', 'os', 's']:
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                return w[:-len(suffix)]
        return w


# ============ 韩语 ============

class KoreanTokenizer(BaseTokenizer):
    """韩语分词器（字符级分析）"""

    _TOKEN_RE = re.compile(r'[가-힣]+|[a-zA-Z]+')

    def tokenize(self, text: str) -> List[str]:
        tokens = self._TOKEN_RE.findall(text)
        return [t.lower() for t in tokens if len(t) >= 1]

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?。！？]\s*', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    def count_syllables(self, word: str) -> int:
        # 韩语音节块每个 = 1 音节
        hangul = len(re.findall(r'[가-힯]', word))
        latin = max(1, len(re.findall(r'[a-zA-Z]', word)) // 3)
        return max(hangul + latin, 1)

    def get_stopwords(self) -> Set[str]:
        return {
            '이', '그', '저', '것', '수', '등', '들', '및', '에서', '로', '으로',
            '를', '을', '이', '가', '은', '는', '의', '에', '와', '과', '한', '할',
            '하', '된', '되고', '있', '없', '되', '같', '그리고', '하지만', '그런데',
            '또는', '또', '그러나', '그래서', '때문', '위해', '통해', '대해',
        }

    def lemmatize(self, word: str) -> str:
        # 韩语不做词形还原（黏着语，复杂度高）
        return word


# ============ 工厂函数 ============

_TOKENIZERS = {
    "en": EnglishTokenizer,
    "ja": JapaneseTokenizer,
    "fr": FrenchTokenizer,
    "de": GermanTokenizer,
    "es": SpanishTokenizer,
    "ko": KoreanTokenizer,
}


def get_tokenizer(language: str) -> BaseTokenizer:
    """获取指定语言的分词器，未知语言默认英语"""
    cls = _TOKENIZERS.get(language, EnglishTokenizer)
    return cls()
