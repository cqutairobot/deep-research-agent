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

def compress_webpage_facts(raw_text: str, focus_topic: str, max_facts: int = 3) -> List[str]:
    """
    Map-Reduce 范式：对单篇抓取的长网页内容执行目标导向的信息压缩，提取高密度事实。
    """
    if not raw_text or len(raw_text.strip()) < 30:
        return [f"关于【{focus_topic}】的相关动态信息已记录。"]

    # 截取前 4000 字符，避免一次性消耗过多 Token
    trimmed_text = raw_text[:4000]

    prompt = f"""
    【调研主题/关注点】：{focus_topic}
    
    【网页原文片段】：
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
    
    return [trimmed_text[:150].strip() + "..."]
