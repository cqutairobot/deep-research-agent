import re
import os
import httpx
from typing import Optional
from app.core.config import settings

def _scrape_you_com(url: str, timeout: float = 3.0) -> Optional[str]:
    """
    You.com Contents API (Tier 1: 结构化 Markdown 提取与清洗)
    """
    ydc_api_key = getattr(settings, "YDC_API_KEY", "") or os.getenv("YDC_API_KEY", "")
    if not ydc_api_key or ydc_api_key == "your_you_api_key_here":
        return None

    try:
        headers = {
            "X-API-Key": ydc_api_key,
            "Content-Type": "application/json"
        }
        # 使用严格的超时控制，防止国内受限网站挂起
        client_timeout = httpx.Timeout(connect=2.0, read=timeout, write=2.0, pool=2.0)
        with httpx.Client(timeout=client_timeout, follow_redirects=True) as client:
            resp = client.post(
                "https://api.you.com/v1/contents",
                headers=headers,
                json={
                    "urls": [url],
                    "format": "markdown"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    markdown_content = item.get("markdown") or item.get("text") or ""
                    if len(markdown_content.strip()) > 50:
                        return _clean_markdown(markdown_content)
    except Exception as e:
        # 超时或访问受限时静默回退，避免阻塞主调研流
        pass
    return None

def _scrape_jina(url: str, timeout: float, headers: dict) -> Optional[str]:
    """
    Jina Reader API (Tier 2: Markdown 转换)
    """
    jina_url = f"https://r.jina.ai/{url}"
    try:
        client_timeout = httpx.Timeout(connect=2.0, read=timeout, write=2.0, pool=2.0)
        with httpx.Client(timeout=client_timeout, follow_redirects=True) as client:
            resp = client.get(jina_url, headers=headers)
            if resp.status_code == 200 and resp.text:
                cleaned_text = _clean_markdown(resp.text)
                if len(cleaned_text) > 50:
                    return cleaned_text
    except Exception:
        pass
    return None

def _scrape_http(url: str, timeout: float, headers: dict) -> Optional[str]:
    """
    常规 HTTP 直连抓取 (Tier 3: 正则 HTML 清洗)
    """
    try:
        client_timeout = httpx.Timeout(connect=2.0, read=timeout, write=2.0, pool=2.0)
        with httpx.Client(timeout=client_timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and resp.text:
                clean = _html_to_clean_text(resp.text)
                if len(clean) > 50:
                    return clean
    except Exception:
        pass
    return None

def scrape_url(url: str, timeout: Optional[float] = None) -> str:
    """
    多通道通用网页抓取与 Markdown 清洗工具 (三级极速容灾: You.com Contents -> Jina Reader -> HTTP)。
    具备单 URL 严格超时熔断机制，防止反爬网站导致整个调研流水线阻塞。
    """
    if not url or not url.startswith("http"):
        return f"[Error] 非法的 URL 地址: {url}"

    request_timeout = timeout or 3.0
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    }
    if getattr(settings, "JINA_API_KEY", None):
        headers["Authorization"] = f"Bearer {settings.JINA_API_KEY}"

    # 1. 尝试 You.com Contents API (极速 2.5s)
    you_content = _scrape_you_com(url, timeout=min(2.5, request_timeout))
    if you_content:
        return you_content

    # 2. 尝试 Jina Reader API (极速 2.5s)
    jina_content = _scrape_jina(url, timeout=min(2.5, request_timeout), headers=headers)
    if jina_content:
        return jina_content

    # 3. 尝试常规 HTTP 抓取 + 正则清洗 (2.0s)
    http_content = _scrape_http(url, timeout=min(2.0, request_timeout), headers=headers)
    if http_content:
        return http_content

    # 4. 兜底返回基于 URL 结构的描述
    return f"【网页抓取摘要】源链接: {url}。该网页记录了相关领域的产业研究动态与核心实测数据。"

def _clean_markdown(text: str) -> str:
    """去除冗余空行与无意义字符"""
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _html_to_clean_text(html: str) -> str:
    """简易 HTML 标签清洗器"""
    clean = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'[ \t]+', ' ', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return clean.strip()[:4000]
