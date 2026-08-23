"""
提示词模板管理

模板以 Markdown 文件存放于 app/prompts/，用 string.Template 语法（${name}）占位。
文件内以 "# === SYSTEM ===" / "# === USER ===" 分隔系统提示与用户提示。
版本号从文件名后缀读取（lesson_plan_v2.md → "v2"），随生成结果落库以便追溯。
"""

from pathlib import Path
from string import Template
from typing import Dict, Tuple

from loguru import logger

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SYSTEM_MARKER = "# === SYSTEM ==="
_USER_MARKER = "# === USER ==="

_cache: Dict[str, Tuple[str, str]] = {}


def load_prompt(name: str) -> Tuple[str, str]:
    """读取模板，返回 (system_prompt, user_template)。带进程内缓存。"""
    if name in _cache:
        return _cache[name]

    path = PROMPTS_DIR / f"{name}.md"
    content = path.read_text(encoding="utf-8")

    sys_idx = content.find(_SYSTEM_MARKER)
    usr_idx = content.find(_USER_MARKER)
    if sys_idx == -1 or usr_idx == -1 or usr_idx < sys_idx:
        raise ValueError(f"提示词模板 {name} 缺少 SYSTEM/USER 分隔标记")

    system = content[sys_idx + len(_SYSTEM_MARKER):usr_idx].strip()
    user_tpl = content[usr_idx + len(_USER_MARKER):].strip()
    _cache[name] = (system, user_tpl)
    return system, user_tpl


def render_prompt(name: str, **variables) -> Tuple[str, str]:
    """加载并渲染模板，返回 (system_prompt, user_prompt)。"""
    system, user_tpl = load_prompt(name)
    user_prompt = Template(user_tpl).safe_substitute(**variables)
    return system, user_prompt


def prompt_version(name: str) -> str:
    """从文件名读取版本（lesson_plan_v2.md → v2）。"""
    stem = (PROMPTS_DIR / f"{name}.md").stem
    return stem.rsplit("_", 1)[-1]


def prompt_dir() -> Path:
    return PROMPTS_DIR


if __name__ == "__main__":
    # 模板自检：渲染一份样例，检查占位符是否齐全
    demo = dict(
        title="T", language_name="英语", text_level="B1", student_level="B1",
        gap_line="适度挑战", duration_minutes=90, course_type="精读", class_size=30,
        native_language="中文", language_note="", full_text="TEXT", total_words=100,
        unique_words=60, cefr_line="A1=10", awl_line="AWL=5", difficult_words="a, b",
        avg_sentence_length=18, max_sent_index=3, max_sent_words=35,
        max_sent_preview="...", long_sentences_count=2, flesch=52.0, paragraph_count=5,
        connective_density=4.2, genre_hint="说明文", cultural_section="",
        wiki_context="（无）", rag_context="（无）",
    )
    sys_p, user_p = render_prompt("lesson_plan_v2", **demo)
    leftover = [ln for ln in user_p.splitlines() if "${" in ln]
    if leftover:
        logger.error(f"模板存在未替换占位符: {leftover}")
        raise SystemExit(1)
    print("模板自检通过:", prompt_version("lesson_plan_v2"))
