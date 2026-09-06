"""
课件主题库 v1（④b）：策展主题 = 完整 token 组 + 主题级组件微调。

骨架 courseware_skeleton_v2.html 的 :root 整块与主题微调样式由后端按主题注入，
内容层 HTML 只写 var(--token)，因此换主题对 LLM 透明（同一内容层契约）。

对比度契约（WCAG AA）：每套主题的 ink/text/muted 及全局四色强调色对该主题
paper 与 card 均 ≥4.5:1，由 tests/test_courseware_themes.py 断言；修改色值必须跑该测试。
"""

from dataclasses import dataclass, field
from typing import Dict, List

DEFAULT_THEME_ID = "academic"

_FONT_TITLE = "'Noto Serif SC','Source Han Serif SC','Songti SC',serif"
_FONT_BODY = "'Noto Sans SC','Source Han Sans SC','PingFang SC',sans-serif"


@dataclass(frozen=True)
class CoursewareTheme:
    id: str
    name: str
    tagline: str
    description: str
    palette_desc: str  # 注入生成提示词的一句话气质描述
    default_accent: str
    tokens: Dict[str, str] = field(default_factory=dict)
    extra_css: str = ""
    dark: bool = False  # 深色主题：强调色锁定主题专属色（全局浅底色板对其不适用），LLM 声明被忽略

    def token_css(self) -> str:
        lines = [f"  --{k}:{v};" for k, v in self.tokens.items()]
        return "\n".join(lines)


THEMES: Dict[str, CoursewareTheme] = {
    "academic": CoursewareTheme(
        id="academic",
        name="学术讲义",
        tagline="墨蓝 · 暖白 · 衬线标题",
        description="理性克制的讲义气质，适合精读、学术与说明类课文，是平台的默认主题。",
        palette_desc="墨蓝墨色配暖白纸面，理性、学术、克制",
        default_accent="#35507a",
        tokens={
            "paper": "#faf9f5",
            "ink": "#1e3a5f",
            "text": "#2b2b33",
            "muted": "#6b6f76",
            "line": "#e3e0d8",
            "card": "#ffffff",
            "backdrop": "#e8e6e0",
            "font-title": _FONT_TITLE,
            "font-body": _FONT_BODY,
            "fs-title": "44px",
            "fs-h2": "32px",
            "fs-body": "21px",
            "fs-caption": "16px",
            "lh-body": "1.8",
        },
        extra_css="",
    ),
    "humanities": CoursewareTheme(
        id="humanities",
        name="人文暖色",
        tagline="朱砂 · 米白 · 暖褐墨色",
        description="温润的米白纸面与暖褐墨色，适合文学、文化、历史与传记类课文。",
        palette_desc="米白纸面配暖褐墨色与朱砂点缀，温润、人文、叙事",
        default_accent="#b5493e",
        tokens={
            "paper": "#fbf6ed",
            "ink": "#4e3527",
            "text": "#33291f",
            "muted": "#6e6152",
            "line": "#e9ddc8",
            "card": "#fffdf6",
            "backdrop": "#ece4d4",
            "font-title": _FONT_TITLE,
            "font-body": _FONT_BODY,
            "fs-title": "44px",
            "fs-h2": "32px",
            "fs-body": "21px",
            "fs-caption": "16px",
            "lh-body": "1.8",
        },
        extra_css=(
            ".page h1,.page h2{letter-spacing:.02em}\n"
            ".kicker{letter-spacing:.4em}\n"
            ".accent-rule{width:56px;height:2px}\n"
            "ul.plain li::before{border-radius:2px}\n"
            ".vocab-card .back{background:var(--ink)}"
        ),
    ),
    "fresh": CoursewareTheme(
        id="fresh",
        name="清新课堂",
        tagline="黛绿 · 暖白 · 圆角卡片",
        description="轻快的暖白纸面与黛绿点缀、更圆润的卡片，适合口语、视听说与低龄课堂。",
        palette_desc="暖白纸面配深黛绿墨色与圆润卡片，轻快、亲和、明亮",
        default_accent="#3e6b5a",
        tokens={
            "paper": "#f4f7f2",
            "ink": "#2c4a3c",
            "text": "#2b332c",
            "muted": "#66746a",
            "line": "#dde6da",
            "card": "#fefffd",
            "backdrop": "#e3eae2",
            "font-title": _FONT_TITLE,
            "font-body": _FONT_BODY,
            "fs-title": "44px",
            "fs-h2": "32px",
            "fs-body": "21px",
            "fs-caption": "16px",
            "lh-body": "1.8",
        },
        extra_css=(
            ".card,.callout,details.reveal{border-radius:14px}\n"
            ".accent-rule{width:72px;height:4px;border-radius:2px}\n"
            "ul.plain li::before{border-radius:3px;transform:rotate(45deg)}\n"
            ".vocab-card .back{background:var(--ink)}"
        ),
    ),
    "press": CoursewareTheme(
        id="press",
        name="经典报刊",
        tagline="纸米白 · 墨黑 · 报红点缀",
        description="报纸排版的秩序感：粗黑标题、细规线与一点报红，适合新闻、评论与时文类课文。",
        palette_desc="纸米白版面配墨黑标题与克制报红点缀，严肃、利落、有报刊排版秩序感",
        default_accent="#9c2f26",
        tokens={
            "paper": "#f9f6f0",
            "ink": "#211d1a",
            "text": "#2b2622",
            "muted": "#6d675e",
            "line": "#e2ddd2",
            "card": "#ffffff",
            "backdrop": "#ece8de",
            "font-title": _FONT_TITLE,
            "font-body": _FONT_BODY,
            "fs-title": "44px",
            "fs-h2": "32px",
            "fs-body": "21px",
            "fs-caption": "16px",
            "lh-body": "1.8",
        },
        extra_css=(
            ".page h2{border-bottom:2px solid var(--line);padding-bottom:10px}\n"
            ".kicker{letter-spacing:.2em;text-transform:uppercase}\n"
            ".accent-rule{width:120px;height:2px}\n"
            "ul.plain li::before{border-radius:1px;width:6px;height:6px}\n"
            ".vocab-card .back{background:var(--ink)}"
        ),
    ),
    "inkwash": CoursewareTheme(
        id="inkwash",
        name="东方水墨",
        tagline="宣纸色 · 黛色 · 赭石点缀",
        description="宣纸底色与黛色墨韵、赭石一点，留白呼吸感，适合传统文化、民俗与艺术类课文。",
        palette_desc="宣纸暖白配黛色墨韵与赭石点缀，含蓄、留白、有东方气韵",
        default_accent="#8c4a2f",
        tokens={
            "paper": "#f8f5ec",
            "ink": "#2f3a3f",
            "text": "#333a3d",
            "muted": "#666d71",
            "line": "#e5e0d2",
            "card": "#fdfbf4",
            "backdrop": "#eae5d7",
            "font-title": _FONT_TITLE,
            "font-body": _FONT_BODY,
            "fs-title": "44px",
            "fs-h2": "32px",
            "fs-body": "21px",
            "fs-caption": "16px",
            "lh-body": "1.8",
        },
        extra_css=(
            ".page h1,.page h2{letter-spacing:.06em}\n"
            ".accent-rule{width:2px;height:40px}\n"
            "ol.timeline li{border-left-width:2px}\n"
            "ul.plain li::before{border-radius:50%;width:5px;height:5px}\n"
            ".vocab-card .back{background:var(--ink)}"
        ),
    ),
    "lecture": CoursewareTheme(
        id="lecture",
        name="深邃学术",
        tagline="深蓝黑底 · 暖光字 · 暖金点缀",
        description="深色底配暖光文字与暖金强调，暗教室投影下更聚焦内容，适合讲座与公开课场景。",
        palette_desc="深蓝黑底色配暖光文字与暖金强调，沉浸、聚焦、适合暗环境投影",
        default_accent="#e3b341",
        tokens={
            "paper": "#232936",
            "ink": "#e8dfcf",
            "text": "#d8d3c8",
            "muted": "#9aa0ac",
            "line": "#3d4557",
            "card": "#2b3242",
            "backdrop": "#1a1f2a",
            "font-title": _FONT_TITLE,
            "font-body": _FONT_BODY,
            "fs-title": "44px",
            "fs-h2": "32px",
            "fs-body": "21px",
            "fs-caption": "16px",
            "lh-body": "1.8",
        },
        extra_css=(
            ".accent-rule{width:84px;height:4px;border-radius:2px}\n"
            ".kicker{letter-spacing:.28em}\n"
            ".vocab-card .back{background:var(--text);color:var(--paper)}"
        ),
        dark=True,
    ),
}

# 冷启动默认映射：无教师历史时按课型关键词推荐（具体规则放前面，命中即返回，未命中走 academic）
_COLD_START_RULES: List = [
    ("inkwash", ("传统文化", "民俗", "艺术", "美学", "水墨", "国学")),
    ("press", ("新闻", "评论", "社论", "时文", "报刊", "报道")),
    ("lecture", ("讲座", "公开课", "演讲", "学术报告")),
    ("humanities", ("文学", "文化", "历史", "人文", "传记", "散文", "小说", "诗歌", "戏剧")),
    ("fresh", ("口语", "听力", "视听说", "语音", "会话", "交际", "少儿", "儿童")),
    ("academic", ("学术", "论文", "翻译", "写作", "说明", "科技")),
]


def get_theme(theme_id: str | None) -> CoursewareTheme:
    """解析主题 id；未知或缺省回落默认主题（academic），保证生成永不因主题失败"""
    if theme_id and theme_id in THEMES:
        return THEMES[theme_id]
    return THEMES[DEFAULT_THEME_ID]


def theme_catalog() -> List[Dict[str, object]]:
    """前端主题卡数据（不含 token 细节，只带展示所需的三个色样）"""
    return [
        {
            "id": t.id,
            "name": t.name,
            "tagline": t.tagline,
            "description": t.description,
            "default_accent": t.default_accent,
            "colors": {
                "paper": t.tokens["paper"],
                "ink": t.tokens["ink"],
                "accent": t.default_accent,
            },
        }
        for t in THEMES.values()
    ]


def themes_digest_for_planner() -> str:
    """风格规划提示词里的主题清单（id + 名称 + 一句气质）"""
    return "\n".join(f"- {t.id}（{t.name}）：{t.palette_desc}" for t in THEMES.values())


def cold_start_recommend(course_type: str | None) -> str:
    """冷启动推荐：按课型关键词映射；LLM 不可用或历史空白时的兜底"""
    ct = course_type or ""
    for theme_id, keywords in _COLD_START_RULES:
        if any(k in ct for k in keywords):
            return theme_id
    return DEFAULT_THEME_ID
