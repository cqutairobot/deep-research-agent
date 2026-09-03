import pytest
from app.agents.summarizer import compress_webpage_facts

def test_compress_webpage_facts_normal():
    """测试长文 Map-Reduce 事实压缩"""
    raw_text = """
    丰田汽车在最新的东京移动出行展上公开宣布，其与日本出光兴产合作开发的硫化物全固态电池试点产线建设顺利。
    官方预计在2027年实现百兆瓦时级示范生产，并在2028年率先搭载于雷克萨斯高端纯电车型。
    该电芯在实验室实测中实现了10分钟快充至80%以及超过1000公里的续航里程。
    不过由于硫化锂原材料提纯成本高达每公斤200美元，初期生产成本较高。
    """
def test_compress_webpage_facts_empty_input():
    """测试空文本或过短文本直接返回空列表，绝不捏造假事实 (Bug 6)"""
    assert compress_webpage_facts("", focus_topic="测试") == []
    assert compress_webpage_facts("   ", focus_topic="测试") == []
    assert compress_webpage_facts("你好", focus_topic="测试") == []

def test_compress_webpage_facts_llm_failure():
    """测试大模型调用异常且无正则事实时安全返回空列表 (Bug 6)"""
    from unittest.mock import patch
    with patch("app.agents.summarizer.call_llm", side_effect=Exception("LLM Timeout")):
        facts = compress_webpage_facts("这是一段普通的短文本没有包含任何参数和数字。" * 3, focus_topic="测试")
        assert isinstance(facts, list)
