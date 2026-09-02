import pytest
from app.tools.search_tools import search_web
from app.tools.scrape_tools import scrape_url

def test_search_web_basic():
    """测试基础搜索功能与返回数据结构"""
    query = "全固态电池 硫化物 量产进度"
    results = search_web(query, max_results=3)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3
    
    first = results[0]
    assert "title" in first
    assert "url" in first
    assert "content" in first
    assert "snippet" in first
    assert isinstance(first["title"], str)
    assert len(first["title"]) > 0

def test_search_web_generic_query():
    """测试通用命题的检索鲁棒性"""
    query = "AI Agent 前沿演进与落地"
    results = search_web(query, max_results=2)
    assert len(results) > 0
    assert len(results) <= 2
    assert results[0]["score"] > 0

def test_scrape_url_invalid():
    """测试非法 URL 异常处理"""
    result = scrape_url("invalid-url-schema")
    assert "[Error]" in result or "非法" in result

def test_scrape_url_structure():
    """测试网页抓取返回结构"""
    url = "https://example.com"
    result = scrape_url(url, timeout=5.0)
    assert isinstance(result, str)
    assert len(result) > 0
