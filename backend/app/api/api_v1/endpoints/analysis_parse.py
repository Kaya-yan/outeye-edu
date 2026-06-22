"""
课文文件解析和 OCR 识别端点

支持上传 PDF/Word/TXT 文件提取文本，以及图片 OCR 识别文字。
"""

import os
import re
import tempfile
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from app.core.config import Settings
from app.core.rate_limit import check_file_upload_rate_limit
from app.api.api_v1.endpoints.users import get_current_user

router = APIRouter()
settings = Settings()


# ============ Magic byte 验证 ============

# 文件头魔数签名
_MAGIC_SIGNATURES = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04"],  # ZIP format (docx is a zip)
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".webp": [b"RIFF"],  # followed by 4 bytes size then "WEBP"
}


def _validate_file_content(content: bytes, ext: str) -> bool:
    """通过 magic bytes 验证文件内容是否匹配扩展名"""
    signatures = _MAGIC_SIGNATURES.get(ext)
    if not signatures:
        # .txt, .md 没有固定签名，跳过验证
        return True
    return any(content.startswith(sig) for sig in signatures)

# ============ 响应模型 ============


class ParseFileResponse(BaseModel):
    text: str
    filename: str
    total_pages: int = 0
    page_from: Optional[int] = None
    page_to: Optional[int] = None
    word_count: int = 0
    file_type: str = ""


class OCRImageResponse(BaseModel):
    text: str
    confidence: float = 0
    engine: str = ""
    word_count: int = 0


# ============ 文件类型配置 ============

ALLOWED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 64 * 1024  # 64KB per chunk


async def _stream_upload_to_temp(
    file: UploadFile, max_size: int, tmp_path: str
) -> tuple[bytes, int]:
    """
    流式读取上传文件，边读边写入临时文件。

    - 每读一个 chunk 就累加大小，超过 max_size 立即抛异常，不会撑爆内存。
    - 返回 (first_chunk, total_size)，first_chunk 用于 magic byte 验证。

    Raises:
        HTTPException 413 if total size exceeds max_size.
    """
    first_chunk = b""
    total = 0

    with open(tmp_path, "wb") as tmp:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            if not first_chunk:
                first_chunk = chunk
            total += len(chunk)
            if total > max_size:
                raise HTTPException(413, "文件大小超过限制（最大 10MB）")
            tmp.write(chunk)

    return first_chunk, total


def _get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _count_words(text: str) -> int:
    """统计词数：英文按空格，中文按字符折算"""
    cleaned = re.sub(r"<[^>]*>", "", text).strip()
    if not cleaned:
        return 0
    en_words = len([w for w in cleaned.split() if w])
    zh_chars = len(re.findall(r"[一-鿿]", cleaned))
    return en_words + int(zh_chars * 0.67)


# ============ 端点 ============


@router.post("/parse-file", response_model=ParseFileResponse)
async def parse_file(
    file: UploadFile = File(...),
    page_from: Optional[int] = Form(None),
    page_to: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
    _rate: None = Depends(check_file_upload_rate_limit),
):
    """
    上传文件并解析为文本

    支持 PDF / Word / TXT / MD 格式。
    PDF 支持指定页码范围（page_from / page_to）。
    """
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_FILE_EXTENSIONS)}")

    # 验证页码范围
    if page_from is not None and page_from < 1:
        raise HTTPException(400, "page_from 必须 >= 1")
    if page_to is not None and page_to < 1:
        raise HTTPException(400, "page_to 必须 >= 1")
    if page_from is not None and page_to is not None and page_from > page_to:
        raise HTTPException(400, "page_from 不能大于 page_to")

    # 流式写入临时文件（不把整个文件读入内存）
    suffix = ext
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name

    try:
        first_chunk, total_size = await _stream_upload_to_temp(file, MAX_FILE_SIZE, tmp_path)

        # Magic byte 验证（用第一个 chunk）
        if not _validate_file_content(first_chunk, ext):
            raise HTTPException(400, f"文件内容与扩展名不匹配，疑似非 {ext} 格式文件")

        total_pages = 0

        if ext == ".pdf":
            text, total_pages = _parse_pdf(tmp_path, page_from, page_to)
        elif ext == ".docx":
            text = _parse_docx(tmp_path)
        elif ext in (".txt", ".md"):
            # 从已写入的临时文件读取，避免双倍内存
            with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        else:
            text = ""

        text = text.strip()
        word_count = _count_words(text)

        return ParseFileResponse(
            text=text,
            filename=file.filename or "unknown",
            total_pages=total_pages,
            page_from=page_from,
            page_to=page_to,
            word_count=word_count,
            file_type=ext.lstrip("."),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        raise HTTPException(500, "文件解析失败，请检查文件是否损坏或格式正确")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.post("/ocr-image", response_model=OCRImageResponse)
async def ocr_image(
    file: UploadFile = File(...),
    engine: str = Form("aliyun"),
    current_user: dict = Depends(get_current_user),
    _rate: None = Depends(check_file_upload_rate_limit),
):
    """
    上传图片并 OCR 识别文字

    支持 JPG / PNG / WebP 格式。
    engine: aliyun（默认）或 llm
    """
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(400, f"不支持的图片格式: {ext}，仅支持 {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

    # 流式读取图片到临时文件，避免一次性加载
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp_path = tmp.name

    try:
        first_chunk, total_size = await _stream_upload_to_temp(file, MAX_FILE_SIZE, tmp_path)

        # Magic byte 验证图片内容
        if not _validate_file_content(first_chunk, ext):
            raise HTTPException(400, f"文件内容与扩展名不匹配，疑似非 {ext} 格式文件")

        # 图片 OCR 需要完整字节，从临时文件读回
        with open(tmp_path, "rb") as f:
            content = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    result = {}

    if engine == "aliyun":
        result = await _ocr_aliyun(content)
        # 如果阿里云失败，自动降级到 LLM
        if not result.get("text") and result.get("error"):
            logger.warning(f"阿里云 OCR 失败，降级到 LLM: {result['error']}")
            result = await _ocr_llm(content)
    elif engine == "llm":
        result = await _ocr_llm(content)
    else:
        raise HTTPException(400, f"不支持的 OCR 引擎: {engine}")

    if not result.get("text") and result.get("error"):
        logger.error(f"OCR 识别失败: {result['error']}")
        raise HTTPException(500, "OCR 识别失败，请稍后重试")

    text = result.get("text", "")
    return OCRImageResponse(
        text=text,
        confidence=result.get("confidence", 0),
        engine=result.get("engine", engine),
        word_count=_count_words(text),
    )


# ============ 内部函数 ============


def _parse_pdf(file_path: str, page_from: Optional[int], page_to: Optional[int]) -> tuple:
    """解析 PDF 文件，支持页码范围"""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)

    start = (page_from - 1) if page_from and page_from >= 1 else 0
    end = min(page_to, total_pages) if page_to and page_to >= 1 else total_pages

    if start >= end or start < 0:
        start = 0
        end = total_pages

    pages_text = []
    for i in range(start, end):
        page_text = reader.pages[i].extract_text() or ""
        pages_text.append(page_text)

    return "\n\n".join(pages_text), total_pages


def _parse_docx(file_path: str) -> str:
    """解析 Word 文件"""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


async def _ocr_aliyun(image_bytes: bytes) -> dict:
    """调用阿里云 OCR"""
    ak_id = settings.ALIYUN_OCR_ACCESS_KEY_ID
    ak_secret = settings.ALIYUN_OCR_ACCESS_KEY_SECRET

    if not ak_id or not ak_secret:
        return {"text": "", "confidence": 0, "engine": "aliyun", "error": "阿里云 OCR 未配置"}

    from app.services.ocr.aliyun_ocr import AliyunOCR

    ocr = AliyunOCR(ak_id, ak_secret, settings.ALIYUN_OCR_ENDPOINT)
    return ocr.recognize(image_bytes)


async def _ocr_llm(image_bytes: bytes) -> dict:
    """调用 LLM 视觉识别"""
    from app.services.ocr.llm_vision import recognize_with_llm

    return await recognize_with_llm(
        image_bytes=image_bytes,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
    )
