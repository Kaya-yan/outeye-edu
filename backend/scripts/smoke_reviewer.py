"""S5 教研员评审真实 LLM 冒烟：两阶段生成 + 逐页复核，验证评审摘要与低分页重写"""

import sys
import time

sys.path.insert(0, ".")

from app.services.courseware_llm_generator import generate_html_courseware

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
elapsed = round(time.time() - t0, 1)

sc = result.self_check
print("\n===== 自检摘要 =====")
print("fallback:", result.fallback, "| duration:", elapsed, "s | pages:", sc.get("pages_count"))
print("interactions:", sc.get("interaction_types"))
print("regen/sanitize/stub:", sc.get("regenerated_pages"), sc.get("sanitized_pages"), sc.get("stub_pages"))
rv = sc.get("reviewer") or {}
print("reviewer version:", rv.get("version"), "| pass_score:", rv.get("pass_score"), "| avg:", rv.get("avg_score"))
for p in rv.get("pages", []):
    problems = "；".join(p.get("problems") or [])[:80]
    print(f"  第{p['page']}页 score={p.get('score')} verdict={p.get('verdict')} rewrites={p.get('rewrites')} {problems}")
vq = sc.get("visual_qc") or {}
print("visual_qc enabled:", vq.get("enabled"), "| skipped:", vq.get("skipped"), "| error:", vq.get("error"),
      "| checked:", vq.get("checked_pages"), "| issues:", vq.get("issue_pages"))
cr = sc.get("consistency_review") or {}
print("consistency enabled:", cr.get("enabled"), "| replaced:", cr.get("total_replaced"),
      "| rolled_back:", cr.get("rolled_back"), "| note:", cr.get("note"), "| error:", cr.get("error"))
for t in cr.get("terminology") or []:
    print("  术语组:", t.get("canonical"), "←", t.get("variants"))
for n in cr.get("structure_notes") or []:
    print("  结构意见:", n)

fails: list = []
if result.fallback:
    fails.append("整体回退 bootstrap")
if rv.get("avg_score") is None:
    fails.append("评审层未产出任何分数")
if len(rv.get("unreviewed_pages") or []) > len(rv.get("pages") or []) / 2:
    fails.append(f"过半页面未复核：{rv.get('unreviewed_pages')}")
if not any("AI 教研员正在复核页面质量" in m for m in messages):
    fails.append("进度文案缺少复核提示")
if not any("正在复核：第" in m for m in messages):
    fails.append("进度文案缺少逐页复核页号")
if cr.get("error"):
    fails.append(f"全局审校异常：{cr.get('error')}")

out = "scripts/_smoke_reviewer.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(result.html)
print(f"\nHTML 已写入 {out}（{len(result.html)} 字符）")
print("\n冒烟结论:", "FAIL — " + "; ".join(fails) if fails else "PASS")
