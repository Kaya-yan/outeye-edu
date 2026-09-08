"""任务E1 上传文件体检：确定性校验（拒绝/警告）+ 编码自动检测"""

import pytest

from app.api.api_v1.endpoints.analysis_parse import (
    _decode_text_auto,
    _inspect_text,
)
from app.core.security import get_current_user
from app.main import app


def _auth():
    async def override():
        return {"user_id": "user-1", "email": "t@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override


# ---- 编码自动检测 ----


def test_decode_utf8_and_bom():
    assert _decode_text_auto("hello 课文".encode("utf-8")) == "hello 课文"
    assert _decode_text_auto("带 BOM 的课文".encode("utf-8-sig")) == "带 BOM 的课文"


def test_decode_gbk_fallback():
    raw = "这是一篇中文课文，用 GBK 编码保存。".encode("gbk")
    assert _decode_text_auto(raw) == "这是一篇中文课文，用 GBK 编码保存。"


def test_decode_utf16_with_bom():
    raw = "UTF-16 课文".encode("utf-16")
    assert "UTF-16 课文" in _decode_text_auto(raw)


def test_decode_undecodable_falls_back_to_replace():
    raw = b"\xff\xfe\xfa" + b"A" * 10
    text = _decode_text_auto(raw)
    assert text.count("�") >= 1 and "A" in text


# ---- 文本体检：拒绝 ----


def test_clean_text_passes_without_warning():
    reject, warning = _inspect_text("word " * 100, ".txt")
    assert reject is None and warning is None


def test_scanned_pdf_rejected_with_actionable_advice():
    reject, warning = _inspect_text("   \n  ", ".pdf", total_pages=3)
    assert reject and "扫描件" in reject and "拍照识别" in reject and "3" in reject
    assert warning is None


def test_short_text_rejected():
    reject, _ = _inspect_text("too short", ".txt")
    assert reject and "有效文本" in reject


def test_binary_like_content_rejected():
    junk = "\x00\x01\x02" * 20 + "x" * 100
    reject, _ = _inspect_text(junk, ".txt")
    assert reject and "二进制" in reject


def test_mojo_killed_encoding_rejected():
    broken = "�" * 20 + "some text here to fill length" * 2
    reject, _ = _inspect_text(broken, ".txt")
    assert reject and "编码" in reject and "UTF-8" in reject


# ---- 文本体检：可疑警告放行 ----


def test_slightly_broken_encoding_warns_but_passes():
    text = "课文内容" * 20 + "�" * 2
    reject, warning = _inspect_text(text, ".txt")
    assert reject is None and warning and "乱码" in warning


def test_few_control_chars_warns_but_passes():
    text = "word " * 100 + "\x01\x02"
    reject, warning = _inspect_text(text, ".txt")
    assert reject is None and warning and "控制字符" in warning


# ---- 端点级：GBK txt 上传成功解码 + 坏文件 400 ----


@pytest.mark.asyncio
async def test_parse_file_endpoint_gbk_txt_and_reject(client):
    _auth()
    gbk_bytes = "这是一篇用于端到端验证的中文课文，长度超过三十个有效字符以满足体检下限。".encode("gbk")
    resp = client.post(
        "/api/v1/analysis/parse-file",
        files={"file": ("课文.txt", gbk_bytes, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "中文课文" in data["text"] and "�" not in data["text"]
    assert data["warning"] is None

    binary = b"\x00\x01\x02\x03" * 100
    resp2 = client.post(
        "/api/v1/analysis/parse-file",
        files={"file": ("junk.txt", binary, "application/octet-stream")},
    )
    assert resp2.status_code == 400
    assert "二进制" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_parse_file_endpoint_scanned_pdf_rejected(client, monkeypatch):
    from app.api.api_v1.endpoints import analysis_parse as ap

    _auth()

    monkeypatch.setattr(ap, "_parse_pdf", lambda path, a, b: ("  ", 5))
    # PDF 魔数开头（伪造一个最小 PDF 头即可过 magic byte），解析层被 mock 为空文本
    resp = client.post(
        "/api/v1/analysis/parse-file",
        files={"file": ("scan.pdf", b"%PDF-1.4 minimal", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "扫描件" in resp.json()["detail"] and "拍照识别" in resp.json()["detail"]
