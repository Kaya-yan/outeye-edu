"""S4 蓝图可编辑真实 LLM 冒烟：规划蓝图 → 模拟教师编辑（删页/改意图）→ 教师蓝图直通逐页生成"""

import sys
import time

sys.path.insert(0, ".")

from app.core.config import settings
from app.services.courseware_llm_generator import (
    _plan_blueprint,
    _slice_analysis,
    _split_paragraphs,
    generate_html_courseware,
)
from app.services.rag import RAGGenerator

TEXT = """This is the story of a sturdy American symbol which has now spread throughout most of the world. The symbol is not the dollar. It is not even Coca-Cola. It is a simple pair of American blue jeans.

Blue jeans are favored equally by bureaucrats and cowboys; they appear on the pages of Vogue as well as on the backs of Iowa farmers. In Europe and Asia, they are a status symbol of the "American way of life." Yet their origins are humble: they were born in the gold camps of the California Gold Rush, stitched together by a peddler named Levi Strauss and a tailor named Jacob Davis, who patented the idea of riveting the pockets so that miners could carry nuggets without tearing the cloth."""

PLAN = {
    "framework": "精读课：先激活背景，再逐段细读，最后迁移写作",
    "objectives": [{"text": "理解并复述牛仔裤如何从矿工工装变成美国象征", "bloom": "理解"}],
    "activity_designs": [
        {"name": "导入与预测", "duration": "10 分钟", "objective": "激活背景图式", "steps": "看标题预测内容"},
        {"name": "逐段精读", "duration": "25 分钟", "objective": "细读修辞与语言点", "steps": "逐段阅读"},
        {"name": "读后讨论", "duration": "15 分钟", "objective": "批判性思维", "steps": "小组讨论"},
    ],
}

ANALYSIS = {
    "vocabulary": {"total_words": 130, "unique_words": 85, "difficult_words": [
        {"word": "sturdy", "level": "B2", "count": 1, "in_awl": False},
        {"word": "rivet", "level": "C1", "count": 1, "in_awl": False},
    ]},
    "syntax": {"total_sentences": 8, "avg_sentence_length": 18, "max_sentence": {"preview": "...", "word_count": 22, "index": 0}},
    "discourse": {"paragraph_count": 2, "connective_density": 3.1, "genre_hint": "说明文"},
}

messages: list = []


def on_progress(msg: str) -> None:
    messages.append(msg)
    print(f"[progress] {msg}")


fails: list = []

# 阶段一：规划（模拟 POST /courseware/blueprint 的服务层）
generator = RAGGenerator(
    api_key=settings.LLM_API_KEY,
    api_base=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL,
    max_tokens=2500,
    temperature=0.5,
)
paragraphs = _split_paragraphs(TEXT)
slices = _slice_analysis(paragraphs, ANALYSIS)
t0 = time.time()
pages, accent, source, note = _plan_blueprint(
    generator,
    title="The Jeaning of America（节选）",
    plan=PLAN,
    analysis=ANALYSIS,
    slices=slices,
    language_name="英语",
    duration_minutes=50,
    course_type="精读",
    teaching_intent="侧重长难句解剖与排除法修辞的迁移写作",
)
plan_elapsed = round(time.time() - t0, 1)
print(f"\n规划完成：{len(pages)} 页 | source={source} | accent={accent} | 耗时 {plan_elapsed}s")
if source != "llm":
    fails.append(f"规划器 source={source}：{note}")

# 阶段二：模拟教师编辑（改封面意图 + 删互动页），确认后直通生成
edited = []
for p in pages:
    if p["kind"] == "interaction":
        continue  # 教师删除互动页
    q = dict(p)
    if q["kind"] == "cover":
        q["intent"] = "教师改写：以美国符号悬念开场，激发预测"
    edited.append(q)
print(f"教师编辑后：{len(edited)} 页（删除互动页 1 页，改封面意图）")

t1 = time.time()
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
    blueprint=edited,
    accent=accent,
    progress_cb=on_progress,
)
gen_elapsed = round(time.time() - t1, 1)

sc = result.self_check
print("\n===== 自检摘要 =====")
print("fallback:", result.fallback, "| plan:", plan_elapsed, "s | generate:", gen_elapsed, "s")
print("pages:", sc.get("pages_count"), "| blueprint source:", sc.get("blueprint", {}).get("source"))
print("interaction kinds:", [p["kind"] for p in sc.get("blueprint", {}).get("pages", [])])
print("interactions:", sc.get("interaction_types"))
print("regen/sanitize/stub:", sc.get("regenerated_pages"), sc.get("sanitized_pages"), sc.get("stub_pages"))

out = "scripts/_smoke_blueprint.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(result.html)
print(f"\nHTML 已写入 {out}（{len(result.html)} 字符）")

if result.fallback:
    fails.append("整体回退 bootstrap")
if sc.get("blueprint", {}).get("source") != "teacher":
    fails.append(f"蓝图来源非 teacher：{sc.get('blueprint', {}).get('source')} / {sc.get('blueprint', {}).get('note')}")
if sc.get("pages_count") != len(edited):
    fails.append(f"页数 {sc.get('pages_count')} ≠ 教师蓝图 {len(edited)}")
if sc.get("stub_pages") or sc.get("sanitized_pages"):
    fails.append(f"兜底/净化页：{sc.get('stub_pages')} {sc.get('sanitized_pages')}")
if not any("已采用教师确认蓝图" in m for m in messages):
    fails.append("进度文案缺少教师蓝图提示")
cover_intent = next((pi["intent"] for pi in sc.get("page_intents", []) if pi["page"] == 1), "")
if "教师改写" not in cover_intent:
    fails.append(f"封面意图未采用教师编辑：{cover_intent}")
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else "PASS")
