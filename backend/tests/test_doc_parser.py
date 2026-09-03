import pytest
from app.tools.doc_parser import parse_uploaded_document, chunk_text

def test_parse_txt_document():
    """测试 TXT/MD 文本解析与分块"""
    content = "第一段：这是关于全固态电池硫化物路线的核心结论。\n\n第二段：宁德时代与丰田宣布2027年量产。"
    result = parse_uploaded_document("test.txt", content.encode('utf-8'))
    assert result["file_name"] == "test.txt"
    assert result["char_count"] > 0
    assert result["chunk_count"] >= 1
    assert len(result["chunks"]) >= 1

def test_chunk_text_boundaries():
    """测试长文本语义切片边界"""
    long_text = "段落内容 " * 200
    chunks = chunk_text(long_text, chunk_size=300)
    assert len(chunks) > 1
    for ch in chunks:
        assert len(ch) > 0

def test_reject_legacy_doc_format():
    """测试明确拒绝旧版 .doc 二进制格式 (Bug 9)"""
    with pytest.raises(ValueError) as exc_info:
        parse_uploaded_document("legacy_document.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    assert "不支持旧版 Word .doc" in str(exc_info.value)

def test_reject_oversized_file():
    """测试拒绝超过 15MB 的超大文件 (Bug 9)"""
    huge_bytes = b"A" * (16 * 1024 * 1024) # 16MB
    with pytest.raises(ValueError) as exc_info:
        parse_uploaded_document("large.txt", huge_bytes)
    assert "超出允许的 15MB 上限" in str(exc_info.value)

def test_reject_corrupt_pdf_magic_bytes():
    """测试拒绝损坏/伪造扩展名的 PDF (Bug 9)"""
    with pytest.raises(ValueError) as exc_info:
        parse_uploaded_document("fake.pdf", b"NOT_A_PDF_HEADER_CONTENT")
    assert "PDF 文件头损坏" in str(exc_info.value)

def test_reject_unsupported_format():
    """测试拒绝不受支持的文件格式 (Bug 9)"""
    with pytest.raises(ValueError) as exc_info:
        parse_uploaded_document("malicious.exe", b"MZ\x90\x00")
    assert "不支持的文件格式" in str(exc_info.value)
