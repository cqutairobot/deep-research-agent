from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_recommendation_dynamic_llm():
    """断言：大模型返回合法 JSON 时，接口正确解析并返回 4 个推荐课题。"""
    mock_response = '''
    [
      {"title": "🚀 可回收火箭复用", "text": "全流量分级燃烧循环发动机甲烷复用寿命与入轨成本核算"},
      {"title": "🧬 单细胞测序图谱", "text": "人类肿瘤微环境单细胞空间转录组学高通量测序与新靶点发现"},
      {"title": "⚡ 钙钛矿叠层电池", "text": "钙钛矿/晶硅叠层太阳能电池效率突破与大面积封装可靠性"},
      {"title": "🤖 具身智能灵巧手", "text": "高自由度触觉感知灵巧手腱绳驱动方案与泛化操作策略"}
    ]
    '''
    with patch("app.services.recommendation_service.call_llm") as mock_llm:
        mock_llm.return_value = mock_response
        resp = client.post("/api/v1/research/recommendations", json={"count": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        topics = data["topics"]
        assert len(topics) == 4
        assert topics[0]["title"] == "🚀 可回收火箭复用"
        assert "全流量" in topics[0]["text"]
        mock_llm.assert_called_once()

def test_recommendation_fallback_sampling():
    """断言：当大模型发生异常时，接口优雅降级从题材库随机抽样 4 个互不相同的课题。"""
    with patch("app.services.recommendation_service.call_llm", side_effect=Exception("LLM Timeout")):
        resp = client.post("/api/v1/research/recommendations", json={"count": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        topics = data["topics"]
        assert len(topics) == 4
        # 验证 4 个课题标题互不相同
        titles = [t["title"] for t in topics]
        assert len(set(titles)) == 4
        for t in topics:
            assert len(t["title"]) > 0
            assert len(t["text"]) > 10
