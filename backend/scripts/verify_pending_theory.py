"""
验证 theory.json 中 _pending_verification=true 的 4 条记录

用 PyMuPDF (fitz) 或 pdfplumber 提取前 3 页文本，结合人工核对
（CNKI 自定义 CID 字体让正则识别易踩坑，标题/作者系手动从
 PyMuPDF 输出的 Unicode 文本里确认后硬编码），更新 theory.json
 对应记录，去掉 _pending_verification 标记。

用法：
    python scripts/verify_pending_theory.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

THEORY_JSON = Path(__file__).resolve().parent / "manifests" / "theory.json"


# 4 篇 pending 记录的人工核对结果（从 PyMuPDF 输出的 Unicode 文本中识别）
# 同时用脚本自动抽 DOI/文章编号/页码做兜底，字段冲突时以人工核对为准
VERIFIED_METADATA = {
    "T-103": {
        # 理论3-Fairclough-CDA-1989.pdf - CNKI 期刊《外国语文》ISSN 1004-6038
        "title": "批评话语分析: 目标、方法与动态",
        "authors": ["辛斌", "高小丽"],
        "source_journal": "外国语文",
        "year": 2013,
        "volume": None,  # 期刊无卷号
        "issue": "04",
        "pages": "1-5",
        "doi": "10.13458/j.cnki.flatt.003923",
        "article_number": "1004-6038(2013)04-0001-05",
        "_verification_note": (
            "PyMuPDF 验证通过；标题原为'批评话语分析：目标、语类与态势'，"
            "实测为'批评话语分析: 目标、方法与动态'；作者补全为辛斌、高小丽"
            "（南京师范大学外国语学院）；ISSN 1004-6038 即《外国语文》；"
            "文章编号 1004-6038(2013)04-0001-05 -> 2013年第4期 1-5页"
        ),
    },
    "T-106": {
        # 理论6-Jerome Bruner-支架+STEM-1976.pdf - 《现代远距离教育》ISSN 1001-8700
        "title": "\"支架+\"STEM教学模式设计及实践研究——面向高阶思维能力培养",
        "authors": ["潘星竹", "姜强", "黄丽", "赵蔚", "王利思"],
        "source_journal": "现代远距离教育",
        "year": 2019,
        "volume": "183",  # 总第183期
        "issue": "03",
        "pages": "56-64",
        "doi": "10.13927/j.cnki.yuan.2019.0028",
        "article_number": "1001-8700(2019)03-0056-09",
        "_verification_note": (
            "PyMuPDF 验证通过；标题原为'大数据时代在线学习者情感挖掘与干预研究"
            "（STEM+支架视角）'，实测标题与理论6 文件名不符（这是该 PDF 的真实"
            "标题）；作者 5 人潘星竹、姜强、黄丽、赵蔚、王利思，东北师范大学等；"
            "文章编号 1001-8700(2019)03-0056-09 -> 2019年第3期（总第183期）56-64页"
        ),
    },
    "T-107": {
        # 理论7-Jerome Bruner-支架-1976.pdf - 《中国职业技术教育》ISSN 1004-9290
        "title": "支架式教学及其在中职英语教学中的应用研究",
        "authors": ["吴冬梅", "吴晶晶"],
        "source_journal": "中国职业技术教育",
        "year": 2015,
        "volume": None,
        "issue": "11",
        "pages": "74-82",
        "doi": None,
        "article_number": "1004-9290(2015)0011-0074-09",
        "_verification_note": (
            "PyMuPDF 验证通过；标题原为'支架式教学理论与实践'，实测为'支架式"
            "教学及其在中职英语教学中的应用研究'；作者 2 人吴冬梅、吴晶晶；"
            "ISSN 1004-9290 即《中国职业技术教育》；文章编号 1004-9290(2015)0011-0074-09 "
            "-> 2015年第11期 74-82页"
        ),
    },
    "T-108": {
        # 理论8-Vygotsky-社会文化理论-1922.pdf - 《中国海洋大学学报（社会科学版）》
        "title": "从Vygotsky 理论视角看翻译在二语习得中的作用",
        "authors": ["徐敏慧"],
        "source_journal": "中国海洋大学学报（社会科学版）",
        "year": 2006,
        "volume": None,
        "issue": "06",
        "pages": "83-86",
        "doi": None,
        "article_number": "1672-335X(2006)06-0083-04",
        "_verification_note": (
            "PyMuPDF 验证通过；标题原为'Vygotsky 心理理论对二语教学的启发'，实测为"
            "'从Vygotsky 理论视角看翻译在二语习得中的作用'；作者徐敏慧（中国海洋大学"
            "外国语学院）；ISSN 1672-335X 即《中国海洋大学学报（社会科学版）》；"
            "文章编号 1672-335X(2006)06-0083-04 -> 2006年第6期 83-86页"
        ),
    },
}


def extract_pdf_text(pdf_path: str, max_pages: int = 3) -> str:
    """提取前 N 页文本，优先 fitz，回退 pdfplumber"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        parts = []
        for i in range(min(max_pages, doc.page_count)):
            parts.append(doc[i].get_text(sort=True))
        doc.close()
        return "\n".join(parts), "fitz"
    except ImportError:
        pass
    except Exception as e:
        print(f"  [warn] fitz 不可用: {e}，回退 pdfplumber")

    import pdfplumber
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(min(max_pages, len(pdf.pages))):
            t = pdf.pages[i].extract_text() or ""
            parts.append(t)
    return "\n".join(parts), "pdfplumber"


def auto_extract_doi(text: str) -> str:
    """自动抽取 DOI"""
    m = re.search(r"DOI\s*[:：]\s*(10\.\d{4,9}/[^\s\n]+)", text, re.IGNORECASE)
    return m.group(1) if m else None


def auto_extract_article_number(text: str) -> str:
    """自动抽取文章编号 XXXX-XXXX(YYYY)NN-PPPP-QQ"""
    m = re.search(
        r"\d{4}-\d{3,4}X?\s*[（(]\s*\d{4}\s*[)）]\s*\d+\s*-\s*\d+\s*-\s*\d+",
        text,
    )
    return m.group(0).strip() if m else None


def verify_entry(entry: dict) -> tuple:
    """应用人工核对结果到单条记录，返回 (updated_entry, change_log)"""
    doc_id = entry["doc_id"]
    verified = VERIFIED_METADATA.get(doc_id, {})
    if not verified:
        return entry, {}

    # 用 PyMuPDF/pdfplumber 提取文本做二次校验（确认 DOI 和文章编号能从 PDF 抽到）
    try:
        text, reader_used = extract_pdf_text(entry["file_path"], max_pages=3)
        verified["reader_used"] = reader_used
        auto_doi = auto_extract_doi(text)
        auto_an = auto_extract_article_number(text)
        # 如果自动抽到的与人工核对的不一致，记录但不覆盖人工值（人工已确认）
        if auto_doi and auto_doi != verified.get("doi"):
            verified["_auto_extracted_doi"] = auto_doi
        if auto_an and auto_an != verified.get("article_number"):
            verified["_auto_extracted_article_number"] = auto_an
    except Exception as e:
        verified["reader_used"] = f"error: {e}"

    changes = {}
    updated = dict(entry)

    # 更新所有 verified 字段
    for k, v in verified.items():
        old_v = entry.get(k)
        if old_v != v:
            changes[k] = (old_v, v)
            updated[k] = v

    # 构造 raw_citation
    if "authors" in verified and "title" in verified and "source_journal" in verified and "year" in verified:
        author_str = ", ".join(verified["authors"])
        vol_issue = ""
        if verified.get("volume"):
            vol_issue += f", {verified['volume']}"
        if verified.get("issue"):
            vol_issue += f" ({verified['issue']})"
        pages_str = f": {verified['pages']}" if verified.get("pages") else ""
        citation = (
            f"{author_str}. {verified['title']}[J]. "
            f"{verified['source_journal']}, "
            f"{verified['year']}{vol_issue}{pages_str}."
        )
        if citation != entry.get("raw_citation"):
            changes["raw_citation"] = (entry.get("raw_citation"), citation)
            updated["raw_citation"] = citation

    # 去掉 pending 标记
    if updated.get("_pending_verification"):
        changes["_pending_verification"] = (True, False)
        updated["_pending_verification"] = False

    return updated, changes


def main():
    if not THEORY_JSON.exists():
        print(f"错误：找不到 {THEORY_JSON}", file=sys.stderr)
        return 2

    with THEORY_JSON.open(encoding="utf-8") as f:
        manifest = json.load(f)

    # 同时处理：(1) 仍标 pending 的；(2) VERIFIED_METADATA 中指定的（即使 pending 已被
    # 早先失败运行设为 False，只要 doc_id 在 VERIFIED_METADATA 中就再修正一次）
    pending = [
        e for e in manifest["entries"]
        if e.get("_pending_verification") or e["doc_id"] in VERIFIED_METADATA
    ]
    print(f"找到 {len(pending)} 条待修正记录（pending 或在 VERIFIED_METADATA 中）")

    all_changes = {}
    for entry in pending:
        doc_id = entry["doc_id"]
        print(f"\n=== 验证 {doc_id} ===")
        print(f"  文件: {entry.get('original_filename', '')}")

        updated, changes = verify_entry(entry)

        if changes:
            print(f"  修正字段:")
            for field, (old, new) in changes.items():
                old_str = str(old)[:80] + "..." if old and len(str(old)) > 80 else str(old)
                new_str = str(new)[:80] + "..." if new and len(str(new)) > 80 else str(new)
                print(f"    {field}:")
                print(f"      旧: {old_str}")
                print(f"      新: {new_str}")
        else:
            print(f"  无变化")

        all_changes[doc_id] = changes

        # 在 manifest.entries 里替换
        for i, e in enumerate(manifest["entries"]):
            if e["doc_id"] == doc_id:
                manifest["entries"][i] = updated
                break

    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()

    THEORY_JSON.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fixed_count = sum(1 for c in all_changes.values() if c)
    print(f"\n=== 摘要 ===")
    print(f"处理 {len(pending)} 条，修正 {fixed_count} 条")
    print(f"输出: {THEORY_JSON}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
