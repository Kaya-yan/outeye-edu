"""任务G1 语料清洗测试：审计分类 / 碎行合并 / 规范化 / 句界重切 / 质量过滤 / 展示修剪"""

import pytest

from app.services.rag.corpus_clean import (
    GLUED_TOKEN_RE,
    LEADING_CONT_CHARS,
    audit_chunk,
    audit_collection,
    chunk_quality,
    clean_document,
    excerpt_by_sentence,
    find_repeated_headers,
    merge_letter_spines,
    normalize_text,
    rechunk,
    single_char_line_ratio,
    split_sentences,
)

CLEAN_CN = (
    "Krashen 提出输入假说，即 i+1 理论。该理论认为语言习得需要略高于当前水平的输入。"
    "教师应当为学习者提供可理解性输入，这在二语习得领域具有重要影响，也是分层教学设计的理论依据。"
)
CLEAN_EN = (
    "Task-based language teaching focuses on meaning-driven tasks. "
    "Learners acquire language naturally while completing authentic activities. "
    "Teachers should design tasks that match the learners' proficiency level."
)


def _chunks(texts):
    return [{"content": t, "chunk_index": i} for i, t in enumerate(texts)]


class TestAuditChunk:
    def test_letter_spine_english(self):
        spine = "\n".join(list("s l a r g e l y a m a t t e r".replace(" ", "")))
        assert "letter_spine" in audit_chunk(spine + "\nAnother line stays normal.")

    def test_letter_spine_chinese(self):
        spine = "\n".join(list("知识库是教学的基础设施"))
        assert single_char_line_ratio(spine) > 0.9
        assert "letter_spine" in audit_chunk(spine)

    def test_mid_sentence_start(self):
        assert "mid_sentence" in audit_chunk("以必要的纠正，从而实现教学目标的达成")

    def test_mid_sentence_english_tail(self):
        assert "mid_sentence" in audit_chunk(
            "The theoretical basis of this approach comes from"
        )

    def test_mid_sentence_citation_cut(self):
        assert "mid_sentence" in audit_chunk("Long( 1988: 115-/141,/1991:39-/52")

    def test_noise_page_number(self):
        assert "noise_lines" in audit_chunk("正文第一段内容。\n12\n正文继续。")

    def test_too_short(self):
        assert "too_short" in audit_chunk("很短。")

    def test_clean_chunks_flagless(self):
        assert audit_chunk(CLEAN_CN) == []
        assert audit_chunk(CLEAN_EN) == []


class TestAuditCollection:
    def test_counts_and_pcts(self):
        report = audit_collection(_chunks([CLEAN_CN, CLEAN_EN, "很短。"]))
        assert report["total"] == 3 and report["flagged"] == 1
        assert report["counts"]["too_short"] == 1
        assert 30.0 < report["pcts"]["too_short"] < 40.0


class TestMergeLetterSpines:
    def test_chinese_direct_join(self):
        merged, glued = merge_letter_spines("\n".join(list("知识库是基础")) + "\n后续正常行。")
        assert merged == "知识库是基础\n后续正常行。"
        assert glued is False

    def test_english_glues_and_flags(self):
        merged, glued = merge_letter_spines("\n".join(list("slargelyamatter")) + "\nNormal line.")
        assert "slargelyamatter" in merged
        assert glued is True

    def test_normal_text_untouched(self):
        assert merge_letter_spines(CLEAN_CN)[0] == CLEAN_CN


class TestNormalize:
    def test_nfkc_fullwidth_and_zero_width(self):
        out = normalize_text("ＡＢＣ　全角")
        assert out == "ABC 全角"

    def test_drops_isolated_page_numbers(self):
        out = normalize_text("第一句。\n12\niv\n第 3 页\npage 4/12\n- 5 -\n第二句。")
        assert out == "第一句。\n第二句。"

    def test_drops_doc_level_headers(self):
        text = "外语教学理论与实践\n正文A。" * 3
        chunks = _chunks(["外语教学理论与实践\n正文A。"] * 3)
        headers = find_repeated_headers(chunks)
        assert "外语教学理论与实践" in headers
        assert normalize_text("外语教学理论与实践\n正文A。", drop_lines=headers) == "正文A。"

    def test_collapses_blank_runs(self):
        assert normalize_text("甲。\n\n\n\n乙。") == "甲。\n乙。"


class TestSplitAndRechunk:
    def test_split_keeps_trailing_quotes(self):
        s = split_sentences('他说："输入假说成立。"然后离开了。')
        assert s[0].endswith('"') or s[0].endswith("。")
        assert len(s) == 2

    def test_rechunk_never_cuts_sentence(self):
        long_text = "。".join(f"这是用于测试切分边界的第{i}个完整中文句子，内容长度适中" for i in range(80)) + "。"
        pieces = rechunk(split_sentences(long_text), min_len=100, max_len=250, overlap=1)
        assert len(pieces) > 3
        for p in pieces:
            assert p[-1] in "。！？；!?…\"”』」）)]】.", p[-10:]
            assert p[0] not in LEADING_CONT_CHARS and not (p[0].isascii() and p[0].islower())
            assert 50 <= len(p)

    def test_rechunk_overlap_one_sentence(self):
        sentences = [f"重叠测试句子编号{i}内容。" for i in range(40)]
        pieces = rechunk(sentences, min_len=40, max_len=90, overlap=1)
        for a, b in zip(pieces, pieces[1:]):
            last_of_a = a[:-1].split("。")[-1] + "。"
            first_of_b = b.split("。")[0] + "。"
            assert last_of_a == first_of_b

    def test_oversize_single_sentence_kept_whole(self):
        big = "超" * 300 + "。"
        pieces = rechunk([big], min_len=100, max_len=200)
        assert pieces == [big]

    def test_english_join_has_spaces(self):
        chunks = rechunk(["Sentence one ends.", "Sentence two ends.", "Sentence three ends."], min_len=1, max_len=100)
        assert chunks == ["Sentence one ends. Sentence two ends. Sentence three ends."]


class TestChunkQuality:
    def test_too_short_quarantined(self):
        ok, reason = chunk_quality("太短。")
        assert not ok and reason == "too_short"

    def test_glued_token_quarantined_only_with_glue_context(self):
        assert GLUED_TOKEN_RE.search("prefix slargelyamatter suffix")
        text = "The text contains slargelyamatter and more words to pass the length gate easily here."
        ok, reason = chunk_quality(text, had_glue=True)
        assert not ok and reason == "glued_needs_llm"

    def test_long_legit_word_passes_without_glue_context(self):
        text = ("Internationalization of higher education brings both opportunities "
                "and challenges to curriculum design in modern universities.")
        ok, _ = chunk_quality(text, had_glue=False)
        assert ok is True

    def test_clean_passes(self):
        assert chunk_quality(CLEAN_CN)[0] is True


class TestCleanDocument:
    def test_mixed_dirty_doc_comes_out_clean(self):
        dirty = [
            {"content": "\n".join(list("知识库是教学的")) + "\n基础。", "chunk_index": 0},
            {"content": "12\nKrashen 提出输入假说，即 i+1 理论。", "chunk_index": 1},
            {"content": "教师应当为学习者提供可理解性输入，", "chunk_index": 2},
            {"content": "这在二语习得领域具有重要影响，也是分层教学设计的理论依据。", "chunk_index": 3},
        ]
        clean, quarantined = clean_document(dirty, min_len=50, max_len=300)
        assert clean, "应至少产出一个可读 chunk"
        assert "12" not in "".join(clean)
        for p in clean:
            issues = audit_chunk(p)
            assert "letter_spine" not in issues and "noise_lines" not in issues, p

    def test_empty_doc_quarantined(self):
        clean, quarantined = clean_document([{"content": "", "chunk_index": 0}])
        assert clean == [] and quarantined


class TestExcerptBySentence:
    def test_short_text_unchanged(self):
        assert excerpt_by_sentence("第一段正文\n\n第二段正文", limit=8000) == "第一段正文\n\n第二段正文"

    def test_leading_partial_dropped(self):
        text = "以及在教学中的具体应用，值得深入探讨。输入假说是二语习得的核心理论之一。它强调可理解性输入的重要性。"
        out = excerpt_by_sentence(text, limit=8000)
        assert out.startswith("输入假说")

    def test_truncated_at_sentence_with_marker(self):
        text = CLEAN_CN * 3
        out = excerpt_by_sentence(text, limit=120)
        assert out.startswith("（节选）")
        assert out.endswith("。")
        assert len(out) <= 124

    def test_no_sentence_end_hard_cut(self):
        text = "无" * 300
        out = excerpt_by_sentence(text, limit=100)
        assert out.startswith("（节选）") and len(out) == 104
