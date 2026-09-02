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
    facts = compress_webpage_facts(raw_text, focus_topic="丰田固态电池量产时间表与性能参数", max_facts=3)
    assert isinstance(facts, list)
    assert len(facts) > 0
    assert len(facts) <= 3
    # 验证提取到了具体事实
    combined = " ".join(facts)
    assert any(k in combined for k in ["2027", "2028", "丰田", "硫化物", "1000", "快充"])
