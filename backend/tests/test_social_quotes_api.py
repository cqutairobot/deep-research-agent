from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_social_quotes_generation():
    """断言：接口返回金句、预测、建议及全平台格式化文案。"""
    mock_llm_json = '''
    {
      "title": "光伏钙钛矿叠层",
      "punchline": "钙钛矿的胜负手不在理论光电转换率，而在大面积涂布均一性与水氧隔绝寿命。",
      "predictions": [
        "2026年GW级产线落地",
        "叠层组件毛利率保持35%以上",
        "传统晶硅龙头全面转向钙钛矿叠层技术采购"
      ],
      "action_advice": "提前布局专用真空涂布机装备与封装胶膜供应商。",
      "platforms": {
        "twitter_thread": "🧵 深度拆解：钙钛矿叠层...",
        "jike_post": "💡 今日硬核：钙钛矿...",
        "xiaohongshu": "🔥 终于把钙钛矿讲透了！"
      }
    }
    '''
    with patch("app.services.social_quotes_service.call_llm", return_value=mock_llm_json):
        res = client.post("/api/v1/research/social-quotes/generate", json={
            "title": "光伏钙钛矿叠层",
            "report": "测试内容..."
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "胜负手" in data["punchline"]
        assert len(data["predictions"]) == 3
        assert "twitter_thread" in data["platforms"]
        assert "jike_post" in data["platforms"]
        assert "xiaohongshu" in data["platforms"]
