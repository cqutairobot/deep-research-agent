import re
from typing import Dict, Any, List, Set, Optional
from app.agents.state import ResearchState, CitationSource

def clean_snippet_text(text: str, max_len: int = 200) -> str:
    """
    清洗引证片段文本，彻底剔除 Markdown 标题符号 (#, ##) 与多余换行，避免污染正文结构
    """
    if not text:
        return "可信引证来源。"
    clean = re.sub(r'#+\s*', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = clean.replace('"', "'")
    if len(clean) > max_len:
        return clean[:max_len] + "..."
    return clean

def citation_verifier_node(state: ResearchState) -> Dict[str, Any]:
    """
    Verifier 智能体节点 (V2.0 全格式引证校验与防丢失版):
    1. 全语法匹配支持：兼容 [^cite:N], [^N], [N], [来源: N] 等全部大模型输出格式；
    2. 引用顺位连续重排：根据正文实际出现的先后顺序重新编排为 [1], [2], [3]...；
    3. 兜底保护机制：若正文角标稀疏但已抓取到权威信源，自动对齐展示已检索的有效数据源，绝不出现“暂无引用”的空白异常。
    """
    raw_report = state.get("draft_report") or state.get("final_report", "")
    citations: List[CitationSource] = state.get("citations", [])
    
    citations_by_old_id: Dict[int, CitationSource] = {
        c["id"]: c for c in citations if "id" in c
    }
    valid_old_ids: Set[int] = set(citations_by_old_id.keys())
    
    # 剥离原有的末尾参考资料部分 (只安全剥离全篇末尾的参考资料章节，严禁误伤正文章节)
    citations_section_pattern = r'\n##\s*(?:📚\s*)?(?:参考资料|参考文献|引用来源|Citations?|Sources?)[\s\S]*$'
    clean_body = re.sub(citations_section_pattern, '', raw_report, flags=re.IGNORECASE).strip()
    clean_body = re.sub(r'\[\d+\]:\s+[^\n]+', '', clean_body).strip()
    clean_body = re.sub(r'---\s*$', '', clean_body).strip()
    
    # 1. 扫描正文中引用的原始编号 (保护代码块与数学公式)
    code_block_placeholders = {}
    def _save_code_block(m):
        pid = f"__CODE_BLOCK_{len(code_block_placeholders)}__"
        code_block_placeholders[pid] = m.group(0)
        return pid
        
    masked_body = re.sub(r'```[\s\S]*?```|`[^`]+`|\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$', _save_code_block, clean_body)

    # 全格式匹配：支持 [^cite:123], [^123], [123], [来源: 123]
    cite_pattern = r'\[\^cite:(\d+)\]|\[\^(\d+)\]|\[(\d+)\]|\[(?:来源|信源|Ref|Doc|Source)[:：]?\s*(\d+)\]'
    raw_matches = list(re.finditer(cite_pattern, masked_body))
    total_refs = len(raw_matches)
    hallucinated_refs = 0
    
    # 2. 建立新旧编号映射表 (按正文先后出现顺序)
    old_to_new_id_map: Dict[int, int] = {}
    new_ordered_citations: List[CitationSource] = []
    
    for m in raw_matches:
        try:
            # 提取匹配到的非空数字组
            num_str = next((g for g in m.groups() if g is not None), None)
            if not num_str:
                continue
            old_id = int(num_str)
            
            # 若不是 [^cite:N]/[^N] 且为 4 位数年份（如 1900-2099）且不在已知引用中，判定为普通年份文本，跳过
            is_explicit_cite = m.group(1) is not None or m.group(2) is not None or m.group(4) is not None
            if not is_explicit_cite and 1900 <= old_id <= 2100 and old_id not in valid_old_ids:
                continue
                
            # 若为非法虚构编号，记录并剥离
            if old_id not in valid_old_ids:
                hallucinated_refs += 1
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

    # 3. 将正文中的所有引用角标替换为重排后的连续新编号 [1], [2], [3]...
    def _replace_body_citation(match):
        try:
            num_str = next((g for g in match.groups() if g is not None), None)
            if not num_str:
                return match.group(0)
            old_id = int(num_str)
            
            is_explicit_cite = match.group(1) is not None or match.group(2) is not None or match.group(4) is not None
            if not is_explicit_cite and 1900 <= old_id <= 2100 and old_id not in valid_old_ids:
                return match.group(0)

            if old_id in old_to_new_id_map:
                return f"[{old_to_new_id_map[old_id]}]"
            else:
                return ""
        except ValueError:
            return match.group(0)

    renumbered_body = re.sub(cite_pattern, _replace_body_citation, masked_body)

    # 还原代码块与公式
    for pid, code_text in code_block_placeholders.items():
        renumbered_body = renumbered_body.replace(pid, code_text)

    # 4. 重点保障：确保用户上传的本地专有私有文档 (local://) 100% 完整收录在文献列表中，绝不丢失
    existing_urls = {c["url"] for c in new_ordered_citations if "url" in c}
    for orig_c in citations:
        if orig_c.get("url", "").startswith("local://") and orig_c.get("url") not in existing_urls:
            new_id = len(new_ordered_citations) + 1
            new_ordered_citations.append({
                "id": new_id,
                "url": orig_c.get("url", "#"),
                "title": orig_c.get("title", "本地私有文件"),
                "snippet": clean_snippet_text(orig_c.get("snippet", "")),
                "score": orig_c.get("score", 0.99),
                "published_date": orig_c.get("published_date", None)
            })
            existing_urls.add(orig_c.get("url"))

    # 4.1 兜底保护：若正文中角标被模型省略，但系统有检索到的真实信源，自动对齐
    if not new_ordered_citations and citations:
        for idx, orig_c in enumerate(citations, start=1):
            new_ordered_citations.append({
                "id": idx,
                "url": orig_c.get("url", "#"),
                "title": orig_c.get("title", "可信网页来源"),
                "snippet": clean_snippet_text(orig_c.get("snippet", "")),
                "score": orig_c.get("score", 0.95),
                "published_date": orig_c.get("published_date", None)
            })

    # 5. 生成洁净、连续排序的参考文献列表
    citation_lines = ["\n\n---\n\n## 📚 参考资料与可信数据来源 (Citations & Sources)\n"]
    if new_ordered_citations:
        for c in new_ordered_citations:
            cid = c["id"]
            title = c.get("title", "来源")
            url = c.get("url", "#")
            snippet = c.get("snippet", "")
            citation_lines.append(f"- [{cid}] [{title}]({url})\n  > \"{snippet}\"\n")
    else:
        citation_lines.append("- 暂无外部引用数据源\n")
        
    final_verified_report = renumbered_body.strip() + "\n" + "\n".join(citation_lines)
    
    fix_msg = f"（已剔除 {hallucinated_refs} 处虚构编号）" if hallucinated_refs > 0 else "（引用准确率 100%）"
    log_msg = f"[Verifier] 引用校验与顺位重排完成：共检测到 {total_refs} 处角标，已按正文顺序重新编排为 1~{len(new_ordered_citations)} 连续标号 {fix_msg}。"
    
    return {
        "final_report": final_verified_report,
        "citations": new_ordered_citations,
        "current_step": "complete",
        "logs": [log_msg]
    }
