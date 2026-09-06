"""③ 两阶段 HTML 课件真实 LLM 冒烟：The Jeaning of America 前两段，验证规划→逐页→拼装全链路"""

import asyncio
import json
import sys
import time

sys.path.insert(0, ".")

from app.services.courseware_llm_generator import generate_html_courseware

TEXT = """This is the story of a sturdy American symbol which has now spread throughout most of the world. The symbol is not the dollar. It is not even Coca-Cola. It is a simple pair of American blue jeans.

Blue jeans are favored equally by bureaucrats and cowboys; they appear on the pages of Vogue as well as on the backs of Iowa farmers. In Europe and Asia, they are a status symbol of the "American way of life." Yet their origins are humble: they were born in the gold camps of the California Gold Rush, stitched together by a peddler named Levi Strauss and a tailor named Jacob Davis, who patented the idea of riveting the pockets so that miners could carry nuggets without tearing the cloth."""

PLAN = {
    "framework": "精读课：先激活背景，再逐段细读，最后迁移写作",
    "objectives": [
        {"text": "理解并复述牛仔裤如何从矿工工装变成美国象征", "bloom": "理解"},
        {"text": "掌握排除法引出主题的写作手法并迁移到自己的写作", "bloom": "应用"},
        {"text": "在语境中习得 sturdy / spread / rivet 等核心词汇", "bloom": "记忆"},
    ],
    "activity_designs": [
        {"name": "导入与预测", "duration": "10 分钟", "objective": "激活背景图式", "steps": "看标题预测内容；快速浏览首段验证预测"},
        {"name": "逐段精读", "duration": "25 分钟", "objective": "细读修辞与语言点", "steps": "逐段阅读；长难句解剖；语言点操练"},
        {"name": "读后讨论", "duration": "15 分钟", "objective": "批判性思维", "steps": "小组讨论美国符号现象；代表汇报"},
    ],
    "assessment": {"formative": ["课堂问答", "段落主旨概括"], "summative": ["写作迁移：排除法介绍一个中国符号"]},
}

ANALYSIS = {
    "vocabulary": {"total_words": 130, "unique_words": 85, "difficult_words": [
        {"word": "sturdy", "level": "B2", "count": 1, "in_awl": False},
        {"word": "spread", "level": "B1", "count": 1, "in_awl": False},
        {"word": "symbol", "level": "B1", "count": 2, "in_awl": False},
        {"word": "rivet", "level": "C1", "count": 1, "in_awl": False},
        {"word": "peddler", "level": "C1", "count": 1, "in_awl": False},
    ]},
    "syntax": {"total_sentences": 8, "avg_sentence_length": 18, "max_sentence": {"preview": "This is the story of a sturdy American symbol...", "word_count": 22, "index": 0}},
    "discourse": {"paragraph_count": 2, "connective_density": 3.1, "genre_hint": "说明文"},
}

messages: list = []


def on_progress(msg: str) -> None:
    messages.append(msg)
    print(f"[progress] {msg}")


t0 = time.time()
result = generate_html_courseware(
    title="The Jeaning of America（节选）",
    plan=PLAN,
    analysis=ANALYSIS,
    text=TEXT,
    language_name="英语",
    text_level="B2",
    student_level="B2",
    duration_minutes=50,
    course_type="精读",
    class_size=32,
    native_language="中文",
    theme="humanities",
    teaching_intent="侧重长难句解剖与排除法修辞的迁移写作",
    progress_cb=on_progress,
)
elapsed = time.time() - t0

sc = result.self_check
print("\n===== 自检摘要 =====")
print("fallback:", result.fallback, "| duration:", round(elapsed, 1), "s")
print("pages:", sc.get("pages_count"), "| blueprint source:", sc.get("blueprint", {}).get("source"))
for p in sc.get("blueprint", {}).get("pages", []):
    print("  ", p)
print("accent:", sc.get("accent"), "| note:", sc.get("accent_note"))
print("interactions:", sc.get("interaction_types"))
print("regen/sanitize/stub:", sc.get("regenerated_pages"), sc.get("sanitized_pages"), sc.get("stub_pages"))

out = "scripts/_smoke_two_stage.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(result.html)
print(f"\nHTML 已写入 {out}（{len(result.html)} 字符）")

fails = []
if result.fallback:
    fails.append("整体回退 bootstrap")
if sc.get("stub_pages"):
    fails.append(f"兜底页：{sc['stub_pages']}")
if sc.get("sanitized_pages"):
    fails.append(f"净化页：{sc['sanitized_pages']}")
bp = sc.get("blueprint", {})
if bp.get("source") != "llm":
    fails.append(f"规划器来源 {bp.get('source')}：{bp.get('note')}")
kinds = [p["kind"] for p in bp.get("pages", [])]
if "cover" not in kinds or "summary" not in kinds or "deep_reading" not in kinds:
    fails.append(f"页型不全：{kinds}")
if "anatomy" not in (sc.get("interaction_types") or []):
    fails.append("全副无长难句解剖组件")
if not any("精讲页" in m for m in messages):
    fails.append("进度文案缺少页类型")
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else "PASS")
