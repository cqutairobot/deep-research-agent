import re
from typing import List
from app.core.config import call_llm

SUMMARIZER_PROMPT = """你是一位专业的事实抽取与信息压缩专家。
你的任务是从给定的网页长文中，提炼出与【调研主题】高度相关的 2~4 条高密度核心事实与数据。

要求：
1. 提取的信息必须精准保留关键数值、年份、公司名、物理/技术参数或政策结论。
2. 剔除广告、导航条、免责声明等噪音。
3. 每条事实用一行精炼的陈述表达（不超过 80 字），格式为单行文本。
4. 严格输出 2~4 条纯文本，每条以 "- " 开头，不要输出任何其它前后缀。
"""

from app.tools.smart_reranker import chunk_webpage_for_rerank, rerank_chunks

def compress_webpage_facts(raw_text: str, focus_topic: str, max_facts: int = 3) -> List[str]:
    """
    Map-Reduce 范式：对单篇抓取的长网页内容执行目标导向的信息压缩，提取高密度事实。
    结合 Smart Chunking + Rerank 精准召回最相关的 Top 3 核心段落，彻底消除首部机械截断 (Phase 1 升级)。
    失败或内容过短时返回空列表，禁止虚构合成事实 (Bug 6)。
    """
    if not raw_text or len(raw_text.strip()) < 30:
        return []

    # 若文本较长，通过智能段落重排序捞取最相关的 Top 3 核心段落
    if len(raw_text) > 2500:
        chunks = chunk_webpage_for_rerank(raw_text, chunk_size=800)
        top_chunks = rerank_chunks(chunks, query=focus_topic, focus=focus_topic, top_k=3)
        trimmed_text = "\n\n---\n\n".join(top_chunks) if top_chunks else raw_text[:4000]
    else:
        trimmed_text = raw_text[:4000]

    prompt = f"""
    【调研主题/关注点】：{focus_topic}
    
    【网页原文精选片段 (Rerank 召回)】：
    {trimmed_text}
    
    请从中抽取核心事实：
    """
    
    try:
        response = call_llm(prompt, system_prompt=SUMMARIZER_PROMPT, temperature=0.1, max_tokens=600)
        lines = [line.strip().lstrip("-*•0123456789. ") for line in response.split("\n") if line.strip()]
        valid_facts = [l for l in lines if len(l) > 10]
        if valid_facts:
            return valid_facts[:max_facts]
    except Exception as e:
        pass

    # 简易正则备选抽取
    sentences = re.split(r'[。！？\n]', trimmed_text)
    meaningful = [s.strip() for s in sentences if len(s.strip()) > 20 and any(k in s for k in focus_topic.split()[:2])]
    if meaningful:
        return meaningful[:max_facts]
    
    return []
