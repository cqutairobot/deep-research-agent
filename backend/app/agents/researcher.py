from typing import Dict, Any, List, Set, Optional, Callable
from app.agents.state import ResearchState, CitationSource, ChapterOutline
from app.tools.search_tools import search_web
from app.tools.scrape_tools import scrape_url
from app.agents.summarizer import compress_webpage_facts
from app.tools.memory_store import SessionMemoryStore
from app.tools.smart_reranker import chunk_webpage_for_rerank, rerank_chunks, compute_rrf_score

def research_worker_node(
    state: ResearchState,
    on_progress: Optional[Callable[[str, Any], None]] = None
) -> Dict[str, Any]:
    """
    Researcher 智能体节点 (V2.0 极速并发与分级阈值控制版):
    根据 research_depth (quick / standard / deep) 严格设置检索词数量、单次召回数与事实沉淀上限，
    杜绝无节制海量抓取，并在第一时间向前端流式更新。
    """
    outline: List[ChapterOutline] = state.get("outline", [])
    existing_citations: List[CitationSource] = state.get("citations", [])
    local_docs: List[Dict[str, Any]] = state.get("local_documents", [])
    iter_count = state.get("iteration_count", 1)
    depth = state.get("research_depth", "standard")
    
    # 严格根据调研深度设定抓取与事实收录上限
    if depth == "quick":
        max_queries_per_ch = 1
        max_results_per_q = 1
        max_facts_per_ch = 3
        max_total_citations = 10
    elif depth == "deep":
        max_queries_per_ch = 3
        max_results_per_q = 2
        max_facts_per_ch = 10
        max_total_citations = 35
    else:  # standard (中等/标准)
        max_queries_per_ch = 2
        max_results_per_q = 2
        max_facts_per_ch = 6
        max_total_citations = 20
    
    all_citations: List[CitationSource] = list(existing_citations)
    seen_urls: Set[str] = {c["url"] for c in all_citations if c.get("url")}
    
    updated_outline: List[ChapterOutline] = []
    logs: List[str] = []
    
    source_counter = len(all_citations) + 1
    new_facts_count = 0
    
    # 1. 本地私有文档混合 RAG 索引构建与权威信源注册
    local_memory = SessionMemoryStore()
    if local_docs:
        init_msg = f"[Researcher] 检测到 {len(local_docs)} 份本地专有文档，建立混合 RAG 向量切片索引与可信信源底座..."
        logs.append(init_msg)
        if on_progress:
            on_progress("thought", {"step": "research", "message": init_msg})
            
        for doc in local_docs:
            fname = doc.get("file_name", "本地文档")
            chunks = doc.get("chunks", [])
            for chunk_idx, chunk in enumerate(chunks):
                local_memory.add_fact(
                    fact_text=chunk,
                    source_id=0,
                    chapter_num=0,
                    metadata={"file_name": fname, "chunk_idx": chunk_idx}
                )
            
            # 预注册本地文档为高权重优先信源 (确保所有上传的专有文献均能收录在全局信源库)
            local_url = f"local://{fname}"
            if local_url not in seen_urls:
                seen_urls.add(local_url)
                first_snippet = chunks[0][:200] if chunks else "用户上传的本地专有参考文档。"
                citation: CitationSource = {
                    "id": source_counter,
                    "url": local_url,
                    "title": f"【本地私有文件】{fname}",
                    "snippet": first_snippet,
                    "score": 0.99,
                    "published_date": None
                }
                all_citations.append(citation)
                source_counter += 1

    start_log = f"[Researcher] 启动第 {iter_count} 轮多源检索与混合知识提炼 (模式: {depth}, 来源上限: {max_total_citations})..."
    logs.append(start_log)
    if on_progress:
        on_progress("thought", {"step": "research", "message": start_log})
    
    for chapter in outline:
        ch_num = chapter.get("chapter_num", 1)
        title = chapter.get("title", f"第 {ch_num} 章")
        focus = chapter.get("focus", "")
        queries = chapter.get("search_queries", [])
        chapter_facts: List[str] = list(chapter.get("extracted_facts", []))

        # 1.1 优先从本地私有文档库召回相关片段 (混合 RAG + RRF 加权，支持章节级专属绑定)
        if local_docs and iter_count == 1:
            bound_docs = chapter.get("bound_documents") or []
            search_k = 4 if bound_docs else 2
            matched_local_chunks = local_memory.search(query=f"{title} {focus}", top_k=search_k)
            
            # 若本章绑定了专属文档，优先提升专属文档切片的排序
            if bound_docs:
                matched_local_chunks.sort(
                    key=lambda m: (0 if m.get("metadata", {}).get("file_name") in bound_docs else 1)
                )
                matched_local_chunks = matched_local_chunks[:2]

            for rank_idx, m in enumerate(matched_local_chunks, start=1):
                fname = m.get("metadata", {}).get("file_name", "本地文件")
                chunk_text = m.get("text", "")
                is_bound = fname in bound_docs
                weight_val = 3.0 if is_bound else 1.5
                
                rrf_val = compute_rrf_score({"local": rank_idx}, weights={"local": weight_val})
                local_url = f"local://{fname}"
                if local_url not in seen_urls:
                    seen_urls.add(local_url)
                    citation: CitationSource = {
                        "id": source_counter,
                        "url": local_url,
                        "title": f"【本地私有文件{'·章节专属' if is_bound else ''}】{fname}",
                        "snippet": chunk_text[:200],
                        "score": round(min(0.99, 0.90 + rrf_val * 5), 2),
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
                    local_log = f"  📄 [本地知识融合]: 从「{fname}」{' (专属绑定)' if is_bound else ''}中为第 {ch_num} 章提炼了专有依据"
                    logs.append(local_log)
                    if on_progress:
                        on_progress("thought", {"step": "research", "message": local_log})

        # 1.2 全网实时检索与长文 Rerank 抓取 (受上限严格保护)
        if queries and len(chapter_facts) < max_facts_per_ch and len(all_citations) < max_total_citations:
            active_queries = queries[:max_queries_per_ch]
            for q in active_queries:
                if len(chapter_facts) >= max_facts_per_ch or len(all_citations) >= max_total_citations:
                    break
                
                q_log = f"  🔍 [第 {ch_num} 章检索]: {q}"
                logs.append(q_log)
                if on_progress:
                    on_progress("search", {"query": q, "chapter": ch_num, "message": q_log, "iteration": iter_count})
                
                search_results = search_web(q, max_results=max_results_per_q)
                
                for item in search_results:
                    if len(chapter_facts) >= max_facts_per_ch or len(all_citations) >= max_total_citations:
                        break
                    
                    url = item.get("url", "")
                    item_title = item.get("title", "未命名网页")
                    raw_search_content = item.get("content", "")
                    snippet = item.get("snippet", raw_search_content[:200])
                    
                    if not url:
                        continue

                    # 1.2.1 极速抓取真实网页全文 (带熔断控制)
                    full_page_content = ""
                    if url.startswith("http"):
                        try:
                            full_page_content = scrape_url(url, timeout=2.5)
                        except Exception:
                            pass
                    
                    # 1.2.2 长文语义分块与 Rerank 核心段落召回 (Smart Reranker)
                    if full_page_content and len(full_page_content) > 1200:
                        page_chunks = chunk_webpage_for_rerank(full_page_content, chunk_size=800)
                        top_paragraphs = rerank_chunks(page_chunks, query=q, focus=f"{title} {focus}", top_k=2)
                        text_for_summary = "\n\n---\n\n".join(top_paragraphs) if top_paragraphs else full_page_content[:3000]
                    elif full_page_content and len(full_page_content) > 100:
                        text_for_summary = full_page_content
                    else:
                        text_for_summary = raw_search_content

                    actual_snippet = snippet if snippet else text_for_summary[:200]

                    if url not in seen_urls:
                        seen_urls.add(url)
                        citation: CitationSource = {
                            "id": source_counter,
                            "url": url,
                            "title": item_title,
                            "snippet": actual_snippet,
                            "score": item.get("score", 0.9),
                            "published_date": None
                        }
                        all_citations.append(citation)
                        source_id = source_counter
                        source_counter += 1
                    else:
                        existing = next((c for c in all_citations if c["url"] == url), None)
                        source_id = existing["id"] if existing else 1
                    
                    if len(text_for_summary) > 200:
                        high_density_facts = compress_webpage_facts(text_for_summary, focus_topic=f"{title} - {q}", max_facts=2)
                    else:
                        high_density_facts = [actual_snippet] if actual_snippet and len(actual_snippet) > 20 else []
                        
                    for fact in high_density_facts:
                        fact_entry = f"{fact} [来源: {item_title} [{source_id}]]"
                        if fact_entry not in chapter_facts:
                            chapter_facts.append(fact_entry)
                            new_facts_count += 1
                            if len(chapter_facts) >= max_facts_per_ch:
                                break
                
                # 实时同步最新事实至前端
                if on_progress:
                    temp_outline = list(updated_outline)
                    current_ch_copy = dict(chapter)
                    current_ch_copy["extracted_facts"] = chapter_facts
                    temp_outline.append(current_ch_copy)
                    for rest_ch in outline[len(temp_outline):]:
                        temp_outline.append(dict(rest_ch))
                    on_progress("facts_extracted", {
                        "citations": all_citations,
                        "outline": temp_outline
                    })
        
        updated_ch = dict(chapter)
        updated_ch["extracted_facts"] = chapter_facts
        updated_outline.append(updated_ch)
    
    end_msg = f"[Researcher] 第 {iter_count} 轮完成！收录 {len(all_citations)} 处高权重信源，提取 {new_facts_count} 条核心量化事实。"
    logs.append(end_msg)
    if on_progress:
        on_progress("thought", {"step": "research", "message": end_msg})
        on_progress("facts_extracted", {
            "citations": all_citations,
            "outline": updated_outline
        })
    
    return {
        "outline": updated_outline,
        "citations": all_citations,
        "current_step": "critic",
        "logs": logs
    }
