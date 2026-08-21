"""
从访谈清单提取教学策略（LLM 调用，DeepSeek API）

输入：backend/scripts/manifests/interview.json
输出：backend/scripts/manifests/interview_strategies.json

字段约束：
- teacher_quote 必须是 answer 的子串（if quote in answer）
- 不满足则降级：evidence_type=inference + confidence=low
- 不入 Qdrant，只产 manifest 供审阅

用法：
    # 预览：只打印 prompt，不调 LLM
    python scripts/extract_strategies.py --dry-run

    # 执行：调 DeepSeek API（需环境变量 DEEPSEEK_API_KEY 或 LLM_API_KEY）
    python scripts/extract_strategies.py --execute

    # 限制处理条数（测试用）
    python scripts/extract_strategies.py --execute --limit 5

约束：
- 服务器 3.4GB 内存：串行调用，每条 sleep 1s
- 失败重试 2 次，最终失败记录到 failures
- teacher_quote 用 difflib 找最近子串做兜底
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
MANIFESTS_DIR = SCRIPTS_DIR / "manifests"
INPUT_PATH = MANIFESTS_DIR / "interview.json"
OUTPUT_PATH = MANIFESTS_DIR / "interview_strategies.json"


SYSTEM_PROMPT = """你是一位教学策略分析专家，从外语教学访谈中提取教师使用的教学策略。

要求：
1. 每个问答对提取 0-3 个策略，没有明确策略时返回空数组 []
2. teacher_quote 必须从 answer 中逐字摘录（10-50字），不要改写或意译
3. strategy_name 用简洁的术语（如 分层教学、支架式提问、情境导入、形成性评价 等）
4. lesson_type 用 听说/精读/读写/综合/语法/翻译/词汇 等标准课型
5. teaching_stage 用 课前预习/课中导入/课中呈现/课中练习/课中反馈/课后作业 等标准阶段
6. 输出严格的 JSON 数组，不要包裹在 markdown 代码块里
7. 不要输出任何解释性文字

输出格式：
[
  {
    "strategy_name": "策略名",
    "lesson_type": "课型",
    "teaching_stage": "教学阶段",
    "teacher_action": "教师具体做法（30-80字）",
    "teacher_quote": "教师原话（从 answer 逐字摘录）"
  }
]
"""


def build_user_prompt(entry: Dict, qa: Dict) -> str:
    """为单个问答对构建 LLM prompt"""
    return f"""教师代号：{entry['teacher_code']}
访谈主题：{entry.get('interview_topic') or '未提供'}
教龄：{entry.get('teaching_years') or '未知'}年
学校类型：{entry.get('school_anonymized') or '未提供'}
问答主题：{qa.get('topic') or '未分组'}

问：{qa['question']}

答：{qa['answer']}

请提取教学策略，输出 JSON 数组（无策略则返回 []）："""


def call_deepseek(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 2,
) -> Tuple[str, Dict]:
    """调用 DeepSeek API，返回 (response_text, usage_info)

    失败重试 max_retries 次，最终失败抛异常。
    """
    import openai

    client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2000,
                temperature=0.3,
                top_p=0.9,
            )
            text = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return text, usage
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"DeepSeek 调用失败（重试 {max_retries} 次）: {last_err}")


def parse_json_response(text: str) -> List[Dict]:
    """解析 LLM 返回的 JSON 数组

    容忍 markdown 代码块包裹、前后说明文字。
    """
    if not text:
        return []

    # 去掉 markdown 代码块
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)

    # 直接 parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "strategies" in data:
            return data["strategies"]
    except json.JSONDecodeError:
        pass

    # 兜底：从文本中提取第一个 JSON 数组
    m = re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return []


def find_closest_substring(quote: str, answer: str, min_len: int = 8) -> Optional[Tuple[int, int]]:
    """在 answer 中找与 quote 最接近的子串

    返回 (start, end) 或 None。用 SequenceMatcher 找最长匹配块。
    """
    if not quote or not answer:
        return None

    sm = SequenceMatcher(None, answer, quote, autojunk=False)
    # 找最长的连续匹配块
    matches = sm.get_matching_blocks()
    if not matches:
        return None

    # 选最长的匹配块作为锚点，再向两边扩展找最大连续子串
    best = max(matches, key=lambda m: m.size)
    if best.size < min_len:
        return None

    return best.a, best.a + best.size


def validate_and_build_strategy(
    raw: Dict,
    entry: Dict,
    qa: Dict,
    qa_index: int,
    strategy_index: int,
) -> Dict:
    """校验 teacher_quote 是否在 answer 里，构造最终策略记录"""
    quote = (raw.get("teacher_quote") or "").strip()
    answer = qa["answer"]

    quote_in_answer = bool(quote) and quote in answer
    fallback_substring = None

    if not quote_in_answer and quote:
        # 找最接近的子串做兜底
        pos = find_closest_substring(quote, answer)
        if pos:
            fallback_substring = answer[pos[0]:pos[1]]

    if quote_in_answer:
        evidence_type = "direct_quote"
        confidence = "high"
        final_quote = quote
    elif fallback_substring:
        evidence_type = "inference"
        confidence = "low"
        final_quote = fallback_substring
    else:
        evidence_type = "inference"
        confidence = "low"
        final_quote = quote

    strategy_id = f"S-{entry['doc_id'].replace('I-', '')}-{qa_index:02d}-{strategy_index:02d}"

    return {
        "strategy_id": strategy_id,
        "doc_id": entry["doc_id"],
        "qa_index": qa_index,
        "qa_topic": qa.get("topic"),
        "teacher_code": entry["teacher_code"],
        "school_anonymized": entry.get("school_anonymized"),
        "interview_topic": entry.get("interview_topic"),
        "strategy_name": raw.get("strategy_name"),
        "lesson_type": raw.get("lesson_type"),
        "teaching_stage": raw.get("teaching_stage"),
        "teacher_action": raw.get("teacher_action"),
        "teacher_quote": final_quote,
        "evidence_type": evidence_type,
        "confidence": confidence,
        "validation": {
            "quote_in_answer": quote_in_answer,
            "original_quote": quote if not quote_in_answer else None,
            "fallback_applied": fallback_substring is not None,
        },
        "scope": "system",
        "source_tag": "seed_interview_strategy",
    }


def process_interview(
    entry: Dict,
    api_key: str,
    base_url: str,
    model: str,
    dry_run: bool,
) -> Tuple[List[Dict], List[Dict]]:
    """处理单个访谈条目，返回 (strategies, failures)"""
    strategies = []
    failures = []
    qa_pairs = entry.get("qa_pairs", [])

    for qi, qa in enumerate(qa_pairs):
        user_prompt = build_user_prompt(entry, qa)

        if dry_run:
            print(f"  [DRY-RUN] {entry['doc_id']} Q{qi+1}: prompt 长度={len(user_prompt)}")
            continue

        try:
            response_text, usage = call_deepseek(
                api_key, base_url, model,
                SYSTEM_PROMPT, user_prompt,
            )
        except Exception as e:
            failures.append({
                "doc_id": entry["doc_id"],
                "qa_index": qi,
                "reason": str(e),
            })
            continue

        raw_strategies = parse_json_response(response_text)
        for si, raw in enumerate(raw_strategies):
            strategy = validate_and_build_strategy(raw, entry, qa, qi, si)
            strategies.append(strategy)

        # 串行限速
        time.sleep(1.0)

    return strategies, failures


def main():
    parser = argparse.ArgumentParser(
        description="从访谈清单提取教学策略（DeepSeek API）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 预览（不调 LLM）
  python scripts/extract_strategies.py --dry-run

  # 执行（需 DEEPSEEK_API_KEY 环境变量）
  python scripts/extract_strategies.py --execute

  # 限制处理条数
  python scripts/extract_strategies.py --execute --limit 3
""",
    )
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不调 LLM")
    parser.add_argument("--execute", action="store_true", help="真正调用 DeepSeek API")
    parser.add_argument("--limit", type=int, default=None, help="限制处理访谈条数")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("错误：必须指定 --dry-run 或 --execute", file=sys.stderr)
        return 2

    # 加载 interview.json
    if not INPUT_PATH.exists():
        print(f"错误：找不到输入文件 {INPUT_PATH}", file=sys.stderr)
        return 2

    with INPUT_PATH.open(encoding="utf-8") as f:
        interview_manifest = json.load(f)

    entries = interview_manifest.get("entries", [])
    if args.limit:
        entries = entries[: args.limit]

    print(f"加载 {len(entries)} 个访谈条目，共 "
          f"{sum(len(e.get('qa_pairs', [])) for e in entries)} 个问答对")

    # LLM 配置
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    if args.execute:
        if not api_key:
            print("错误：环境变量 DEEPSEEK_API_KEY 或 LLM_API_KEY 未设置",
                  file=sys.stderr)
            return 2
        print(f"使用 LLM: base_url={base_url}, model={model}")
    else:
        print("DRY-RUN 模式：不调 LLM")

    # 处理
    all_strategies: List[Dict] = []
    all_failures: List[Dict] = []

    for ei, entry in enumerate(entries, 1):
        print(f"\n[{ei}/{len(entries)}] 处理 {entry['doc_id']} "
              f"(T:{entry['teacher_code']}, qa:{len(entry.get('qa_pairs', []))})")
        strats, fails = process_interview(
            entry, api_key, base_url, model, args.dry_run,
        )
        all_strategies.extend(strats)
        all_failures.extend(fails)
        if not args.dry_run:
            print(f"  -> {len(strats)} 策略，{len(fails)} 失败")

    # 摘要
    direct_count = sum(1 for s in all_strategies if s["evidence_type"] == "direct_quote")
    inference_count = sum(1 for s in all_strategies if s["evidence_type"] == "inference")
    high_count = sum(1 for s in all_strategies if s["confidence"] == "high")
    low_count = sum(1 for s in all_strategies if s["confidence"] == "low")

    output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(INPUT_PATH.name),
        "llm_model": model if args.execute else "(dry-run, no LLM)",
        "total_count": len(all_strategies),
        "stats": {
            "direct_quote": direct_count,
            "inference": inference_count,
            "high_confidence": high_count,
            "low_confidence": low_count,
        },
        "strategies": all_strategies,
        "failures": all_failures,
        "notes": [
            "teacher_quote 字段必须是 answer 的子串（if quote in answer）",
            "不满足则降级为 evidence_type=inference + confidence=low，并用 difflib 找最接近子串兜底",
            "不入 Qdrant，只产 manifest 供审阅",
            "scope=system：seed 入库时与现有 5 个 system_seed 并存",
            "source_tag=seed_interview_strategy：与 seed_materials_interview 区分",
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n=== 摘要 ===")
    print(f"总策略数:    {len(all_strategies)}")
    print(f"  direct_quote (high): {direct_count}")
    print(f"  inference (low):     {inference_count}")
    print(f"失败数:      {len(all_failures)}")
    print(f"输出:        {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
