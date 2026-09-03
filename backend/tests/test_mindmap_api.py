from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.mindmap_service import generate_causal_mindmap

client = TestClient(app)

def test_mindmap_generation_success():
    """断言：大模型返回标准 Mermaid 与因果节点结构。"""
    mock_llm_json = '''
    {
      "title": "具身智能手",
      "summary": "解构具身智能灵巧手在触觉感知与机械直驱之间的因果权衡。",
      "mermaid_code": "graph LR\\n    A[\\"触觉高频采样\\"] -->|制约| B[\\"算力延迟\\"]",
      "nodes": [
        {"id": "A", "label": "触觉高频采样", "type": "challenge", "detail": "..."},
        {"id": "B", "label": "算力延迟", "type": "tradeoff", "detail": "..."},
        {"id": "C", "label": "端侧轻量模型", "type": "solution", "detail": "..."},
        {"id": "D", "label": "量产拐点", "type": "convergence", "detail": "..."}
      ],
      "edges": [
        {"from": "A", "to": "B", "relation": "causes", "label": "制约"},
        {"from": "B", "to": "C", "relation": "solves", "label": "解决"}
      ]
    }
    '''
    with patch("app.services.mindmap_service.call_llm", return_value=mock_llm_json):
        res = client.post("/api/v1/research/mindmap/generate", json={
            "title": "具身智能手",
            "report": "测试研报..."
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["nodes"]) == 4
        assert "graph LR" in data["mermaid_code"]

def test_mindmap_generation_fallback():
    """断言：网络异常时平滑输出标准 Mermaid 因果图谱结构。"""
    with patch("app.services.mindmap_service.call_llm", side_effect=Exception("Network Error")):
        data = generate_causal_mindmap("量子计算", "研报测试内容...")
        assert data["status"] == "fallback"
        assert "graph LR" in data["mermaid_code"]
        assert len(data["nodes"]) >= 8
