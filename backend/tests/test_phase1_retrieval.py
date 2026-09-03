import pytest
from unittest.mock import patch, MagicMock

from app.tools.search_tools import search_web, _search_you_com, _search_tavily, _search_ddgs
from app.tools.scrape_tools import scrape_url, _scrape_you_com
from app.tools.smart_reranker import (
    chunk_webpage_for_rerank,
    rerank_chunks,
    score_chunk,
    compute_rrf_score,
    fuse_ranked_lists
)

def test_you_com_search_success():
    """测试 You.com Search 成功响应解析"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": {
            "web": [
                {
                    "title": "Solid Power Commercialization Roadmap",
                    "url": "https://solidpowerbattery.com/all-solid-state",
                    "description": "Solid Power is developing all-solid-state battery cells.",
                    "snippets": [
                        "2026 pilot line production with 390 Wh/kg specific energy.",
                        "Partnership with BMW and Ford on automotive qualification."
                    ]
                }
            ]
        }
    }
    
    with patch("httpx.Client.post", return_value=mock_resp):
        with patch("app.core.config.settings.YDC_API_KEY", "test-you-key"):
            results = _search_you_com("solid state battery", max_results=2)
            assert len(results) == 1
            assert results[0]["title"] == "Solid Power Commercialization Roadmap"
            assert results[0]["url"] == "https://solidpowerbattery.com/all-solid-state"
            assert "390 Wh/kg" in results[0]["content"]
            assert results[0]["score"] == 0.98

def test_you_com_search_failover():
    """测试 You.com 搜索异常时平滑回退到 Tavily 与 DDGS"""
    # 模拟 You.com 抛出异常
    with patch("app.tools.search_tools._search_you_com", return_value=[]):
        with patch("app.tools.search_tools._search_tavily", return_value=[{
            "title": "Tavily Fallback Source",
            "url": "https://tavily.com/source",
            "content": "Tavily returned search data.",
            "snippet": "Tavily snippet",
            "score": 0.95
        }]):
            results = search_web("solid state battery", max_results=3)
            assert len(results) == 1
            assert results[0]["title"] == "Tavily Fallback Source"

def test_you_com_scrape_contents_api():
    """测试 You.com Contents API 抓取高质量 Markdown"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "url": "https://example.com/report",
            "markdown": "# 行业深度研究报告\n\n| 厂商 | 技术路线 | 能量密度 |\n|---|---|---|\n| 宁德时代 | 硫化物 | 500 Wh/kg |\n\n核心结论：全固态电池预计 2027 年小批量量产。",
            "title": "行业深度研报"
        }
    ]
    
    with patch("httpx.Client.post", return_value=mock_resp):
        with patch("app.core.config.settings.YDC_API_KEY", "test-you-key"):
            content = _scrape_you_com("https://example.com/report", timeout=5.0)
            assert content is not None
            assert "500 Wh/kg" in content
            assert "核心结论" in content

def test_smart_reranker_long_document():
    """测试 15,000 字符长文切块与 Rerank 智能段落召回 (确保末尾/中间关键段落不被遗漏)"""
    # 构造一篇超长网页：前 12,000 字符为无关噪音历史介绍，在第 13,000 字符处包含关键量化对比表格与结论
    noise_part = "公司历史沿革与组织架构介绍。\n\n" * 400 # 约 6,400 字符
    noise_part2 = "一般性行业背景描述与常识性介绍。\n\n" * 400 # 约 6,400 字符
    
    crucial_finding = (
        "## 核心技术参数与量化对比结论\n\n"
        "| 厂商名称 | 电解质体系 | 实测能量密度 (Wh/kg) | 循环寿命 (次) | 量产时间表 |\n"
        "|---|---|---|---|---|\n"
        "| 丰田 (Toyota) | 硫化物系 | 450 Wh/kg | 1500 次 | 2027~2028 年 |\n"
        "| 清陶能源 | 氧化物复合 | 368 Wh/kg | 2000 次 | 2025 年上车 |\n"
        "| QuantumScape | 固态陶瓷隔膜 | 400 Wh/kg | 1000 次 | 2026 年试产 |\n\n"
        "投资分析结论：硫化物体系在能量密度上具备终极优势，但存在空气敏感性与硫化氢副产物等商业化工艺痛点。"
    )
    
    full_long_doc = noise_part + noise_part2 + crucial_finding
    assert len(full_long_doc) > 10000

    # 1. 语义分块
    chunks = chunk_webpage_for_rerank(full_long_doc, chunk_size=800)
    assert len(chunks) >= 8

    # 2. 目标导向 Rerank
    query = "全固态电池 厂商参数对比 量产时间表"
    focus = "梳理各头部厂商能量密度指标与商业化时间表"
    top_chunks = rerank_chunks(chunks, query=query, focus=focus, top_k=3)

    assert len(top_chunks) == 3
    # 验证关键对比表格与结论被成功命中召回
    combined_top = "\n\n".join(top_chunks)
    assert "丰田 (Toyota)" in combined_top
    assert "450 Wh/kg" in combined_top
    assert "硫化物" in combined_top

def test_rrf_hybrid_fusion():
    """测试 RRF (Reciprocal Rank Fusion) 混合融合排序"""
    local_docs = [
        {"id": "doc_local_1", "text": "本地专有研报：宁德时代全固态电池专利分析"},
        {"id": "doc_local_2", "text": "本地专有研报：清陶能源装车实测数据"}
    ]
    web_docs = [
        {"id": "doc_web_1", "text": "网络公开新闻：丰田宣布2027年量产固态电池"},
        {"id": "doc_local_1", "text": "网络转载：宁德时代全固态电池专利分析"} # 重叠项
    ]

    fused = fuse_ranked_lists(
        ranked_lists_with_weights=[(local_docs, 1.5), (web_docs, 1.0)],
        id_key="id",
        k=60
    )

    assert len(fused) == 3
    # doc_local_1 在本地排第 1，在网络排第 2，且本地权重更高，其 RRF 得分必定为最高
    assert fused[0]["id"] == "doc_local_1"
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]
