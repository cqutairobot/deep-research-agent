"""
专有名词划词即刻释义服务 (Context-Aware Glossary Explainer)
100% 依赖大模型根据研报真实上下文进行动态通俗解析，杜绝硬编码静态词表。
"""

import re
from typing import Optional, Dict, Any
from app.core.config import call_llm, CustomLLMConfig

# 会话内短期缓存（避免用户在同一页面中对同一个词频繁重复发起请求）
_GLOSSARY_CACHE: Dict[str, str] = {}


def explain_term_in_context(
    term: str,
    context: Optional[str] = None,
    custom_llm_config: Optional[CustomLLMConfig] = None
) -> Dict[str, Any]:
    """
    划词即刻释义核心入口：
    由大模型严格结合用户研报当前的上下文段落进行动态解释。
    不预置任何偏向特定领域的死板词典，保证任何行业课题均真实自适应生成。
    """
    clean_term = term.strip()
    if not clean_term:
        return {"term": "", "explanation": "请选择有效词汇", "status": "error"}

    cache_key = f"{clean_term.lower()}::{hash(context[:80]) if context else ''}"
    if cache_key in _GLOSSARY_CACHE:
        return {
            "term": clean_term,
            "explanation": _GLOSSARY_CACHE[cache_key],
            "status": "success",
            "cached": True
        }

    clean_context = (context or "").strip()[:600]
    prompt = (
        f"请结合以下研报上下文，用 100 字以内通俗易懂的大白话，解释专业术语「{clean_term}」的核心含义与在本文中的实际作用：\n\n"
        f"【研报语境】：{clean_context if clean_context else '通用科技与商业研报'}\n\n"
        f"请直接给出定义与业务影响，无需寒暄客套。"
    )
    
    system_prompt = (
        "你是一位精通跨领域科学技术与商业分析的资深学者。"
        "请根据用户提供的研报语境，用不超过 100 字的精炼通俗语言解释选中的专有名词，"
        "直击其在当前研报讨论中的真实含义与作用，严禁废话，严禁编造不相关领域的内容。"
    )

    try:
        explanation = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            custom_llm_config=custom_llm_config
        )
        explanation = re.sub(r'^(好的|当然|关于|简而言之[，：]|释义[：:])\s*', '', explanation).strip()
        
        # 截断控制在 130 字以内
        if len(explanation) > 130:
            sents = [s for s in explanation.split("。") if s.strip()]
            explanation = "。".join(sents[:2]) + "。"
            if len(explanation) > 130:
                explanation = explanation[:125] + "..."

        _GLOSSARY_CACHE[cache_key] = explanation
        return {
            "term": clean_term,
            "explanation": explanation,
            "status": "success",
            "cached": False
        }
    except Exception as e:
        print(f"[GlossaryService] 动态释义调用失败: {e}")
        return {
            "term": clean_term,
            "explanation": f"暂无法连接大模型解析「{clean_term}」，请检查模型网关配置或在右侧 Q&A 中进一步追问探讨。",
            "status": "failed",
            "cached": False,
            "error": str(e)
        }
