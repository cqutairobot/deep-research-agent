"""
Token 算力追踪与法币成本计费服务 (Cost Estimator Service)
针对业界主流大语言模型提供精准的输入/输出 Token 估算与法币（CNY / USD）成本测算模型。
"""

from typing import Dict, Any, Optional
import re

USD_TO_CNY_RATE = 7.25

# 主流模型单价表 (每百万 Token 单价: Million Tokens / MTokens)
MODEL_PRICE_MAP = {
    # DeepSeek 官方定价 (人民币)
    "deepseek-chat": {"input_cny_per_m": 1.0, "output_cny_per_m": 2.0},
    "deepseek-v3": {"input_cny_per_m": 1.0, "output_cny_per_m": 2.0},
    "deepseek-reasoner": {"input_cny_per_m": 4.0, "output_cny_per_m": 16.0},
    "deepseek-r1": {"input_cny_per_m": 4.0, "output_cny_per_m": 16.0},
    "deepseek-v4-flash-vision-exp": {"input_cny_per_m": 1.0, "output_cny_per_m": 2.0},
    
    # OpenAI 官方定价 (换算为人民币)
    "gpt-4o-mini": {"input_cny_per_m": 0.15 * USD_TO_CNY_RATE, "output_cny_per_m": 0.60 * USD_TO_CNY_RATE},
    "gpt-4o": {"input_cny_per_m": 2.50 * USD_TO_CNY_RATE, "output_cny_per_m": 10.00 * USD_TO_CNY_RATE},
    "gpt-4-turbo": {"input_cny_per_m": 10.00 * USD_TO_CNY_RATE, "output_cny_per_m": 30.00 * USD_TO_CNY_RATE},
    
    # Anthropic Claude 官方定价 (换算为人民币)
    "claude-3-5-sonnet-20241022": {"input_cny_per_m": 3.00 * USD_TO_CNY_RATE, "output_cny_per_m": 15.00 * USD_TO_CNY_RATE},
    "claude-3-5-haiku-20241022": {"input_cny_per_m": 0.80 * USD_TO_CNY_RATE, "output_cny_per_m": 4.00 * USD_TO_CNY_RATE},
    
    # 通用/开源默认
    "default": {"input_cny_per_m": 1.5, "output_cny_per_m": 3.0}
}


def estimate_tokens_from_text(text: str) -> int:
    """
    当上游未返回精准 token usage 时，基于语言学分词密度估算文本 Token 数量：
    中文通常 1.4~1.6 字符 / Token；英文通常 0.75 词 / Token。
    """
    if not text:
        return 0
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计其他英文字词
    other_text = re.sub(r'[\u4e00-\u9fff]', ' ', text)
    words = len(other_text.split())
    
    estimated = int(chinese_chars / 1.5 + words * 1.3)
    return max(1, estimated)


def calculate_estimated_cost(metrics: Dict[str, Any], model_name: Optional[str] = None) -> Dict[str, float]:
    """
    根据输入的输入/输出 Token 数量和模型名称，精确计算预估法币花费。
    """
    model = (model_name or metrics.get("model") or "deepseek-chat").lower().strip()
    
    pricing = MODEL_PRICE_MAP.get("default")
    for k, v in MODEL_PRICE_MAP.items():
        if k in model:
            pricing = v
            break

    in_tokens = float(metrics.get("input_tokens") or metrics.get("prompt_tokens") or 0)
    out_tokens = float(metrics.get("output_tokens") or metrics.get("completion_tokens") or 0)

    cost_cny_in = (in_tokens / 1_000_000.0) * pricing["input_cny_per_m"]
    cost_cny_out = (out_tokens / 1_000_000.0) * pricing["output_cny_per_m"]
    total_cny = round(cost_cny_in + cost_cny_out, 5)
    total_usd = round(total_cny / USD_TO_CNY_RATE, 5)

    return {
        "total_cny": total_cny,
        "total_usd": total_usd,
        "input_tokens": int(in_tokens),
        "output_tokens": int(out_tokens),
        "total_tokens": int(in_tokens + out_tokens),
        "model": model
    }


def create_initial_metrics(model_name: str = "deepseek-chat") -> Dict[str, Any]:
    """初始化任务算力统计数据结构"""
    return {
        "model": model_name,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "total_cost_cny": 0.0,
        "total_cost_usd": 0.0,
        "search_count": 0,
        "node_breakdown": {
            "planner": {"input": 0, "output": 0, "tokens": 0},
            "researcher": {"input": 0, "output": 0, "tokens": 0},
            "writer": {"input": 0, "output": 0, "tokens": 0},
            "critic": {"input": 0, "output": 0, "tokens": 0},
            "verifier": {"input": 0, "output": 0, "tokens": 0}
        }
    }
