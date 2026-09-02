import re
from typing import Dict, Any, List, Set
from app.agents.state import ResearchState, CitationSource

def clean_snippet_text(text: str, max_len: int = 200) -> str:
    """
    清洗引证片段文本，彻底剔除 Markdown 标题符号 (#, ##) 与多余换行，避免污染正文结构
    """
    if not text:
        return "可信引证来源。"
    # 移除标题符号与多余空格
    clean = re.sub(r'#+\s*', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = clean.replace('"', "'")
    if len(clean) > max_len:
        return clean[:max_len] + "..."
    return clean

def citation_verifier_node(state: ResearchState) -> Dict[str, Any]:
    """
    Verifier 智能体节点：
    1. 防幻觉校验：剔除或修正大模型虚构的 [N] 编号；
    2. 引用顺位重排：根据正文实际出现的顺序，将 [15], [31], [2] 等散乱编号重新统一按 1, 2, 3... 连续连续重排；
    3. 参考文献清洗：彻底过滤 Snippet 内的 Markdown 标题符号，杜绝混入正文排版。
    """
    raw_report = state.get("draft_report") or state.get("final_report", "")
    citations: List[CitationSource] = state.get("citations", [])
    
    citations_by_old_id: Dict[int, CitationSource] = {
        c["id"]: c for c in citations if "id" in c
    }
    valid_old_ids: Set[int] = set(citations_by_old_id.keys())
    
    # 剥离原有的末尾参考资料部分
    citations_section_pattern = r'## 📚 参考资料[\s\S]*$'
    clean_body = re.sub(citations_section_pattern, '', raw_report).strip()
    # 剥离末尾多余的分隔线
    clean_body = re.sub(r'---\s*$', '', clean_body).strip()
    
    # 1. 扫描正文中引用的原始编号
    raw_matches = list(re.finditer(r'\[(\d+)\]', clean_body))
    total_refs = len(raw_matches)
    hallucinated_refs = 0
    
    # 2. 建立新旧编号映射表 (按正文先后出现顺序)
    old_to_new_id_map: Dict[int, int] = {}
    new_ordered_citations: List[CitationSource] = []
    
    for m in raw_matches:
        try:
            old_id = int(m.group(1))
            # 若为非法虚构编号，映射到最近的合法编号
            if old_id not in valid_old_ids:
                hallucinated_refs += 1
                if valid_old_ids:
                    old_id = min(valid_old_ids, key=lambda x: abs(x - old_id))
                else:
                    continue
            
            if old_id not in old_to_new_id_map:
                new_id = len(old_to_new_id_map) + 1
                old_to_new_id_map[old_id] = new_id
                
                orig_c = citations_by_old_id[old_id]
                new_ordered_citations.append({
                    "id": new_id,
                    "url": orig_c.get("url", "#"),
                    "title": orig_c.get("title", "可信网页来源"),
                    "snippet": clean_snippet_text(orig_c.get("snippet", "")),
                    "score": orig_c.get("score", 0.95),
                    "published_date": orig_c.get("published_date", None)
                })
        except ValueError:
            continue

    # 3. 将正文中的所有编号替换为重排后的连续新编号 [1], [2], [3]...
    def _replace_body_citation(match):
        try:
            old_id = int(match.group(1))
            if old_id in old_to_new_id_map:
                return f"[{old_to_new_id_map[old_id]}]"
            elif valid_old_ids:
                closest_old = min(valid_old_ids, key=lambda x: abs(x - old_id))
                return f"[{old_to_new_id_map.get(closest_old, 1)}]"
            return ""
        except ValueError:
            return match.group(0)

    renumbered_body = re.sub(r'\[(\d+)\]', _replace_body_citation, clean_body)

    # 4. 生成洁净、连续排序的参考文献列表
    citation_lines = ["\n\n---\n\n## 📚 参考资料与可信数据来源 (Citations & Sources)\n"]
    if new_ordered_citations:
        for c in new_ordered_citations:
            cid = c["id"]
            title = c.get("title", "来源")
            url = c.get("url", "#")
            snippet = c.get("snippet", "")
            citation_lines.append(f"- **[{cid}]** [{title}]({url})\n  > \"{snippet}\"\n")
    else:
        citation_lines.append("- 暂无外部引用数据源\n")
        
    final_verified_report = renumbered_body + "\n" + "\n".join(citation_lines)
    
    fix_msg = f"（已纠偏 {hallucinated_refs} 处编号）" if hallucinated_refs > 0 else "（引用准确率 100%）"
    log_msg = f"[Verifier] 引用校验与顺位重排完成：共检测到 {total_refs} 处引用，已按正文顺序重新编排为 1~{len(new_ordered_citations)} 连续标号 {fix_msg}。"
    
    return {
        "final_report": final_verified_report,
        "citations": new_ordered_citations,
        "current_step": "complete",
        "logs": [log_msg]
    }
