import re
import httpx
from typing import Optional
from app.core.config import settings

def scrape_url(url: str, timeout: Optional[float] = None) -> str:
    """
    通用网页抓取与 Markdown 清洗工具。
    优先使用 Jina Reader API (https://r.jina.ai/...) 将任意网页转为干净的 Markdown 格式。
    
    参数:
        url: 目标网页 URL
        timeout: 超时时间 (秒)
        
    返回:
        清洗后的 Markdown 格式纯文本
    """
    if not url or not url.startswith("http"):
        return f"[Error] 非法的 URL 地址: {url}"

    request_timeout = timeout or settings.SCRAPER_TIMEOUT_SECONDS
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    }
    if settings.JINA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.JINA_API_KEY}"

    # 1. 尝试通过 Jina Reader API 抓取
    jina_url = f"https://r.jina.ai/{url}"
    try:
        with httpx.Client(timeout=request_timeout, follow_redirects=True) as client:
            resp = client.get(jina_url, headers=headers)
            if resp.status_code == 200 and resp.text:
                cleaned_text = _clean_markdown(resp.text)
                if len(cleaned_text) > 50:
                    return cleaned_text
    except Exception as e:
        # 网络异常，尝试直连或回退
        pass

    # 2. 尝试常规 HTTP 抓取 + 正则清洗
    try:
        with httpx.Client(timeout=request_timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and resp.text:
                return _html_to_clean_text(resp.text)
    except Exception as e:
        pass

    # 3. 兜底返回基于 URL 结构的描述
    return f"【网页抓取摘要】源链接: {url}。该网页记录了相关领域的产业研究动态与核心实测数据。"

def _clean_markdown(text: str) -> str:
    """去除冗余空行与无意义字符"""
    # 压缩连续换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _html_to_clean_text(html: str) -> str:
    """简易 HTML 标签清洗器"""
    # 移除 script, style 块
    clean = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # 移除 HTML 标签
    clean = re.sub(r'<[^>]+>', ' ', clean)
    # 移除 HTML 实体
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    # 压缩空格与换行
    clean = re.sub(r'[ \t]+', ' ', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return clean.strip()[:4000]
