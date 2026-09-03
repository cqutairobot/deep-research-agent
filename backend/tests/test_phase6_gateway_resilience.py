from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import CustomLLMConfig, call_llm
from app.services.recommendation_service import generate_recommendations
from app.services.infographic_service import generate_infographic_data
from app.services.podcast_service import generate_podcast_dialogue
from app.services.mindmap_service import generate_causal_mindmap
from app.services.social_quotes_service import generate_social_quotes
from app.services.nli_service import evaluate_report_grounding
from app.services.glossary_service import explain_term_in_context

client = TestClient(app)

def test_gateway_invalid_auth_failover():
    """断言：当模型网关遭遇认证失败或超时时，各大下游服务均具备秒级保底兜底能力，不向用户抛出 500 崩溃。"""
    broken_config = CustomLLMConfig(
        provider_type="openai",
        base_url="https://invalid-non-existent-domain.internal/v1",
        api_key="sk-invalid-fake-key",
        model_name="mock-model"
    )

    with patch("app.core.config.call_llm", side_effect=Exception("Gateway Timeout / Auth Failed")):
        # 1. 推荐课题平滑兜底
        recs = generate_recommendations(custom_llm_config=broken_config, count=4)
        assert len(recs) == 4
        assert any("title" in r for r in recs)

        # 2. 视觉长图数据平滑兜底
        info = generate_infographic_data("测试标题", "测试正文", custom_llm_config=broken_config)
        assert info["status"] == "fallback"
        assert len(info["metrics"]) == 3

        # 3. 双人播客台词平滑兜底
        script = generate_podcast_dialogue("测试课题", "测试正文", custom_llm_config=broken_config)
        assert len(script) >= 4
        assert any(s["speaker"] == "Yunxi" for s in script)
        assert any(s["speaker"] == "Xiaoxiao" for s in script)

        # 4. 因果思维导图平滑兜底
        mindmap = generate_causal_mindmap("测试课题", "测试正文", custom_llm_config=broken_config)
        assert mindmap["status"] == "fallback"
        assert "graph LR" in mindmap["mermaid_code"]

        # 5. 社交爆款金句平滑兜底
        quotes = generate_social_quotes("测试课题", "测试正文", custom_llm_config=broken_config)
        assert quotes["status"] == "fallback"
        assert "punchline" in quotes
        assert "twitter_thread" in quotes["platforms"]

        # 6. NLI 事实雷达平滑兜底
        nli = evaluate_report_grounding("测试正文 [^cite:1]", citations=[], custom_llm_config=broken_config)
        assert nli["status"] == "fallback"
        assert nli["fact_grounding_score"] >= 90

        # 7. 专有名词释义平滑兜底
        gloss = explain_term_in_context("BOM成本", "测试上下文", custom_llm_config=broken_config)
        assert "BOM" in gloss["explanation"]
