from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.podcast_service import generate_podcast_dialogue

client = TestClient(app)

def test_podcast_dialogue_generation():
    """断言：大模型返回双人对谈剧本，包含云希与晓晓的交替台词。"""
    mock_llm_json = '''
    [
      {"speaker": "Yunxi", "name": "云希", "role": "行业观察员", "text": "晓晓，这份关于全固态电池的报告太硬核了！"},
      {"speaker": "Xiaoxiao", "name": "晓晓", "role": "技术专家", "text": "没错，云希。它直击了硫化物界面阻抗的核心瓶颈。"},
      {"speaker": "Yunxi", "name": "云希", "role": "行业观察员", "text": "那商业化落地的真实时间表呢？"},
      {"speaker": "Xiaoxiao", "name": "晓晓", "role": "技术专家", "text": "预计 2027 年会在特定高端场景率先实现百 GWh 突破。"}
    ]
    '''
    with patch("app.services.podcast_service.call_llm", return_value=mock_llm_json):
        script = generate_podcast_dialogue("全固态电池", "正文内容...")
        assert len(script) == 4
        assert script[0]["speaker"] == "Yunxi"
        assert script[1]["speaker"] == "Xiaoxiao"
        assert "全固态" in script[0]["text"] or "晓晓" in script[0]["text"]

def test_podcast_dialogue_fallback():
    """断言：当大模型超时时，触发稳健的结构化双人对谈兜底剧本。"""
    with patch("app.services.podcast_service.call_llm", side_effect=Exception("Timeout")):
        script = generate_podcast_dialogue("脑机接口", "正文内容...")
        assert len(script) >= 4
        speakers = {s["speaker"] for s in script}
        assert "Yunxi" in speakers and "Xiaoxiao" in speakers
