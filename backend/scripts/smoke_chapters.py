# -*- coding: utf-8 -*-
"""章节式滚动重构冒烟：章上限算法 / 回退蓝图 / 蓝图归一化 / 骨架拼装。

跑法（backend 目录下）：
    python scripts/smoke_chapters.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.courseware_llm_generator import (  # noqa: E402
    MAX_CHAPTERS,
    MAX_SECTIONS_PER_CHAPTER,
    _ContentPage,
    _assemble_skeleton,
    _derive_chapters,
    _enforce_chapter_caps,
    _fallback_blueprint,
    _normalize_blueprint,
)

PASS = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}{(' | ' + detail) if detail and not cond else ''}")
    if cond:
        PASS += 1
    else:
        print(f"      {detail}")


def chapters_summary(specs):
    return [(ch["display"], len(ch["idxs"])) for ch in _derive_chapters(specs)]


def make_specs(chapter_sizes, anchored=True):
    """按 [(章标签, 节数)] 构造平面节蓝图；首章 cover、末章 summary。"""
    specs = []
    for label, n in chapter_sizes:
        for j in range(n):
            if label == "导入":
                kind = "cover" if j == 0 else "agenda"
            elif label == "总结作业":
                kind = "summary"
            else:
                kind = "language_focus"
            spec = {"kind": kind, "title": "", "intent": "", "chapter": label,
                    "para": None}
            if kind == "language_focus":
                spec["para"] = [len(specs)] if anchored else None
                if not anchored and j > 5:
                    spec["kind"] = "interaction"
            specs.append(spec)
    return specs


def coverage(specs, n):
    got = set()
    for s in specs:
        got.update(s.get("para") or [])
    return got == set(range(1, n + 1))


# ---- 1. caps：极端不可行（12 章 × 8 锚定节）→ 每章 ≤6、覆盖保住、章数放开 ----
extreme = make_specs([("导入", 1)] + [(f"章{i}", 8) for i in range(1, 11)] + [("总结作业", 1)], anchored=True)
extreme_out = _enforce_chapter_caps(extreme)
ext_chs = _derive_chapters(extreme_out)
ok("caps.extreme 每章≤6", all(len(c["idxs"]) <= 6 for c in ext_chs),
   str(chapters_summary(extreme_out)))
ok("caps.extreme 锚定节零丢弃", len(extreme_out) == len(extreme), f"{len(extreme_out)} vs {len(extreme)}")

# ---- 2. caps：中等可压缩（11 章 × 5 节 = 中间 45 节 → 8 章）----
moderate = make_specs([("导入", 1)] + [(f"章{i}", 5) for i in range(1, 10)] + [("总结作业", 1)], anchored=True)
moderate_out = _enforce_chapter_caps(moderate)
mod_chs = _derive_chapters(moderate_out)
ok("caps.moderate 章≤10", len(mod_chs) <= MAX_CHAPTERS, str(chapters_summary(moderate_out)))
ok("caps.moderate 每章≤6", all(len(c["idxs"]) <= MAX_SECTIONS_PER_CHAPTER for c in mod_chs),
   str(chapters_summary(moderate_out)))
ok("caps.moderate 节零丢弃", len(moderate_out) == len(moderate))

# ---- 3. caps：单章 7 锚定节 → （续）拆章 ----
split_in = make_specs([("导入", 1), ("课文精讲", 7), ("总结作业", 1)], anchored=True)
split_out = _enforce_chapter_caps(split_in)
sp_chs = _derive_chapters(split_out)
ok("caps.split 锚定章拆（续）", any("（续）" in c["label"] for c in sp_chs) and all(len(c["idxs"]) <= 6 for c in sp_chs),
   str(chapters_summary(split_out)))
ok("caps.split 覆盖保住", coverage(split_out, 7))

# ---- 4. caps：超章含可丢节 → 优先丢节 ----
drop_in = make_specs([("导入", 1), ("课堂活动", 9), ("总结作业", 1)], anchored=False)
drop_out = _enforce_chapter_caps(drop_in)
dr_chs = _derive_chapters(drop_out)
ok("caps.drop 丢节到≤6", all(len(c["idxs"]) <= 6 for c in dr_chs) and len(drop_out) < len(drop_in),
   str(chapters_summary(drop_out)))

# ---- 5. fallback：任意段数下 章≤10、每章≤6、全覆盖 ----
def fake_slices(n):
    return [{"index": i, "word_count": 40, "preview": f"p{i}", "difficult_words": ["w"] if i == 1 else [], "long_sentences": []} for i in range(1, n + 1)]

for n in (4, 7, 13, 24, 60):
    fb = _fallback_blueprint(fake_slices(n))
    fb_chs = _derive_chapters(fb)
    ok(f"fallback n={n} 章≤10", len(fb_chs) <= MAX_CHAPTERS, str(chapters_summary(fb_chs)))
    ok(f"fallback n={n} 每章≤6", all(len(c["idxs"]) <= 6 for c in fb_chs), str(chapters_summary(fb_chs)))
    ok(f"fallback n={n} 段落全覆盖", coverage(fb, n))

# ---- 6. normalize：嵌套 chapters 形态 + 上限强制 + 旧平面形态 ----
nested = {"chapters": [
    {"title": "导入", "sections": [{"kind": "cover"}, {"kind": "agenda"}]},
    {"title": "词汇预教", "sections": [{"kind": "vocab"}]},
    {"title": "课文精讲", "sections": [
        {"kind": "text_anatomy", "para": 1}, {"kind": "lang_points", "para": 1},
        {"kind": "text_anatomy", "para": 2}, {"kind": "lang_points", "para": 2},
        {"kind": "text_anatomy", "para": 3}, {"kind": "lang_points", "para": 3},
        {"kind": "text_anatomy", "para": 4}, {"kind": "lang_points", "para": 4},
    ]},
    {"title": "课堂活动", "sections": [{"kind": "interaction"}]},
    {"title": "总结作业", "sections": [{"kind": "summary"}]},
]}
norm, why = _normalize_blueprint(nested, n_paras=4)
ok("normalize.nested 通过", norm is not None and why == "", why)
if norm:
    nm_chs = _derive_chapters(norm)
    ok("normalize.nested 章数", [c["label"] for c in nm_chs] == ["导入", "词汇预教", "课文精讲", "课文精讲（续）", "课堂活动", "总结作业"],
       str(chapters_summary(norm)))
    ok("normalize.nested 每章≤6", all(len(c["idxs"]) <= 6 for c in nm_chs))
    ok("normalize.nested 覆盖", coverage(norm, 4))

legacy = {"pages": [{"kind": "cover"}, {"kind": "vocab"}]
          + [{"kind": "text_anatomy", "para": i} for i in range(1, 4)]
          + [{"kind": "lang_points", "para": i} for i in range(1, 4)]
          + [{"kind": "summary"}]}
lg, lwhy = _normalize_blueprint(legacy, n_paras=3)
ok("normalize.legacy 通过", lg is not None and lwhy == "", lwhy)
if lg:
    ok("normalize.legacy 按节型派生章", [c["label"] for c in _derive_chapters(lg)] == ["导入", "词汇预教", "课文精讲", "总结作业"],
       str(chapters_summary(lg)))

bad = {"chapters": [{"title": "x", "sections": [{"kind": "text_anatomy", "para": 1}]}]}
_, bwhy = _normalize_blueprint(bad, n_paras=3)
ok("normalize.缺覆盖拒绝", bwhy != "", bwhy)

# ---- 7. 拼装：章结构 / 节重编 / 标记替换 ----
pages = [_ContentPage(title=f"节{i}", intent="教学意图", html='<div class="page-focus"><p>内容</p></div>')
         for i in range(len(norm))]
html = _assemble_skeleton("测试课件", "#3a6ea5", pages, blueprint=norm)
n_ch = html.count('<section class="oe-chapter"')
secs = [int(x) for x in re.findall(r'data-sec="(\d+)"', html)]
ok("assemble 章数一致", n_ch == len(_derive_chapters(norm)), f"{n_ch} vs {len(_derive_chapters(norm))}")
ok("assemble 节序重编 1..N", secs == list(range(1, len(norm) + 1)), str(secs))
ok("assemble 标记全替换", "__TITLE__" not in html and "__TOKEN_BLOCK__" not in html
   and "__THEME_EXTRA__" not in html and "<!--SECTIONS-->" not in html)
ok("assemble 滚动骨架特征", "oe-chapter" in html and "oe-toc" in html and ".page{" not in html)
ok("assemble TOC 数据源", html.count('data-section=') >= n_ch)

print(f"\n{PASS} 项通过")
sys.exit(0 if PASS else 1)
