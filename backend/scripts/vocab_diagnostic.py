"""
词汇分级覆盖率诊断（F4.2/F4.3 前置）

用真实英语文本跑白盒分析，把"未分级"词分为四类：
1) 专有名词（原文中大写开头，且不在句首位置）
2) 功能词（停用词表命中）
3) 词形还原漏网（尝试手工变形后在词表中命中）
4) 词表真实缺口
输出占比与样例，供 F4.1 词表扩展 / F4.2 专有名词分桶 / F4.3 LLM 兜底分级决策。
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer  # noqa: E402

TEXTS = {
    "文化叙事文": """
Every November, our family gathers for thanksgiving dinner. My grandmother still tells the story
of the first celebration in Plymouth, and how the tradition of turkey and pumpkin pie spread
across the continent after the civil war. Although she left Europe decades ago, the rituals of
her childhood remain unchanged: she bakes bread on Sunday mornings, hums songs she learned in
school, and insists that everyone share one thing they are grateful for before the meal begins.
""",
    "学术议论文": """
Democracy requires more than elections; it depends on institutions that distribute power and
constrain those who hold it. Recent scholarship suggests that economic inequality erodes public
trust, weakening the accountability mechanisms on which representative government relies.
This paper examines these dynamics, considering evidence from longitudinal surveys conducted
across industrialized societies, and proposes reforms designed to enhance transparency.
""",
    "说明文": """
Photosynthesis converts sunlight into chemical energy stored in glucose. Chlorophyll absorbs
red and blue wavelengths while reflecting green light, which explains why leaves appear green.
The process occurs in two stages: light reactions split water molecules, releasing oxygen, and
the Calvin cycle fixes carbon dioxide into carbohydrates. Understanding these mechanisms helps
students appreciate how ecosystems sustain themselves.
""",
}


def main() -> None:
    analyzer = WhiteboxAnalyzer()
    vocab = analyzer.cefr_vocab
    print(f"CEFR 词表规模: {len(vocab)} 词条\n")

    for name, text in TEXTS.items():
        raw_tokens = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text)
        analyzer_en = WhiteboxAnalyzer()
        result = analyzer_en.analyze(text, "B1", language="en")
        dist = result.vocabulary.cefr_distribution
        total = sum(dist.values())
        ungraded_ratio = dist.get("未分级", 0) / max(total, 1)

        # 原文中保留大小写的 token → 专有名词候选（非句首大写）
        proper_noun_candidates = set()
        for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]+\b", text.strip()):
            proper_noun_candidates.add(m.group(0).lower())

        # 词形还原后的词 + 计数（与 analyzer 相同的管线）
        lemmas = [
            analyzer_en._lemmatize(w)
            for w in (t.lower() for t in raw_tokens)
            if len(w) >= 2
        ]
        counts = Counter(lemmas)
        ungraded = {w: c for w, c in counts.items() if w not in vocab}

        buckets = {"专有名词": [], "功能词": [], "还原漏网": [], "词表缺口": []}
        for w, c in sorted(ungraded.items(), key=lambda x: -x[1]):
            if w in proper_noun_candidates or w in {"thanksgiving"}:
                buckets["专有名词"].append(w)
            elif analyzer_en._is_stopword(w):
                buckets["功能词"].append(w)
            else:
                variants = [w + "e", w[:-1], w + "y", w.replace("ize", "ise")]
                if any(v in vocab for v in variants):
                    buckets["还原漏网"].append(w)
                else:
                    buckets["词表缺口"].append(w)

        n_ungraded = sum(counts[w] for w in ungraded)
        print(f"== {name} == 总词数 {total}，未分级 {dist.get('未分级', 0)}（{ungraded_ratio:.0%}）")
        for label, words in buckets.items():
            share = sum(counts[w] for w in words) / max(n_ungraded, 1)
            sample = ", ".join(f"{w}×{counts[w]}" for w in words[:8])
            print(f"  {label}: {len(words)} 种 / {share:.0%}  {sample}")
        print()


if __name__ == "__main__":
    main()
