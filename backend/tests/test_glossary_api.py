from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_glossary_explainer_dynamic():
    """断言：划词释义由大模型动态生成，并严格约束在 130 字以内。"""
    with patch("app.services.glossary_service.call_llm") as mock_llm:
        mock_llm.return_value = "BOM 指的是制造电芯所需的全部原材料直接采购成本汇总。"
        resp = client.post("/api/v1/research/glossary", json={
            "term": "BOM成本",
            "context": "在全固态电芯制造工艺中，BOM成本占比超过60%，干法电极是降本关键。"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["term"] == "BOM成本"
        assert "BOM" in data["explanation"]
        assert len(data["explanation"]) <= 130
        mock_llm.assert_called_once()

def test_glossary_cache_instant_response():
    """断言：同一词汇在当前会话中二次查询命中缓存，无需重复调用大模型。"""
    with patch("app.services.glossary_service.call_llm") as mock_llm:
        mock_llm.return_value = "CRISPR 是一种革命性的基因组编辑技术。"
        # 第一次请求
        resp1 = client.post("/api/v1/research/glossary", json={"term": "CRISPR", "context": "生物医药基因编辑"})
        assert resp1.status_code == 200
        assert resp1.json()["cached"] is False
        assert mock_llm.call_count == 1

        # 第二次请求 (应直接命中内存缓存)
        resp2 = client.post("/api/v1/research/glossary", json={"term": "CRISPR", "context": "生物医药基因编辑"})
        assert resp2.status_code == 200
        assert resp2.json()["cached"] is True
        # 确认没有重复请求大模型
        assert mock_llm.call_count == 1

def test_glossary_empty_term_handling():
    """断言：传入空术语时给出友好提示而非崩溃。"""
    resp = client.post("/api/v1/research/glossary", json={"term": "   ", "context": "上下文"})
    assert resp.status_code == 422 or resp.json().get("status") == "error"

