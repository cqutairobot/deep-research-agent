from typing import Dict, Any, List, Set
from app.agents.state import ResearchState, CitationSource, ChapterOutline
from app.tools.search_tools import search_web
from app.tools.scrape_tools import scrape_url
from app.agents.summarizer import compress_webpage_facts
from app.tools.memory_store import SessionMemoryStore

def research_worker_node(state: ResearchState) -> Dict[str, Any]:
    """
    Researcher 智能体节点 (Phase 5 混合 RAG 升级版):
    融合【本地私有知识切片检索】与【全网实时并发搜索】，并通过 Map-Reduce 事实压缩器提取核心高密度事实卡片
    """
    outline: List[ChapterOutline] = state.get("outline", [])
    existing_citations: List[CitationSource] = state.get("citations", [])
    local_docs: List[Dict[str, Any]] = state.get("local_documents", [])
    iter_count = state.get("iteration_count", 1)
    
    all_citations: List[CitationSource] = list(existing_citations)
    seen_urls: Set[str] = {c["url"] for c in all_citations if c.get("url")}
    
    updated_outline: List[ChapterOutline] = []
    logs: List[str] = []
    
    source_counter = len(all_citations) + 1
    new_facts_count = 0
    
    # 1. 本地私有文档混合 RAG 索引构建
    local_memory = SessionMemoryStore()
    if local_docs:
        logs.append(f"[Researcher] 检测到 {len(local_docs)} 份本地专有文档，建立混合 RAG 向量切片索引...")
        for doc in local_docs:
            fname = doc.get("file_name", "本地文档")
            for chunk_idx, chunk in enumerate(doc.get("chunks", [])):
                local_memory.add_fact(
                    fact_text=chunk,
                    source_id=0, # 动态分配
                    chapter_num=0,
                    metadata={"file_name": fname, "chunk_idx": chunk_idx}
                )

    logs.append(f"[Researcher] 启动第 {iter_count} 轮网络检索与混合知识提炼...")
    
    for chapter in outline:
        ch_num = chapter.get("chapter_num", 1)
        title = chapter.get("title", f"第 {ch_num} 章")
        focus = chapter.get("focus", "")
        queries = chapter.get("search_queries", [])
        chapter_facts: List[str] = list(chapter.get("extracted_facts", []))
        
        # 1.1 优先从本地私有文档库召回相关片段 (混合 RAG)
        if local_docs and iter_count == 1:
            matched_local_chunks = local_memory.search(query=f"{title} {focus}", top_k=2)
            for m in matched_local_chunks:
                fname = m.get("metadata", {}).get("file_name", "本地文件")
                chunk_text = m.get("text", "")
                
                # 记录本地引用
                local_url = f"local://{fname}"
                if local_url not in seen_urls:
                    seen_urls.add(local_url)
                    citation: CitationSource = {
                        "id": source_counter,
                        "url": local_url,
                        "title": f"【本地私有文件】{fname}",
                        "snippet": chunk_text[:200],
                        "score": 0.98,
                        "published_date": None
                    }
                    all_citations.append(citation)
                    source_id = source_counter
                    source_counter += 1
                else:
                    existing = next((c for c in all_citations if c["url"] == local_url), None)
                    source_id = existing["id"] if existing else 1
                
                fact_entry = f"{chunk_text[:180]}... [来源: 本地私有文档「{fname}」[{source_id}]]"
                if fact_entry not in chapter_facts:
                    chapter_facts.append(fact_entry)
                    new_facts_count += 1
                    logs.append(f"  📄 [本地知识融合]: 从「{fname}」中为第 {ch_num} 章提炼了专有依据")

        # 1.2 全网实时检索与抓取
        if queries:
            for q in queries:
                logs.append(f"  🔍 [第 {ch_num} 章检索]: {q}")
                search_results = search_web(q, max_results=3)
                
                for item in search_results:
                    url = item.get("url", "")
                    item_title = item.get("title", "未命名网页")
                    content = item.get("content", "")
                    snippet = item.get("snippet", content[:200])
                    
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        citation: CitationSource = {
                            "id": source_counter,
                            "url": url,
                            "title": item_title,
                            "snippet": snippet,
                            "score": item.get("score", 0.9),
                            "published_date": None
                        }
                        all_citations.append(citation)
                        source_id = source_counter
                        source_counter += 1
                    else:
                        existing = next((c for c in all_citations if c["url"] == url), None)
                        source_id = existing["id"] if existing else 1
                    
                    if len(content) > 300:
                        high_density_facts = compress_webpage_facts(content, focus_topic=f"{title} - {q}")
                    else:
                        high_density_facts = [snippet] if snippet else []
                        
                    for fact in high_density_facts:
                        fact_entry = f"{fact} [来源: {item_title} [{source_id}]]"
                        if fact_entry not in chapter_facts:
                            chapter_facts.append(fact_entry)
                            new_facts_count += 1
        
        updated_ch = dict(chapter)
        updated_ch["extracted_facts"] = chapter_facts
        updated_outline.append(updated_ch)
    
    logs.append(f"[Researcher] 第 {iter_count} 轮完成！累计收录 {len(all_citations)} 处来源，本轮新增提取 {new_facts_count} 条高密度事实。")
    
    return {
        "outline": updated_outline,
        "citations": all_citations,
        "current_step": "critic",
        "logs": logs
    }
