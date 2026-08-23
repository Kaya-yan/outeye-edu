"""
提示词回归测试（FIX-2 · F2.5）

从数据库取最近 3 篇不同标题的分析记录课文，跑"白盒分析 → 教案生成"全链路
（跳过双源检索，置空以保持可比），产物写入 regression_runs/<时间戳>/：

  - plan_<n>_prompt.txt    实际发送的用户 Prompt（改模板后 diff 对比）
  - plan_<n>_result.json   解析后的教案结构（框架/目标/环节/评估/self_check）
  - summary.txt            汇总表 + 人工评估清单

用法：cd backend && python -X utf8 scripts/prompt_regression.py
判定标准（人工评估清单）：
  1. 教学目标 3-5 条且可测量（无"了解/掌握/熟悉"空泛动词）
  2. 课堂环节 4-6 个，时间总和 = 90 分钟
  3. 形成性评估点 ≥2 且嵌入具体环节；终结性 ≥2
  4. 建议条目均带数据依据（含具体指标数值）与理论依据
  5. 反复制粘贴抽查：环节材料不整段照抄课文
"""

import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

OUT_ROOT = Path(__file__).resolve().parent.parent / "regression_runs"


async def load_texts(count: int = 3) -> list:
    """取最近 N 篇不同标题、有正文的分析记录"""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.analysis import AnalysisRecord

    async with AsyncSessionLocal() as db:
        records = (
            await db.execute(
                select(AnalysisRecord)
                .where(AnalysisRecord.text_content.isnot(None))
                .order_by(AnalysisRecord.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        seen, picked = set(), []
        for r in records:
            if r.text_title in seen or not (r.text_content or "").strip():
                continue
            seen.add(r.text_title)
            picked.append((r.text_title, r.text_content))
            if len(picked) == count:
                break
        return picked


def build_analysis_dict(result) -> dict:
    """与 /generate-plan 端点同构的分析字典（键名与白盒产出一致，直传）"""
    return {
        "text_level": result.text_level,
        "language": result.language,
        "language_name": result.language_name,
        "vocabulary": {
            "total_words": result.vocabulary.total_words,
            "unique_words": result.vocabulary.unique_words,
            "cefr_distribution": result.vocabulary.cefr_distribution,
            "awl_count": result.vocabulary.awl_count,
            "awl_ratio": result.vocabulary.awl_ratio,
            "difficult_words": [
                {"word": d.word, "level": d.level, "count": d.count, "in_awl": d.in_awl}
                for d in result.vocabulary.difficult_words
            ],
            "vocabulary_richness": result.vocabulary.vocabulary_richness,
        },
        "syntax": {
            "total_sentences": result.syntax.total_sentences,
            "avg_sentence_length": result.syntax.avg_sentence_length,
            "max_sentence": {
                "preview": result.syntax.max_sentence.preview,
                "word_count": result.syntax.max_sentence.word_count,
                "index": result.syntax.max_sentence.index,
            },
            "long_sentences_count": result.syntax.long_sentences_count,
            "very_long_sentences_count": result.syntax.very_long_sentences_count,
            "flesch_reading_ease": result.syntax.flesch_reading_ease,
        },
        "discourse": {
            "paragraph_count": result.discourse.paragraph_count,
            "connective_density": result.discourse.connective_density,
            "genre_hint": result.discourse.genre_hint,
        },
        "learner_gap": {
            "text_level": result.learner_gap.text_level,
            "student_level": result.learner_gap.student_level,
            "gap": result.learner_gap.gap,
            "gap_description": result.learner_gap.gap_description,
        },
        "enhancement_tags": result.enhancement_tags,
        "teaching_insights": result.teaching_insights,
        "cultural_elements": [
            {"category": e.category, "keyword": e.keyword, "explanation": e.explanation}
            for e in getattr(result, "cultural_elements", []) or []
        ],
    }


def run_one(title: str, text: str, out_dir: Path, index: int) -> dict:
    from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer
    from app.services.analysis.fusion_generator import (
        generate_teaching_plan,
        build_fusion_prompt,
    )

    analyzer = WhiteboxAnalyzer()
    result = analyzer.analyze(text, "B1", language=None)
    analysis_dict = build_analysis_dict(result)

    prompt = build_fusion_prompt(
        text_title=title,
        text_content=text,
        analysis=analysis_dict,
        wiki_context="",
        rag_context="",
        duration_minutes=90,
        course_type="精读",
        class_size=30,
        native_language="zh",
    )
    (out_dir / f"plan_{index}_prompt.txt").write_text(prompt, encoding="utf-8")

    plan = generate_teaching_plan(
        text_title=title,
        text_content=text,
        analysis=analysis_dict,
        wiki_results=[],
        rag_results=[],
        mode="enhanced",
        duration_minutes=90,
        course_type="精读",
        class_size=30,
        native_language="zh",
    )

    payload = asdict(plan)
    (out_dir / f"plan_{index}_raw.txt").write_text(plan.raw_response, encoding="utf-8")
    (out_dir / f"plan_{index}_result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    sc = plan.self_check or {}
    return {
        "title": title,
        "framework": plan.framework.splitlines()[0][:40] if plan.framework else "",
        "objectives": len(plan.objectives),
        "stages": len(plan.activity_designs),
        "time_sum": sc.get("time_sum_minutes", "?"),
        "time_ok": sc.get("time_matches_duration", "?"),
        "formative": len(plan.assessment.get("formative", [])),
        "summative": len(plan.assessment.get("summative", [])),
        "fallback": plan.fallback,
        "model": plan.model,
        "duration_s": plan.generation_duration,
    }


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    texts = asyncio.run(load_texts(count))
    if not texts:
        logger.error("数据库中没有可用课文，无法回归")
        raise SystemExit(1)

    out_dir = OUT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, (title, text) in enumerate(texts, 1):
        logger.info(f"[{i}/{len(texts)}] 生成：{title}")
        try:
            rows.append(run_one(title, text, out_dir, i))
        except Exception as e:
            logger.error(f"课文 {title} 生成失败: {e}")
            rows.append({"title": title, "error": str(e)})

    lines = [
        "提示词回归汇总（模板改动前后对比用）",
        "=" * 72,
        f"{'课文':<24}{'目标':<5}{'环节':<5}{'时间和':<7}{'形成':<5}{'终结':<5}{'降级':<5}{'耗时s':<6}",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"{r['title'][:20]:<24}ERROR: {r['error']}")
            continue
        lines.append(
            f"{r['title'][:20]:<24}{r['objectives']:<5}{r['stages']:<5}"
            f"{str(r['time_sum']):<7}{r['formative']:<5}{r['summative']:<5}"
            f"{str(r['fallback']):<5}{r['duration_s']:<6}"
        )
    lines += [
        "",
        "人工评估清单（逐篇核对）：",
        "1. 目标 3-5 条、可测量、无空泛动词；2. 环节 4-6 个、时间和=90；",
        "3. 形成性≥2 嵌入环节、终结性≥2；4. 建议带数据+理论依据；5. 无整段照抄课文。",
        "",
        "说明：本脚本跳过双源检索（wiki/rag 置空），只回归提示词与解析链路。",
    ]
    summary = "\n".join(lines)
    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"\n产物目录：{out_dir}")


if __name__ == "__main__":
    main()
