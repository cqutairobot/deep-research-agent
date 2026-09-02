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
