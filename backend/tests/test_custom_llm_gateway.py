import pytest
from unittest.mock import patch, MagicMock
from app.core.config import (
    CustomLLMConfig,
    call_llm,
    mask_api_key,
    check_llm_connection,
    active_custom_llm,
    _call_anthropic_api,
    settings
)

def test_custom_llm_config_defaults():
    cfg = CustomLLMConfig()
    assert cfg.provider_type == "openai"
    assert cfg.base_url is None
    assert cfg.api_key is None
    assert cfg.model_name is None
    assert cfg.temperature is None

def test_mask_api_key():
    assert mask_api_key(None) == "None"
    assert mask_api_key("") == "None"
    assert mask_api_key("12345") == "sk-***"
    assert mask_api_key("sk-1234567890abcdef") == "sk-1...cdef"

@patch("openai.OpenAI")
def test_openai_gateway_fallback_to_env(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="OpenAI Response"))]
    mock_client.chat.completions.create.return_value = mock_response

    # 1. 传入空配置 -> 回退到 .env
    res = call_llm("Hello", custom_llm_config={})
    assert res == "OpenAI Response"
    mock_openai_cls.assert_called_with(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=mock_openai_cls.call_args[1]["timeout"],
        max_retries=settings.LLM_MAX_RETRIES
    )

@patch("openai.OpenAI")
def test_openai_gateway_custom_override(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Custom OpenAI"))]
    mock_client.chat.completions.create.return_value = mock_response

    custom_cfg = {
        "provider_type": "openai",
        "base_url": "https://my-proxy.com/v1",
        "api_key": "sk-custom-123456",
        "model_name": "gpt-4o-custom",
        "temperature": 0.7
    }
    res = call_llm("Hello", custom_llm_config=custom_cfg)
    assert res == "Custom OpenAI"
    mock_openai_cls.assert_called_with(
        api_key="sk-custom-123456",
        base_url="https://my-proxy.com/v1",
        timeout=mock_openai_cls.call_args[1]["timeout"],
        max_retries=settings.LLM_MAX_RETRIES
    )
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-custom"
    assert call_kwargs["temperature"] == 0.7

@patch("httpx.Client")
def test_anthropic_gateway_dispatch(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [
            {"type": "text", "text": "Claude 3.5 Response"}
        ]
    }
    mock_client.post.return_value = mock_resp

    custom_cfg = {
        "provider_type": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key": "sk-ant-api03-12345",
        "model_name": "claude-3-5-sonnet-20241022"
    }
    res = call_llm("Hello Anthropic", system_prompt="You are Claude", custom_llm_config=custom_cfg)
    assert res == "Claude 3.5 Response"
    
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    url = call_args[0][0]
    headers = call_args[1]["headers"]
    payload = call_args[1]["json"]

    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "sk-ant-api03-12345"
    assert headers["anthropic-version"] == "2023-06-01"
    assert payload["system"] == "You are Claude"
    assert payload["model"] == "claude-3-5-sonnet-20241022"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Hello Anthropic"

@patch("app.core.config.call_llm")
def test_connection_testing(mock_call_llm):
    mock_call_llm.return_value = "pong"
    res = check_llm_connection({"provider_type": "openai"})
    assert res["success"] is True
    assert res["reply"] == "pong"
    assert "latency_ms" in res

@patch("app.core.config.call_llm")
def test_connection_testing_failure(mock_call_llm):
    mock_call_llm.side_effect = RuntimeError("Unauthorized")
    res = check_llm_connection({"provider_type": "openai"})
    assert res["success"] is False
    assert "Unauthorized" in res["error"]
