from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_infographic_dynamic_llm():
    """断言：大模型返回标准 JSON 时，社交长图接口返回完整的三大指标、两句总结和三大洞察。"""
    mock_llm_json = '''
    {
      "metrics": [
        {"value": "3,000+通道", "label": "电极通道密度", "sub": "单芯片微电极集成突破"},
        {"value": "85%准确率", "label": "运动意图解码率", "sub": "毫秒级端侧低延迟推理"},
        {"value": "2026窗口期", "label": "人体临床转化", "sub": "多中心试验进入关键阶段"}
      ],
      "summary_lines": [
        "• 侵入式微电极高密度集成构筑信号采集核心护城河。",
        "• 算法软硬件一体化与临床数据闭环是规模化商业化的关键。"
      ],
      "insights": [
        {"num": "01", "title": "电极生物相容性决定长期植入寿命", "content": "柔性聚酰亚胺薄膜与微通道封装技术大幅降低胶质瘢痕反应。"},
        {"num": "02", "title": "算法平台毛利率天花板高于硬件电极", "content": "随着临床真实世界数据积累，解码算法模型构成持续收费的高壁垒飞轮。"},
        {"num": "03", "title": "伦理与监管合规成为准入核心考量", "content": "中美欧医疗器械快速通道认证与神经数据隐私法案重塑准入门槛。"}
      ]
    }
    '''
    with patch("app.services.infographic_service.call_llm") as mock_llm:
        mock_llm.return_value = mock_llm_json
        resp = client.post("/api/v1/research/infographic/generate", json={
            "title": "脑机接口临床试验突破",
            "report": "正文内容..."
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["metrics"]) == 3
        assert data["metrics"][0]["value"] == "3,000+通道"
        assert len(data["insights"]) == 3
        assert data["insights"][0]["title"] == "电极生物相容性决定长期植入寿命"
        mock_llm.assert_called_once()

def test_infographic_fallback_handling():
    """断言：当大模型发生网络异常时，平滑降级生成连贯完整的兜底结构，绝无残句。"""
    with patch("app.services.infographic_service.call_llm", side_effect=Exception("Timeout")):
        resp = client.post("/api/v1/research/infographic/generate", json={
            "title": "测试课题",
            "report": "测试内容..."
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "fallback"
        assert len(data["metrics"]) == 3
        assert len(data["insights"]) == 3
        for ins in data["insights"]:
            assert len(ins["title"]) > 0
            assert len(ins["content"]) > 10
