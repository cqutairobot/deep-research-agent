import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

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
        
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
        self.JINA_API_KEY = os.getenv("JINA_API_KEY", None)
        self.MAX_SEARCH_RESULTS_PER_QUERY = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
        self.SCRAPER_TIMEOUT_SECONDS = float(os.getenv("SCRAPER_TIMEOUT", "15.0"))

settings = Settings()

def call_llm(
    prompt: str,
    system_prompt: str = "You are an expert autonomous AI research assistant.",
    temperature: float = 0.3,
    max_tokens: int = 8192
) -> str:
    """
    统一调用真实大模型接口 (支持 deepseek-v4-flash-vision-exp / deepseek-chat 等原生及兼容多模态模型)
    """
    settings.reload()
    api_key = settings.LLM_API_KEY
    
    if not api_key:
        raise ValueError("【缺少 LLM API Key】请在 backend/.env 文件中配置有效的 LLM_API_KEY。")

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=settings.LLM_BASE_URL
        )
        
        model_name = settings.LLM_MODEL

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        content = response.choices[0].message.content or ""
        return content.strip()

    except Exception as e:
        print(f"\n[LLM Error] 调用大模型失败 ({settings.LLM_MODEL} @ {settings.LLM_BASE_URL}): {e}")
        raise RuntimeError(f"大模型 API 调用失败: {e}")
