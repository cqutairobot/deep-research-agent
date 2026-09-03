import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# 修复 macOS 环境下 NO_PROXY/no_proxy 包含 IPv6 地址 (::1) 导致 httpx 抛出 Invalid port: ':1' 异常
for _proxy_key in ["NO_PROXY", "no_proxy"]:
    if _proxy_key in os.environ and "::" in os.environ[_proxy_key]:
        os.environ[_proxy_key] = ",".join([p.strip() for p in os.environ[_proxy_key].split(",") if "::" not in p])

class Settings:
    """系统全局配置与大模型客户端包装器"""
    
    def __init__(self):
        self.reload()

    def reload(self):
        load_dotenv(override=True)
        self.LLM_API_KEY = (
            os.getenv("TASK_LLM_API_KEY") or 
            os.getenv("LLM_API_KEY") or 
            os.getenv("OPENAI_API_KEY", "")
        ).strip()
        
        self.LLM_BASE_URL = (
            os.getenv("TASK_LLM_BASE_URL") or 
            os.getenv("LLM_BASE_URL") or 
            "https://api.deepseek.com"
        ).strip()
        
        self.LLM_MODEL = (
            os.getenv("TASK_LLM_MODEL") or 
            os.getenv("LLM_MODEL") or 
            "deepseek-v4-flash-vision-exp"
        ).strip()
        
        self.YDC_API_KEY = (
            os.getenv("YDC_API_KEY") or 
            os.getenv("YOU_API_KEY") or 
            ""
        ).strip()
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
        self.JINA_API_KEY = os.getenv("JINA_API_KEY", None)
        self.MAX_SEARCH_RESULTS_PER_QUERY = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
        self.SCRAPER_TIMEOUT_SECONDS = float(os.getenv("SCRAPER_TIMEOUT", "15.0"))
        self.LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT", "60.0"))
        self.LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

settings = Settings()

from contextvars import ContextVar
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

active_custom_llm: ContextVar[Optional[Dict[str, Any]]] = ContextVar("active_custom_llm", default=None)

class CustomLLMConfig(BaseModel):
    provider_type: Literal["openai", "anthropic"] = Field("openai", description="服务协议类型: openai 兼容格式 或 anthropic 原生格式")
    base_url: Optional[str] = Field(None, description="自定义 Base URL，留空走系统默认")
    api_key: Optional[str] = Field(None, description="自定义 API Key，留空走系统默认")
    model_name: Optional[str] = Field(None, description="模型名称，留空走默认")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="采样温度")

def mask_api_key(key: Optional[str]) -> str:
    """脱敏 API Key 显示，保护用户隐私与凭据安全"""
    if not key:
        return "None"
    key_str = str(key).strip()
    if len(key_str) <= 8:
        return "sk-***"
    return f"{key_str[:4]}...{key_str[-4:]}"

def check_llm_connection(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    快速测试自定义模型连接连通性
    """
    import time
    start_time = time.time()
    try:
        res = call_llm(
            prompt="Hello, please reply with 'pong'.",
            system_prompt="You are a connection test agent.",
            temperature=0.1,
            max_tokens=20,
            custom_llm_config=config
        )
        latency_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "success": True,
            "message": "模型连接成功！",
            "reply": res,
            "latency_ms": latency_ms
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def _call_anthropic_api(
    prompt: str,
    system_prompt: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: float
) -> str:
    """
    Anthropic 原生 Messages API 适配器 (POST /v1/messages)
    """
    import httpx
    
    url = base_url.rstrip("/")
    if not url.endswith("/messages"):
        if not url.endswith("/v1"):
            url += "/v1/messages"
        else:
            url += "/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    custom_timeout = httpx.Timeout(timeout=timeout_seconds, connect=10.0)
    with httpx.Client(timeout=custom_timeout) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Anthropic API 请求异常 (HTTP {resp.status_code}): {resp.text}")
        data = resp.json()
        contents = data.get("content", [])
        text_parts = [c.get("text", "") for c in contents if c.get("type") == "text"]
        return "".join(text_parts).strip()

def call_llm(
    prompt: str,
    system_prompt: str = "You are an expert autonomous AI research assistant.",
    temperature: float = 0.3,
    max_tokens: int = 8192,
    custom_llm_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    统一调用真实大模型接口 (支持 OpenAI 兼容协议与 Anthropic 原生协议，支持自定义参数与平滑降级回退)
    """
    settings.reload()
    
    cfg = custom_llm_config or active_custom_llm.get() or {}
    
    provider_type = cfg.get("provider_type", "openai")
    api_key = (cfg.get("api_key") or "").strip() or settings.LLM_API_KEY
    base_url = (cfg.get("base_url") or "").strip() or settings.LLM_BASE_URL
    model_name = (cfg.get("model_name") or "").strip()
    
    # 温度配置
    temp = cfg.get("temperature")
    used_temperature = temp if (temp is not None and isinstance(temp, (int, float))) else temperature

    if not api_key:
        raise ValueError("【缺少 LLM API Key】请在设置中配置自定义 API Key 或在 backend/.env 文件中配置 LLM_API_KEY。")

    try:
        if provider_type == "anthropic":
            used_model = model_name or "claude-3-5-sonnet-20241022"
            return _call_anthropic_api(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=api_key,
                base_url=base_url if base_url != "https://api.deepseek.com" else "https://api.anthropic.com",
                model_name=used_model,
                temperature=used_temperature,
                max_tokens=max_tokens,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS
            )
        else:
            # 默认走 OpenAI 兼容协议
            from openai import OpenAI
            import httpx
            
            custom_timeout = httpx.Timeout(
                timeout=settings.LLM_TIMEOUT_SECONDS,
                connect=10.0
            )
            
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=custom_timeout,
                max_retries=settings.LLM_MAX_RETRIES
            )
            
            used_model = model_name or settings.LLM_MODEL
            
            response = client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=used_temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content or ""
            return content.strip()

    except Exception as e:
        print(f"\n[LLM Error] 调用大模型失败 ({provider_type} | {model_name or settings.LLM_MODEL} @ {base_url}): {e}")
        raise RuntimeError(f"大模型 API 调用失败: {e}")
