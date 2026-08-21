"""
验证 lesson.json 中 _pending_verification=true 的 6 条 PDF 教案记录

用 PyMuPDF (fitz) 打开对应 PDF，人工核对前 2 页 + 关键字段（课时/学段）
后硬编码修正值，更新 lesson.json 对应记录并去掉 pending 标记。

修正内容：
- student_level：L-022/L-023 原本 null，补全为"法语专业三年级"
- class_hours：L-019 误提取"每周2学时"→改为本单元 6 学时；L-020/021/023 补全；
  L-024 的 36 是整门课学时 → 改为第一单元 4 学时
- unit：补全单元主题（"教案标题"等价物）
- L-024 匿名化：text_preview 与 note 中 3 位真实教师姓名/校名脱敏

用法：
    python scripts/verify_pending_lesson.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LESSON_JSON = Path(__file__).resolve().parent / "manifests" / "lesson.json"


# 6 篇 pending 记录的人工核对结果（从 PyMuPDF 输出的 Unicode 文本识别）
VERIFIED_METADATA = {
    "L-019": {
        # 法语读写 unit2 - 《理解当代中国法语读写教程》第二单元
        "unit": "unit2",
        "student_level": "法语专业三年级",
        "class_hours": 6,  # 课内 6 个学时完成 1 个单元（第 1~6 课时）
        "_verification_note": (
            "PyMuPDF(fitz) 验证通过，无 mojibake；课程名称'高级法语'，"
            "课程内容《理解当代中国法语读写教程》第二单元（文明交流互鉴）；"
            "每周 2 学时、每学时 45 分钟，课内 6 学时完成 1 个单元"
        ),
    },
    "L-020": {
        # 法语读写 unit4 - 第四课：美丽中国 La belle Chine
        "unit": "unit4 美丽中国 La belle Chine",
        "student_level": "法语专业三年级",
        "class_hours": 4,  # 本单元共需要四课时
        "_verification_note": (
            "PyMuPDF(fitz) 验证通过，无 mojibake；课程名称'高级法语阅读与写作'，"
            "课程内容'第四课：美丽中国 La belle Chine'；本单元共四课时"
        ),
    },
    "L-021": {
        # 法语读写 unit6 - 第六单元 民族复兴之路
        "unit": "unit6 民族复兴之路",
        "student_level": "法语专业三年级",
        "class_hours": 4,  # 分两次授课，每次课 90 分钟、含 2 课时
        "_verification_note": (
            "PyMuPDF(fitz) 验证通过，无 mojibake；课程名称'高级法语'，"
            "课程内容《理解当代中国》第六单元 民族复兴之路；"
            "分两次授课，每次课 90 分钟、含 2 课时"
        ),
    },
    "L-022": {
        # 法语读写 unit7 - Unité 7 Mener à terme nos réformes
        "unit": "unit7 Mener à terme nos réformes",
        "student_level": "法语专业三年级",
        "class_hours": 4,  # 本单元四课时（已正确）
        "_verification_note": (
            "PyMuPDF(fitz) 验证通过，无 mojibake；课程名称'高级法语（上）'，"
            "课程内容《理解当代中国-法语读写教程》Unité 7 - Mener à terme nos réformes；"
            "教授学段'法语专业大三学生'；本单元四课时"
        ),
    },
    "L-023": {
        # 法语读写 unit8 - Unité 8 Vers où se dirige la civilisation humaine ?
        "unit": "unit8 Vers où se dirige la civilisation humaine ?",
        "student_level": "法语专业三年级",
        "class_hours": 5,  # 每单元教学时长 5 课时
        "_verification_note": (
            "PyMuPDF(fitz) 验证通过，无 mojibake；课程名称'高级法语'，"
            "课程内容 Unité 8 构建人类命运共同体；教授学段'法语本科三年级'；"
            "每单元教学时长 5 课时，分三周完成"
        ),
    },
    "L-024": {
        # 汉俄翻译 unit1 - 理解当代中国：汉俄翻译课程
        "unit": "unit1 中国特色社会主义最本质的特征和中国特色社会主义制度的最大优势",
        "student_level": "俄语专业四年级",
        "class_hours": 4,  # 第一单元共使用 4 学时（原 36 为整门课学时）
        "_verification_note": (
            "PyMuPDF(fitz) 验证通过，无 mojibake；课程名称'理解当代中国：汉俄翻译课程'；"
            "授课教师 3 人已匿名化；学校名称已匿名化；"
            "36 学时为整门课学时（2 学时/周×18 周），第一单元实为 4 学时"
        ),
        # 匿名化替换（text_preview 首 200 字符泄露了真实姓名/校名）
        "anonymize_preview": {
            "钱琴": "钱老师",
            "许宏": "许老师",
            "刘涛": "刘老师",
            "上海外国语大学": "某高校外国语学院",
        },
        "_anonymization_note_override": (
            "教师代号 T-07（教案署名 钱老师，主教师）；本课含 3 位授课教师"
            "（钱老师、许老师、刘老师）均已匿名化；学校名称已匿名化为 某高校外国语学院"
        ),
    },
}


def extract_pdf_text(pdf_path: str, max_pages: int = 3) -> str:
    """提取前 N 页文本（fitz），用于二次校验课时/学段可被抽取"""
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


def verify_entry(entry: dict) -> tuple:
    """应用人工核对结果到单条记录，返回 (updated_entry, change_log)"""
    doc_id = entry["doc_id"]
    verified = VERIFIED_METADATA.get(doc_id, {})
    if not verified:
        return entry, {}

    # 用 fitz 提取文本做二次校验，记录 reader 与是否抽到课时/学段
    try:
        text, reader_used = extract_pdf_text(entry["file_path"], max_pages=3)
        verified["reader_used"] = reader_used
        clean = "".join(c for c in text if c == "\n" or ord(c) >= 0x20)
        # 记录自动抽到的课时/学段线索（仅审计，不覆盖人工值）
        if "课时" in clean:
            hits = re.findall(r"(?:本单元|每单元)[^\n]{0,15}?(\d+)\s*课时", clean)
            if hits:
                verified["_auto_unit_hours"] = hits[:3]
        if "学时" in clean:
            hits = re.findall(r"(\d+)\s*学时", clean)
            if hits:
                verified["_auto_hours"] = hits[:5]
    except Exception as e:
        verified["reader_used"] = f"error: {e}"

    changes = {}
    updated = dict(entry)

    # 应用人工核对字段
    for k in ("unit", "student_level", "class_hours", "_verification_note"):
        if k not in verified:
            continue
        v = verified[k]
        old_v = entry.get(k)
        if old_v != v:
            changes[k] = (old_v, v)
            updated[k] = v

    # L-024 匿名化 text_preview
    if "anonymize_preview" in verified and entry.get("text_preview"):
        new_preview = entry["text_preview"]
        for real, anon in verified["anonymize_preview"].items():
            new_preview = new_preview.replace(real, anon)
        if new_preview != entry["text_preview"]:
            changes["text_preview"] = (entry["text_preview"], new_preview)
            updated["text_preview"] = new_preview

    # L-024 匿名化 note 覆盖
    if "_anonymization_note_override" in verified:
        new_note = verified["_anonymization_note_override"]
        if new_note != entry.get("_anonymization_note"):
            changes["_anonymization_note"] = (entry.get("_anonymization_note"), new_note)
            updated["_anonymization_note"] = new_note

    # 去掉 pending 标记
    if updated.get("_pending_verification"):
        changes["_pending_verification"] = (True, False)
        updated["_pending_verification"] = False

    # reader_used 更新为实际验证用到的 reader
    if "reader_used" in verified:
        old_reader = entry.get("reader_used")
        if old_reader != verified["reader_used"]:
            changes["reader_used"] = (old_reader, verified["reader_used"])
            updated["reader_used"] = verified["reader_used"]

    return updated, changes


def main():
    if not LESSON_JSON.exists():
        print(f"错误：找不到 {LESSON_JSON}", file=sys.stderr)
        return 2

    with LESSON_JSON.open(encoding="utf-8") as f:
        manifest = json.load(f)

    # 处理 pending 记录 + VERIFIED_METADATA 中的记录（防止早先失败运行已把 pending 置 false）
    targets = [
        e for e in manifest["entries"]
        if e.get("_pending_verification") or e["doc_id"] in VERIFIED_METADATA
    ]
    print(f"找到 {len(targets)} 条待修正记录")

    all_changes = {}
    for entry in targets:
        doc_id = entry["doc_id"]
        print(f"\n=== 验证 {doc_id} ===")
        print(f"  文件: {entry.get('original_filename', '')}")

        updated, changes = verify_entry(entry)

        if changes:
            print(f"  修正字段:")
            for field, (old, new) in changes.items():
                old_str = str(old)[:70] + "..." if old and len(str(old)) > 70 else str(old)
                new_str = str(new)[:70] + "..." if new and len(str(new)) > 70 else str(new)
                print(f"    {field}:")
                print(f"      旧: {old_str}")
                print(f"      新: {new_str}")
        else:
            print(f"  无变化")

        all_changes[doc_id] = changes

        for i, e in enumerate(manifest["entries"]):
            if e["doc_id"] == doc_id:
                manifest["entries"][i] = updated
                break

    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()

    LESSON_JSON.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fixed_count = sum(1 for c in all_changes.values() if c)
    print(f"\n=== 摘要 ===")
    print(f"处理 {len(targets)} 条，修正 {fixed_count} 条")
    print(f"输出: {LESSON_JSON}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
