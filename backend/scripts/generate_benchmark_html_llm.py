"""M4 benchmark 的 LLM 课件生成脚本（消耗 token，默认只 dry-run）。

为 30 个不同课文生成平台 HTML 课件，供 V2 编辑器 benchmark 使用。
默认 dry-run 只打印计划；加 --run 才真正调用 LLM（预计 30 次 × 30-40s）。

用法:
  venv/Scripts/python.exe scripts/generate_benchmark_html_llm.py --run [--n 30] [--out DIR]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 12 篇风格各异的短教学文本，循环补足到 N 个（标题加序号区分）
CORPUS = [
    ("The Ocean's Breath", """The ocean moves in rhythms older than any language. Twice a day, tides rise and fall, pulled by the moon and pushed by the sun. Sailors who learned to read these rhythms crossed oceans long before maps existed.
Waves begin as wind. A breeze brushing the surface leaves ripples; a storm can stack water into walls thirty meters high. When a wave reaches shallow water, its bottom drags against the sea floor, the top overtakes, and it collapses in a curl of white foam.
Yet the ocean's deepest secret is not motion but stillness. Below the storm layer lies a world of slow currents, moving water across the planet over centuries. Scientists call it the global conveyor belt. It carries heat from the equator toward the poles, and without it, Europe would be far colder than it is.
The ocean, in other words, does not merely surround us. It regulates the air we breathe, the rain that feeds our crops, and the climate we argue about. To study it is to study the planet's heartbeat."""),
    ("A Letter to My Younger Self", """Dear fourteen-year-old me,
I write to you from a desk you cannot imagine yet, in a city you have never visited. Do not worry about the spelling test on Friday. I know it feels enormous. It is not.
Here is what matters instead: the friend who sits alone at lunch will remember your kindness for decades, long after both of you forget the test existed. The book you are ashamed to love—yes, that one about dragons—will teach you more about courage than any lecture.
You will fail at things you worked hard for, and succeed at things you never planned. This is not injustice; it is life refusing to follow a syllabus. Learn to revise your expectations the way you revise an essay: keep the structure, cut the sentences that lie.
One more thing. Call grandmother more often. You believe there will be time. There is less than you think, and it goes faster than any teacher warns you.
With more patience than you have now,
Yourself"""),
    ("Why Cities Grow Upward", """For most of human history, cities spread outward because gravity was cheap and land was cheaper. Buildings stayed low, streets grew long, and walking was the price of distance.
The elevator changed that equation. In 1853, Elisha Otis demonstrated a safety brake that kept an elevator from falling even if the cable snapped. Within decades, Manhattan reached for the sky. Height, suddenly, was safer than sprawl.
Tall buildings solve one problem by creating others. A tower packs thousands of people onto a small footprint, which makes public transport viable and shops busy. But towers also block light, strain water systems, and concentrate wealth in dramatic views.
The newest generation of skyscrapers tries to answer these complaints with engineering: glass that generates power, gardens every ten floors, water recycled through the building's veins. Whether such towers become good neighbors or merely tall ones depends on rules written by cities, not by architects.
Urban height, in the end, is a bargain between ambition and livability. Every skyline is that argument frozen in concrete and glass."""),
    ("The Science of Sleep", """Sleep was once a scientific embarrassment: a state in which every animal becomes defenseless for hours, which evolution should have eliminated. Yet every creature studied, from fruit flies to whales, sleeps in some form.
The reason appears to be maintenance. During deep sleep, the brain's waste-clearance system accelerates, flushing out proteins that accumulate during waking hours. Sleep is also when the brain files the day's memories, moving them from temporary storage into long-term circuits.
Deprivation experiments show the cost of skipping this work. After one sleepless night, attention fragments and reaction time slows to the level of mild intoxication. Chronic short sleep is associated with weakened immunity, weight gain, and impaired emotional control.
Teenagers face a particular trap: their internal clocks shift later, while school schedules do not. A sixteen-year-old's body wants sleep at midnight, but the first class often begins at eight.
The practical advice is unglamorous. Keep a constant wake time. Avoid screens before bed, not because they are evil, but because their light tells the brain the day is not over. Treat sleep not as lost time, but as the third pillar of health beside diet and exercise."""),
    ("Coffee: A Short History", """Coffee began as a legend about dancing goats. An Ethiopian shepherd, the story goes, noticed his animals leaping after eating red berries from a certain bush. Monks nearby brewed the berries to stay awake through night prayers.
From Ethiopia, coffee crossed the Red Sea to Yemen, where cultivation began in the fifteenth century. The port of Mocha gave its name to a bean that conquered the world. Coffee houses followed the drink: in Mecca, then Cairo, then Istanbul, rooms filled with argument, chess, and poetry.
Europeans first called coffee a Muslim drink and some rulers tried to ban it. The bans failed. By the seventeenth century, London alone had hundreds of coffee houses, each a hub for merchants, scientists, and gossip. Lloyd's of London, the insurance market, began in one.
The industrial revolution turned coffee into a commodity and colonies into plantations. Brazil's rise as a producer reshaped the global economy and the Atlantic slave trade, a chapter too often missing from the legend of dancing goats.
Today coffee is the world's second most traded good by some measures, after oil. Every cup carries this history: a goat herder's observation, a monk's discipline, a merchant's risk, and a picker's labor."""),
    ("Learning a Language Late", """They say children learn languages effortlessly and adults cannot. The first claim is exaggerated; the second is simply false.
Children have advantages: thousands of exposure hours, forgiving listeners, and brains that prune sounds slowly. But adults hold cards children lack: literacy, an organized understanding of grammar, and decades of world knowledge to attach new words to.
Research on immersion learners shows a consistent pattern. Adults progress faster in the first year of study; children pull ahead over many years because they keep going. Persistence, not age, separates fluent speakers from stalled ones.
The real obstacles for adults are logistical and emotional. Time is scarce, and embarrassment is expensive. A child accepts being corrected a hundred times a day; an adult feels each correction as a verdict.
The practical conclusions are hopeful. Short daily practice beats weekend marathons, because memory consolidates between sessions. Mistakes are not evidence of failure but the primary fuel of learning. And a language learned at fifty may be spoken with an accent, but with a richness of things to say that no seven-year-old can match."""),
    ("The Story of Paper", """Before paper, knowledge lived on materials that fought back. Clay tablets were durable but heavy; silk was light but ruinously expensive; papyrus grew only along the Nile.
Paper, invented in China around the first century, began as a craft of rags, bark, and water beaten into pulp. The technique traveled slowly—centuries to reach Korea and Japan, more centuries westward through the Islamic world, reaching Europe only in the twelfth century.
Wherever paper arrived, literacy followed it. Islamic scholars used it to build libraries of hundreds of thousands of volumes. European universities could not have existed without cheap pages for students to copy, annotate, and argue over.
The printing press then multiplied paper's power. A single press could produce more pages in a day than a scribe managed in a year, and the price of ideas collapsed. Reformation, scientific revolution, and mass literacy all rode on sheets of pressed fiber.
The digital age promised the paperless office and delivered more paper than ever, before finally bending the curve. Yet even now, readers remember better from paper than screens—so this ancient technology, born from rags and river water, still holds a small seat at the table of knowledge."""),
    ("Ants: The First Farmers", """Long before humans planted seeds, ants were farming. Certain ant species have grown fungus gardens underground for over fifty million years, tending their crops with a dedication any farmer would recognize.
The leafcutter ants of the Americas do not eat the leaves they cut. They carry the fragments home, chew them into mulch, and use it to cultivate a fungus found nowhere in nature outside their nests. The fungus is their food; the ants are its roots, wings, and defenders.
This partnership is enforced by chemistry. The ants carry bacteria that produce antibiotics, protecting the garden from invasive molds. It is agriculture with pesticides, invented epochs before any human field existed.
Ants also keep livestock. Aphids sip plant sap and excrete sugar-rich honeydew, which some ants milk, protect, and even carry to new pastures. In winter, certain species shelter aphid eggs in their nests.
None of this involves intelligence as we understand it. Each ant follows simple rules; the sophisticated farm emerges from the colony. It is a humbling thought: civilization, in the sense of agriculture and animal husbandry, has been invented more than once on this planet, and not first by us."""),
    ("The Invention of Tomorrow", """Every language has a word for yesterday; not every language has a grammar for tomorrow. Linguists studying ancient texts note that futures were often optional—spoken of as wishes or fates rather than plans.
The future became a place, somewhere one could travel by preparation, only slowly. The first calendars tied tomorrow to the sky: floods, harvests, eclipses returned on schedules the patient could learn. Prediction became power.
Finance turned the future into a market. Merchants in Renaissance Italy traded promises—delivery of grain next spring, repayment of a loan next year—and modern economies still run on these promises. An interest rate is simply the price of tomorrow's money.
Science then made forecasting a discipline. Weather services, population projections, and climate models sell the future with error bars attached, honest about uncertainty in a way prophecy never was.
Perhaps that is the quiet achievement of modernity: not that we predict tomorrow better than oracles did, but that we argue about the predictions with data. The future is no longer fate or fantasy. It is a draft, revisable—and for the first time in history, we admit it."""),
    ("Bridges", """A bridge is a negotiated truce between gravity and human purpose. Everything about one—its shape, its materials, its lifespan—is a way of moving weight across emptiness.
The oldest answers were beams: a log across a stream, weight pressing straight down. Arches came next, turning downward force into sideways push, which is why Roman engineers needed banks of stone to lean against. Their bridges still stand because compression suits stone perfectly.
Steel and tension inverted the logic. A suspension bridge hangs its deck from cables that carry pull, not push—the material's strength stretched rather than squeezed. Steel's tolerance for tension let spans grow from hundreds of meters to kilometers.
Each design is an argument written in physics, and failures are the debate's sharper sentences. A bridge that flexes too little snaps; one that flexes too freely resonates with the wind. Engineers learn from wrecks as much as from works.
The next generation carries more than traffic. Some will harvest tidal energy; some will host gardens and shops, becoming streets that happen to cross water. The truce with gravity continues, but the purpose on the far bank keeps changing."""),
    ("The Color Blue", """Look at the sky and name its color. Now search the oldest written texts: Homer's sea is 'wine-dark,' and ancient Chinese, Icelandic, and Indian epics describe the world without ever calling the sky blue.
Some scholars conclude ancient people were colorblind; the more careful conclusion is linguistic. Blue rarely appears on earth—few plants or animals are truly blue—so languages adopted words for it late, usually after developing terms for black, white, red, green, and yellow.
Once a culture has the word, the color becomes visible as a category. Egyptian artisans manufactured blue pigment five thousand years ago, grinding lapis lazuli into paint for gods and royalty. Blue was sacred precisely because it was scarce.
Modern chemistry democratized it. Synthetic ultramarine and denim dyes made blue the color of work clothes and jeans, of corporate logos and links on every webpage. Scarcity's child became ubiquity's uniform.
The lesson travels beyond color. Perception is trained by vocabulary and by tools. We see what our words and industries have taught us to see—and the history of one color is a small reminder that even the sky needed a word before it was blue."""),
    ("Running on Two Legs", """Humans are mediocre sprinters. A house cat accelerates faster; a dog holds speed longer. Yet over distances beyond twenty kilometers, no animal on earth can keep pace with a healthy, trained human.
The secret is bipedal running combined with sweating. Four-legged animals bound efficiently but must pant to cool, and panting fails at a gallop. Humans shed heat through millions of sweat glands while breathing steadily on two legs, turning us into the planet's best endurance machines.
Some anthropologists link this anatomy to hunting: persistent hunters ran antelope to exhaustion in the midday heat, tracking a trotting animal until it collapsed. Running, on this view, is not exercise we invented but an inheritance we abandoned.
The modern marathon reenacts the inheritance in ritual form. Watch amateur runners at kilometer thirty: exhausted, overheated, still moving—machines doing what they were built for.
There is a quieter lesson for anyone learning a difficult skill. Endurance beats intensity across long distances. The tribe that could keep going, not the one that ran fastest, caught the dinner and, eventually, the world."""),
]


def build_synth_analysis(title: str) -> dict:
    return {
        "vocabulary": {"total_words": 260, "unique_words": 150, "cefr_distribution": {"B1": 90, "B2": 70, "C1": 55, "unknown": 5}, "awl_count": 12, "difficult_words": []},
        "syntax": {"total_sentences": 22, "avg_sentence_length": 18.5, "long_sentences_count": 3, "flesch_reading_ease": 48},
        "discourse": {"paragraph_count": 5, "connective_density": 0.05, "genre_hint": "expository"},
        "learner_gap": {"text_level": "B2", "student_level": "B1", "gap": "B1→B2", "gap_description": "学术词汇与长难句为主要差距"},
    }


def build_synth_plan(title: str, seq: int) -> dict:
    return {
        "framework": "PWP" if seq % 2 == 1 else "TBLT",
        "objectives": [
            {"text": "识别并运用本课 8 个核心学术词汇", "bloom": "Understand"},
            {"text": "分析文章结构并复述主要论点", "bloom": "Analyze"},
            {"text": "就话题进行小组讨论并表达立场", "bloom": "Create"},
        ],
        "difficulty_overview": f"{title} 为说明性文本，词汇密度中等，长难句集中在第 2、4 段。",
        "teaching_suggestions": ["采用图示组织者梳理篇章结构", "词汇教学结合语境猜词策略"],
        "activity_designs": [
            {"name": "Lead-in 导入", "objective": "激活背景图式", "steps": "展示图片，提问预测主题；两人小组分享观点。", "duration": "8 分钟", "assessment": "口头回答"},
            {"name": "While-reading 读中", "objective": "获取主旨与结构", "steps": "略读匹配段落大意；精读完成结构图。", "duration": "25 分钟", "assessment": "结构图完成度"},
            {"name": "Post-task 产出", "objective": "迁移运用", "steps": "小组就话题完成口头报告，全班互评。", "duration": "20 分钟", "assessment": "量规评价"},
        ],
        "assessment": {"formative": ["结构图", "口头报告"], "summative": ["课后词汇练习"]},
        "differentiation": "为基础较弱学生提供词汇表；为较强学生增加批判性追问。",
        "theoretical_basis": "输入假说与任务型教学结合。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--run", action="store_true", help="真正调用 LLM（消耗 token）")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "scripts", "v2benchmark", "samples"))
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "llm-manifest.json")
    manifest = []
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    done_files = {m["file"] for m in manifest}

    plan_list = []
    for i in range(1, args.n + 1):
        title, text = CORPUS[(i - 1) % len(CORPUS)]
        title = f"{title} ({(i - 1) // len(CORPUS) + 1})" if i > len(CORPUS) else title
        plan_list.append((i, title, text))

    if not args.run:
        print(f"[dry-run] 将为 {len(plan_list)} 篇课文生成 HTML 课件（每篇 1 次 LLM 调用，约 30-40s）")
        for i, title, text in plan_list[:5]:
            print(f"  {i:02d}. {title} ({len(text.split())} words)")
        print("  ...")
        print("加 --run 执行。")
        return

    from app.services.courseware_llm_generator import generate_html_courseware

    try:
        from app.services.courseware_seed import OFFICIAL_COMPONENTS
    except Exception:
        OFFICIAL_COMPONENTS = []

    for i, title, text in plan_list:
        name = f"llm-{i:02d}.html"
        if name in done_files:
            print(f"[skip] {name} 已存在")
            continue
        t0 = time.time()
        result = generate_html_courseware(
            title=title,
            plan=build_synth_plan(title, i),
            analysis=build_synth_analysis(title),
            text=text,
            language_name="英语",
            text_level="B2",
            student_level="B1",
            duration_minutes=45,
            course_type="阅读课",
            class_size=40,
            native_language="中文",
            components=[c for c in OFFICIAL_COMPONENTS],
        )
        html = result.html
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(html)
        manifest.append(
            {
                "file": name,
                "kind": "llm",
                "title": title,
                "fallback": result.fallback,
                "model": result.model,
                "seconds": round(time.time() - t0, 1),
                "bytes": len(html.encode("utf-8")),
            }
        )
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"[done] {name} fallback={result.fallback} {round(time.time() - t0, 1)}s {len(html)} chars")

    print(f"完成：{len(manifest)} 个 LLM 样本 -> {out_dir}/llm-manifest.json")


if __name__ == "__main__":
    main()
