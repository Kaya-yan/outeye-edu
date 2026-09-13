"""
公共知识库语料清洗（任务G1）：审计 → 修复 → 句界重切 → 质量过滤 → 展示修剪。

离线管线：scripts/corpus_audit.py（只读审计）与 scripts/corpus_clean.py（清洗重建）
驱动本模块；旧 collection 不动，清洗后数据灌入新 collection，回滚 = 换回环境变量。
展示层只消费 excerpt_by_sentence（资料抽屉兜底，漏网 chunk 不展示断头断尾）。
"""

import re
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Set, Tuple

# ---------- 常量 ----------

ZERO_WIDTH_RE = re.compile("[​-‏‪-‮⁠﻿]")
PAGENUM_LINE_RE = re.compile(
    r"^\s*(?:\d{1,4}|[ivxlcdm]{1,7}|第\s*\d+\s*页|page\s+\d+(?:\s*/\s*\d+)?|-\s*\d+\s*-)\s*$",
    re.IGNORECASE,
)
# 英文逐字碎行合并后无法确定性还原词边界（如 "slargelyamatter"），此类超长裸词留待 LLM 修复
GLUED_TOKEN_RE = re.compile(r"[A-Za-z]{14,}")
CJK_RE = re.compile("[一-鿿㐀-䶿]")
ASCII_WORD_RE = re.compile(r"[A-Za-z]+")

SENT_END_RE = re.compile(r"[。！？；!?…]|(?<=\.)\s")
# 明确的句中接续开头：出现在 chunk 首字符时视为半句开头（保守集合，避免误杀合法句首）
LEADING_CONT_CHARS = set("，、；：和与或但也而且因此于是并且以及的话了着")

AUDIT_CATEGORIES = ("letter_spine", "mid_sentence", "noise_lines", "too_short", "lang_anomaly")


# ---------- 审计（只读指标） ----------

def single_char_line_ratio(text: str) -> float:
    lines = [l for l in (x.strip() for x in text.splitlines()) if l]
    if not lines:
        return 0.0
    return sum(1 for l in lines if len(l) == 1) / len(lines)


def isolated_noise_lines(text: str) -> List[str]:
    """孤立页码 / 短页眉页脚形态的行（孤立数字、罗马数字、第N页、page N）。"""
    return [l.strip() for l in text.splitlines() if PAGENUM_LINE_RE.match(l)]


def _starts_mid_sentence(text: str) -> bool:
    c = text.lstrip()[:1]
    if not c:
        return False
    if c.isascii() and c.islower():
        return True
    return c in LEADING_CONT_CHARS


def _ends_mid_sentence(text: str) -> bool:
    t = text.rstrip()
    if not t:
        return False
    c = t[-1]
    if c in "。！？；!?…\"”』」）)]】.":
        return False
    # 英文以小写字母/逗号等收尾 = 从句中切断
    return c.isascii() and (c.islower() or c in ",;:")


def audit_chunk(text: str) -> List[str]:
    """返回该 chunk 命中的问题类别列表。"""
    issues: List[str] = []
    stripped = (text or "").strip()
    if not stripped:
        return ["too_short"]

    if single_char_line_ratio(stripped) > 0.30:
        issues.append("letter_spine")

    if _starts_mid_sentence(stripped) or _ends_mid_sentence(stripped) or (
        len(stripped) < 100 and stripped[-1] not in "。！？；!?…\"”』」）)]】."
    ):
        issues.append("mid_sentence")

    if isolated_noise_lines(stripped):
        issues.append("noise_lines")

    if len(stripped) < 50:
        issues.append("too_short")

    cjk = len(CJK_RE.findall(stripped))
    ascii_letters = sum(len(w) for w in ASCII_WORD_RE.findall(stripped))
    printable = max(len(re.sub(r"\s", "", stripped)), 1)
    if cjk / printable > 0.3 and ascii_letters / printable > 0.3:
        issues.append("lang_anomaly")

    return issues


def audit_collection(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按 chunk 列表汇总审计报告（不含抽样，抽样由脚本层做）。"""
    per_cat: Counter = Counter()
    flagged = 0
    for c in chunks:
        issues = audit_chunk(c.get("content", "") or "")
        if issues:
            flagged += 1
        per_cat.update(issues)
    total = max(len(chunks), 1)
    return {
        "total": len(chunks),
        "flagged": flagged,
        "flagged_pct": round(flagged / total * 100, 1),
        "counts": {k: per_cat.get(k, 0) for k in AUDIT_CATEGORIES},
        "pcts": {k: round(per_cat.get(k, 0) / total * 100, 1) for k in AUDIT_CATEGORIES},
    }


# ---------- 修复与规范化 ----------

def merge_letter_spines(text: str) -> Tuple[str, bool]:
    """连续单字符行合并：CJK 直接拼接；纯 ASCII 字母行只能黏成裸词（无法还原空格），
    返回 (合并后文本, 是否存在需 LLM 修复的英文裸词)。"""
    lines = text.splitlines()
    out: List[str] = []
    run: List[str] = []
    glued = False

    def flush():
        nonlocal glued
        if not run:
            return
        chars = [c.strip() for c in run]
        if all(len(c) == 1 and c.isascii() and c.isalpha() for c in chars):
            out.append("".join(chars))
            glued = True
        else:
            out.append("".join(chars))
        run.clear()

    for line in lines:
        s = line.strip()
        if len(s) == 1:
            run.append(s)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out), glued


def find_repeated_headers(chunks_per_doc: List[Dict[str, Any]]) -> Set[str]:
    """文档级页眉页脚：在 ≥3 个 chunk 里重复出现且出现率 ≥30% 的短行。
    以句读符号结尾的行是正文句子（页眉页脚是标题形态），不参与判定。"""
    line_docs: Dict[str, Set[int]] = {}
    for idx, c in enumerate(chunks_per_doc):
        for l in (x.strip() for x in (c.get("content") or "").splitlines()):
            if 0 < len(l) <= 40 and l[-1] not in "。！？；!?….":
                line_docs.setdefault(l, set()).add(idx)
    n = len(chunks_per_doc)
    if n < 3:
        return set()
    return {l for l, docs in line_docs.items() if len(docs) >= 3 and len(docs) / n >= 0.3}


def normalize_text(text: str, drop_lines: Set[str] = None) -> str:
    """NFKC 归一 / 去零宽 / 压缩空白 / 删孤立页码与文档级页眉页脚行。"""
    text = unicodedata.normalize("NFKC", text or "")
    text = ZERO_WIDTH_RE.sub("", text)
    drop = drop_lines or set()
    kept: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if PAGENUM_LINE_RE.match(s) or s in drop:
            continue
        kept.append(re.sub(r"[ \t]{2,}", " ", s))
    return "\n".join(kept)


# ---------- 句界重切 ----------

def split_sentences(text: str) -> List[str]:
    """按句读切分：中文 。！？；…，英文句点+空白；后置引号/括号留在前句。"""
    boundaries = [m.end() for m in SENT_END_RE.finditer(text)]
    parts: List[str] = []
    prev = 0
    for b in boundaries:
        j = b
        while j < len(text) and text[j] in "\"'”』」）)]】":
            j += 1
        parts.append(text[prev:j].strip())
        prev = j
    parts.append(text[prev:].strip())
    return [p for p in parts if p]


def _join_sentences(parts: List[str]) -> str:
    """句间拼接：边界两侧都是 CJK 直接连；英文句点后补一个空格。"""
    out = parts[0]
    for p in parts[1:]:
        prev_tail = out[-1:]
        head = p[:1]
        if CJK_RE.match(prev_tail or " ") or CJK_RE.match(head or " "):
            pass
        else:
            out += " "
        out += p
    return out


def rechunk(
    sentences: List[str], min_len: int = 200, max_len: int = 800, overlap: int = 1
) -> List[str]:
    """句级聚合：目标 200-800 字符，重叠 1 句，禁止从句中切断。
    单句超 max_len 时整句独立成块（宁可超长也不切句）。"""
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for s in sentences:
        if cur and cur_len + len(s) > max_len and cur_len >= min_len:
            chunks.append(_join_sentences(cur))
            cur = cur[-overlap:] if overlap > 0 else []
            cur_len = sum(len(x) for x in cur)
        cur.append(s)
        cur_len += len(s)
    if cur:
        chunks.append(_join_sentences(cur))
    return [c for c in chunks if c.strip()]


def chunk_quality(text: str, had_glue: bool = False) -> Tuple[bool, str]:
    """清洗后质检：False = 隔离（quarantine），不删除但不入库。
    had_glue：该文档合并过英文逐字碎行时才启用裸词检测（避免误伤
    internationalization 这类合法长词）。"""
    stripped = (text or "").strip()
    if len(stripped) < 50:
        return False, "too_short"
    if single_char_line_ratio(stripped) > 0.30:
        return False, "letter_spine_unresolved"
    printable = re.sub(r"\s", "", stripped)
    cjk_or_word = len(CJK_RE.findall(stripped)) + sum(
        len(w) for w in ASCII_WORD_RE.findall(stripped)
    )
    if cjk_or_word / max(len(printable), 1) < 0.3:
        return False, "no_content"
    if had_glue and GLUED_TOKEN_RE.search(stripped):
        return False, "glued_needs_llm"
    return True, ""


def clean_document(
    chunks: List[Dict[str, Any]], min_len: int = 200, max_len: int = 800
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """单文档清洗全流程：合并碎行 → 规范化 → 句界重切 → 质量过滤。
    返回 (入库 chunk 文本列表, [(被隔离文本, 原因)])。"""
    chunks = sorted(chunks, key=lambda c: c.get("chunk_index", 0))
    headers = find_repeated_headers(chunks)
    merged = "\n".join((c.get("content") or "").strip() for c in chunks if c.get("content"))
    repaired, had_glue = merge_letter_spines(merged)
    normalized = normalize_text(repaired, drop_lines=headers)
    if not normalized.strip() and headers:
        # 页眉误判兜底：删完为空则回退为不删页眉
        normalized = normalize_text(repaired)
    if not normalized.strip():
        return [], [(merged[:80], "empty_after_clean")]
    sentences = split_sentences(normalized)
    pieces = rechunk(sentences, min_len=min_len, max_len=max_len)
    clean: List[str] = []
    quarantined: List[Tuple[str, str]] = []
    for p in pieces:
        ok, reason = chunk_quality(p, had_glue=had_glue)
        if ok:
            clean.append(p)
        else:
            quarantined.append((p, reason))
    return clean, quarantined


# ---------- 展示层兜底 ----------

def excerpt_by_sentence(text: str, limit: int = 8000, marker: str = "（节选）") -> str:
    """按句边界修剪：去开头不完整半句；超长时截到最后一个完整句，头部加「（节选）」。"""
    text = (text or "").strip()
    if not text:
        return ""
    if _starts_mid_sentence(text):
        m = SENT_END_RE.search(text)
        if m and m.end() < len(text):
            text = text[m.end():].strip()
    if len(text) <= limit:
        return text
    last_end = -1
    for m in SENT_END_RE.finditer(text):
        if m.end() > limit:
            break
        end = m.end() - 1 if m.group(0).isspace() else m.end()
        last_end = max(last_end, end)
    cut = last_end if last_end != -1 else limit
    return f"{marker}{text[:cut].strip()}"
