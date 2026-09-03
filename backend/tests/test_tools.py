import pytest
from unittest.mock import patch
from app.tools.search_tools import search_web
from app.tools.scrape_tools import scrape_url

def test_search_web_failure_returns_empty_list():
    """测试网络/检索异常时返回空列表，杜绝任何假造 URL 与论据 (Bug 5)"""
    with patch("app.tools.search_tools.DDGS") as mock_ddgs:
        mock_instance = mock_ddgs.return_value
        mock_instance.text.side_effect = Exception("Connection timeout / DNS failed")
        
        results = search_web("测试搜索故障", max_results=3)
        assert isinstance(results, list)
        assert len(results) == 0  # 严禁生成 fake fallback 数据

def test_search_web_mocked_success():
    """测试 DuckDuckGo 搜索成功时的字段标准化"""
    mock_raw_items = [
        {"title": "全固态电池最新进展", "href": "https://example.com/battery", "body": "丰田计划2027年量产。"}
    ]
    with patch("app.tools.search_tools.DDGS") as mock_ddgs:
        mock_instance = mock_ddgs.return_value
        mock_instance.text.return_value = mock_raw_items
        
        results = search_web("全固态电池", max_results=3)
        assert len(results) == 1
        assert results[0]["title"] == "全固态电池最新进展"
        assert results[0]["url"] == "https://example.com/battery"
        assert "丰田计划2027年量产" in results[0]["snippet"]
        assert results[0]["score"] == 0.9

def test_scrape_url_invalid():
    """测试非法 URL 异常处理"""
    result = scrape_url("invalid-url-schema")
    assert "[Error]" in result or "非法" in result

def test_scrape_url_network_failure():
    """测试抓取超时或网络故障时的降级提示"""
    with patch("httpx.Client.get", side_effect=Exception("Connection timeout")):
        result = scrape_url("https://unreachable-domain.xyz", timeout=1.0)
        assert "网页抓取摘要" in result or "unreachable-domain.xyz" in result
