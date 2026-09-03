import os
import httpx
from typing import List, Dict, Any, Optional
from ddgs import DDGS
from app.core.config import settings

def _search_you_com(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    You.com Web Search API (Tier 1 首选商业级搜索)
    """
    ydc_api_key = getattr(settings, "YDC_API_KEY", "") or os.getenv("YDC_API_KEY", "")
    if not ydc_api_key or ydc_api_key == "your_you_api_key_here":
        return []

    try:
        headers = {
            "X-API-Key": ydc_api_key,
            "Content-Type": "application/json"
        }
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(
                "https://api.you.com/v1/search",
                headers=headers,
                json={
                    "query": query,
                    "num_web_results": max_results
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                web_hits = data.get("results", {}).get("web", [])
                results = []
                for item in web_hits:
                    url = item.get("url", "")
                    if not url:
                        continue
                    snippets = item.get("snippets", [])
                    desc = item.get("description", "")
                    content = " ".join(snippets) if snippets else desc
                    results.append({
                        "title": item.get("title", "未命名网页"),
                        "url": url,
                        "content": content,
                        "snippet": content[:300] if content else desc[:300],
                        "score": 0.98
                    })
                if results:
                    return results
    except Exception as e:
        print(f"[Search Warning] You.com search failed: {e}. Falling back...")
    return []

def _search_tavily(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Tavily Search API (Tier 2 次选商业搜索)
    """
    tavily_api_key = settings.TAVILY_API_KEY or os.getenv("TAVILY_API_KEY", "")
    if not tavily_api_key or tavily_api_key == "your_tavily_api_key_here":
        return []

    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", "未命名网页"),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "snippet": item.get("content", "")[:300],
                        "score": item.get("score", 0.95)
                    })
                if results:
                    return results
    except Exception as e:
        print(f"[Search Warning] Tavily search failed: {e}. Falling back...")
    return []

def _search_ddgs(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    DuckDuckGo Search (Tier 3 免费兜底)
    """
    try:
        ddgs = DDGS()
        raw_results = list(ddgs.text(query, max_results=max_results))
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", "未命名网页"),
                "url": item.get("href", ""),
                "content": item.get("body", ""),
                "snippet": item.get("body", "")[:300],
                "score": 0.9
            })
        if results:
            return results
    except Exception as e:
        print(f"[Search Error] DDGS live search failed: {e}")
    return []

def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    真实全网多源实时搜索引擎 (三级容灾矩阵: You.com -> Tavily -> DDGS)。
    严格遵循零伪造原则，失败或无结果时返回空列表。
    """
    # 1. 首选 You.com Web Search API
    results = _search_you_com(query, max_results=max_results)
    if results:
        return results

    # 2. 次选 Tavily Search API
    results = _search_tavily(query, max_results=max_results)
    if results:
        return results

    # 3. 兜底 DDGS 实时检索
    results = _search_ddgs(query, max_results=max_results)
    if results:
        return results

    # 4. 搜索失败或无结果时返回空列表 (Bug 5: 严禁伪造虚构检索结果与链接)
    print(f"[Search Info] 检索词 '{query}' 未返回有效网络结果。")
    return []
