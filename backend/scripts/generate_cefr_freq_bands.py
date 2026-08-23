"""
生成 CEFR 频段补充词表 data/cefr_freq_bands.json（F4.1）

用 wordfreq 语料频率带近似 CEFR 等级，只填充主词表（cefr_wordlist.json，
3253 条权威分级）未覆盖的词——主词表优先级更高，本表仅做缺口补充。

运行前置：pip install wordfreq（运行时不需要，产物是纯 JSON）
映射带（基于词频排名的工程近似）：
  1-1000 → A1，1001-2500 → A2，2501-5000 → B1，
  5001-9000 → B2，9001-14000 → C1，14001-20000 → C2
"""

import json
import re
from pathlib import Path

from wordfreq import top_n_list

BANDS = [(1000, "A1"), (2500, "A2"), (5000, "B1"), (9000, "B2"), (14000, "C1"), (20000, "C2")]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    with open(DATA_DIR / "cefr_wordlist.json", encoding="utf-8") as f:
        primary = {e["word"].lower() for e in json.load(f)}

    out = []
    seen = set(primary)
    words = top_n_list("en", BANDS[-1][0])
    cutoff = 0
    for limit, level in BANDS:
        for w in words[cutoff:limit]:
            cutoff = limit
            if w in seen or not re.fullmatch(r"[a-z]+", w):
                continue
            seen.add(w)
            out.append({"word": w, "level": level})

    path = DATA_DIR / "cefr_freq_bands.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"主词表 {len(primary)} 条；补充词表 {len(out)} 条 → {path}")


if __name__ == "__main__":
    main()
