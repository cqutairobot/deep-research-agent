import pytest
from app.services.cost_service import calculate_estimated_cost, estimate_tokens_from_text, create_initial_metrics

def test_token_estimation_heuristics():
    """断言：基于语言学的中文与英文分词估算逻辑符合预期"""
    zh_text = "全固态电池技术路线横评与工程化制造壁垒分析" # 20 字符
    tokens_zh = estimate_tokens_from_text(zh_text)
    assert 10 <= tokens_zh <= 20

    en_text = "Solid-state battery commercialization and manufacturing roadmap."
    tokens_en = estimate_tokens_from_text(en_text)
    assert 5 <= tokens_en <= 15

def test_cost_calculation_deepseek():
    """断言：DeepSeek 计费公式正确 (¥1/M in, ¥2/M out)"""
    res = calculate_estimated_cost({
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000
    }, model_name="deepseek-chat")
    # 1.0 + 2.0 = 3.0 元
    assert pytest.approx(res["total_cny"], 0.01) == 3.0
    assert res["total_usd"] > 0
    assert res["total_tokens"] == 2_000_000

def test_cost_calculation_openai():
    """断言：OpenAI GPT-4o-mini 单价换算正确"""
    res = calculate_estimated_cost({
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000
    }, model_name="gpt-4o-mini")
    # (0.15 + 0.60) * 7.25 = 5.4375 元
    assert pytest.approx(res["total_cny"], 0.1) == 5.4375

def test_initial_metrics_structure():
    """断言：初始化的算力数据结构包含完整的 Agent 节点"""
    metrics = create_initial_metrics()
    assert "node_breakdown" in metrics
    for node in ["planner", "researcher", "writer", "critic", "verifier"]:
        assert node in metrics["node_breakdown"]
