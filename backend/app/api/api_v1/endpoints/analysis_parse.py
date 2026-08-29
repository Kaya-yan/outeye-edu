"""
课文文件解析和 OCR 识别端点

支持上传 PDF/Word/TXT 文件提取文本，以及图片 OCR 识别文字。
"""

import asyncio
import os
import re
import tempfile
import time
from typing import Any, Dict, Optional, Tuple
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
    likely_scanned: bool = False


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

        # 扫描件/图片型 PDF：有页数但几乎提不出文本（每页平均不足 10 词）
        likely_scanned = ext == ".pdf" and total_pages > 0 and word_count < 10 * total_pages

        return ParseFileResponse(
            text=text,
            filename=file.filename or "unknown",
            total_pages=total_pages,
            page_from=page_from,
            page_to=page_to,
            word_count=word_count,
            file_type=ext.lstrip("."),
            likely_scanned=likely_scanned,
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


@router.get("/ocr-status")
async def ocr_status():
    """图片识别能力探针：前端据此决定是否展示拍照入口（无需登录）

    只查配置会误报 available:true（阿里云控制台未开通产品时返回
    ocrServiceNotOpen 401，配置却齐全）。因此对阿里云引擎追加一次真实
    RecognizeGeneral 调用（1x1 PNG），结果缓存 15 分钟；探测失败且与
    凭证无关时不翻转 available，仅透出 detail 供排查。
    """
    aliyun = bool(settings.ALIYUN_OCR_ACCESS_KEY_ID and settings.ALIYUN_OCR_ACCESS_KEY_SECRET)
    vision = bool(settings.LLM_VISION_MODEL)

    verified: Optional[bool] = None
    detail: Optional[str] = None
    if aliyun:
        if time.time() - _ocr_probe_cache["ts"] > _OCR_PROBE_TTL_SECONDS:
            async with _ocr_probe_lock:
                if time.time() - _ocr_probe_cache["ts"] > _OCR_PROBE_TTL_SECONDS:
                    try:
                        ok, detail = await asyncio.wait_for(
                            asyncio.to_thread(_probe_aliyun_ocr), timeout=15
                        )
                    except asyncio.TimeoutError:
                        ok, detail = None, None
                        logger.warning("阿里云 OCR 探测超时")
                    except Exception as e:
                        ok, detail = None, None
                        logger.warning(f"阿里云 OCR 探测异常: {e}")
                    _ocr_probe_cache.update(ts=time.time(), ok=ok, detail=detail)
        verified = _ocr_probe_cache["ok"]
        detail = _ocr_probe_cache["detail"]

    available = vision or (aliyun and verified is not False)
    return {
        "available": available,
        "verified": verified,
        "detail": detail,
        "engines": {"aliyun": aliyun, "llm_vision": vision},
    }


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
    aliyun_configured = bool(settings.ALIYUN_OCR_ACCESS_KEY_ID and settings.ALIYUN_OCR_ACCESS_KEY_SECRET)

    if engine == "aliyun" and not aliyun_configured and not settings.LLM_VISION_MODEL:
        # 两条链都不可用：短路返回 503，不空跑注定失败的调用
        raise HTTPException(
            503,
            "图片识别服务未配置（阿里云 OCR 凭证缺失，且未配置视觉模型），请联系管理员",
        )
    if engine == "llm" and not settings.LLM_VISION_MODEL:
        raise HTTPException(503, "视觉识别未配置（LLM_VISION_MODEL 未设置），无法使用 LLM 识别")

    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            400,
            f"不支持的图片格式: {ext}，仅支持 {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}，"
            f"如为 HEIC 请转换为 JPG 或 PNG 后上传",
        )

    # 流式读取图片到临时文件，避免一次性加载
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp_path = tmp.name

    try:
        first_chunk, total_size = await _stream_upload_to_temp(file, MAX_FILE_SIZE, tmp_path)

        # Magic byte 验证图片内容
        if not _validate_file_content(first_chunk, ext):
            raise HTTPException(400, f"文件内容与扩展名不匹配，疑似非 {ext} 格式文件，请转换为 JPG 或 PNG 后上传")

        # 图片 OCR 需要完整字节，从临时文件读回
        with open(tmp_path, "rb") as f:
            content = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # OCR 前置校验与归一化（HEIC/CMYK/尺寸），不合规时给用户明确的转换提示
    content, norm_err = _validate_and_normalize_image(content)
    if norm_err:
        raise HTTPException(400, norm_err)

    result = {}

    if engine == "aliyun":
        if aliyun_configured:
            result = await _ocr_aliyun(content)
            # 阿里云失败时仅在视觉模型可用时降级
            if not result.get("text") and result.get("error"):
                logger.warning(f"阿里云 OCR 失败: {result['error']}")
                if result.get("error_code") == "ocrServiceNotOpen":
                    # 负缓存：让 ocr-status 探针立即反映真实状态
                    _ocr_probe_cache.update(ts=time.time(), ok=False, detail=result["error"])
                if settings.LLM_VISION_MODEL:
                    result = await _ocr_llm(content)
        else:
            result = await _ocr_llm(content)
    elif engine == "llm":
        result = await _ocr_llm(content)
    else:
        raise HTTPException(400, f"不支持的 OCR 引擎: {engine}")

    if not result.get("text") and result.get("error"):
        logger.error(f"OCR 识别失败: {result['error']}")
        if result.get("error_code"):
            raise HTTPException(503, result["error"])
        raise HTTPException(503, f"图片识别失败：{result['error']}")

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


# ============ 阿里云 OCR 真实可用性探针 ============

_OCR_PROBE_TTL_SECONDS = 900
_ocr_probe_cache: Dict[str, Any] = {"ts": 0.0, "ok": None, "detail": None}
_ocr_probe_lock = asyncio.Lock()

# 探针图：100×30 真实文字 PNG（"OCR TEST"，黑字白底）。1×1 合成图会被阿里云以
# unsupportedImageFormat 415 拒绝，真实小图才能验证识别链路。运行时用 PIL 生成并缓存，
# 避免在源码里嵌一段易损坏的超长 base64。
_PROBE_IMAGE_CACHE: Dict[str, bytes] = {}


def _get_probe_image() -> bytes:
    if "png" not in _PROBE_IMAGE_CACHE:
        from io import BytesIO

        from PIL import Image, ImageDraw, ImageFont

        im = Image.new("RGB", (100, 30), (255, 255, 255))
        draw = ImageDraw.Draw(im)
        font = None
        for candidate in ("arial.ttf", "DejaVuSans.ttf", "NotoSansCJK-Regular.ttc"):
            try:
                font = ImageFont.truetype(candidate, 18)
                break
            except OSError:
                continue
        draw.text((10, 4), "OCR TEST", fill=(0, 0, 0), font=font or ImageFont.load_default())
        buf = BytesIO()
        im.save(buf, "PNG")
        _PROBE_IMAGE_CACHE["png"] = buf.getvalue()
    return _PROBE_IMAGE_CACHE["png"]


def _validate_and_normalize_image(content: bytes) -> tuple[Optional[bytes], Optional[str]]:
    """OCR 前置校验与归一化（PIL）。

    - 真实格式白名单（HEIC 等无法解码的格式给出明确转换提示，而非笼统"服务异常"）
    - 最短边 ≥15px、最长边 ≤8192px（超长截图自动缩放），符合 RecognizeGeneral 限制
    - CMYK / 透明通道 / 16 位色深统一压到白底 RGB，避免服务端 415
    返回 (归一化后的 bytes, None) 或 (None, 用户可读的错误信息)。
    """
    from io import BytesIO

    from PIL import Image

    try:
        im = Image.open(BytesIO(content))
        im.load()
    except Exception:
        return None, "图片文件无法读取，请转换为 JPG 或 PNG 后重新上传"

    fmt = (im.format or "").upper()
    if fmt not in {"JPEG", "PNG", "WEBP", "BMP"}:
        return None, f"暂不支持 {fmt or '该'} 格式图片（如 iPhone 默认的 HEIC），请转换为 JPG 或 PNG 后上传"

    w, h = im.size
    if min(w, h) < 15:
        return None, "图片尺寸过小（最短边需不小于 15 像素），请换用更清晰的图片"

    # 非 RGB 模式（CMYK/RGBA/P/16 位）统一压到白底 RGB
    if im.mode != "RGB":
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")

    # 超长边缩到 8192 以内（保持比例）
    if max(im.size) > 8192:
        ratio = 8192 / max(im.size)
        im = im.resize((max(15, round(im.size[0] * ratio)), max(15, round(im.size[1] * ratio))))

    if fmt == "JPEG" and im.mode == "RGB" and max(im.size) <= 8192 and im.size == (w, h):
        return content, None

    buf = BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue(), None


def _probe_aliyun_ocr() -> Tuple[Optional[bool], Optional[str]]:
    """真调一次 RecognizeGeneral；返回 (ok, detail)。ok=None 表示无法判定（网络/图片被拒等）"""
    from app.services.ocr.aliyun_ocr import AliyunOCR

    ocr = AliyunOCR(
        settings.ALIYUN_OCR_ACCESS_KEY_ID,
        settings.ALIYUN_OCR_ACCESS_KEY_SECRET,
        settings.ALIYUN_OCR_ENDPOINT,
    )
    result = ocr.recognize(_get_probe_image())
    if result.get("error_code") == "ocrServiceNotOpen":
        return False, result["error"]
    if result.get("error"):
        return None, f"阿里云 OCR 探测失败：{result['error']}"
    return True, None


async def _ocr_aliyun(image_bytes: bytes) -> dict:
    """调用阿里云 OCR"""
    ak_id = settings.ALIYUN_OCR_ACCESS_KEY_ID
    ak_secret = settings.ALIYUN_OCR_ACCESS_KEY_SECRET

    if not ak_id or not ak_secret:
        return {"text": "", "confidence": 0, "engine": "aliyun", "error": "阿里云 OCR 未配置"}

    from app.services.ocr.aliyun_ocr import AliyunOCR

    ocr = AliyunOCR(ak_id, ak_secret, settings.ALIYUN_OCR_ENDPOINT)
    return await asyncio.to_thread(ocr.recognize, image_bytes)


async def _ocr_llm(image_bytes: bytes) -> dict:
    """调用 LLM 视觉识别（仅当配置了多模态模型）"""
    if not settings.LLM_VISION_MODEL:
        return {"text": "", "confidence": 0, "engine": "llm", "error": "视觉模型未配置"}

    from app.services.ocr.llm_vision import recognize_with_llm

    return await recognize_with_llm(
        image_bytes=image_bytes,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_VISION_MODEL,
    )
