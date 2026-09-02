from typing import Dict, Any, List
from app.agents.state import ResearchState, CitationSource, ChapterOutline
from app.core.config import call_llm

WRITER_SYSTEM_PROMPT = """你是一位国际顶尖智库的资深首席研究员。
你的任务是根据收集到的事实清单和章节大纲，撰写一份结构严谨、逻辑缜密、带有详实数据与对比表格的深度行业研究报告。

撰写要求：
1. 报告必须完整撰写全部章节，严禁中途截断！包括【执行摘要 (Executive Summary)】、大纲规划的每一个章节论述、数据对比表格（Markdown Table）以及最后的【应用场景落地与未来趋势研判】。
2. 写作风格客观、专业、详实，充分利用提供的量化指标与厂商事实。
3. 关键事实与数据必须在句末准确标注文献角标，格式为 [1], [2], [3] 等，角标编号必须与提供的证据源编号完全对应。
4. 正文末尾无需手动编写参考资料列表（系统验证器会自动统一生成排版）。
"""

def synthesize_report_node(state: ResearchState) -> Dict[str, Any]:
    """
    Writer 智能体节点：整合全部章节事实与论据，生成结构完整、不截断的深度研报初稿
    """
    query = state.get("user_query", "")
    outline: List[ChapterOutline] = state.get("outline", [])
    style = state.get("report_style", "consulting")
    critic_feedback = state.get("critic_feedback", "")
    
    # 构造材料上下文
    material_blocks = []
    for ch in outline:
        ch_num = ch.get("chapter_num", 1)
        title = ch.get("title", "")
        facts = "\n  - ".join(ch.get("extracted_facts", ["暂无特定事实"]))
        material_blocks.append(f"### 第 {ch_num} 章：{title}\n  - {facts}")
    
    materials_text = "\n\n".join(material_blocks)
    
    prompt = f"""
    研究课题：{query}
    报告风格：{style}
    评审意见参考：{critic_feedback}
    
    【搜集到的核心事实与证据材料（带引用来源编号）】：
    {materials_text}
    
    请严格基于上述材料与事实，完整撰写一篇专业、详实、逻辑严密的深度研究报告。
    务必完整输出所有章节论述、对比表格与最终结论展望，确保全篇内容完整收尾！
    """
    
    report_body = call_llm(
        prompt, 
        system_prompt=WRITER_SYSTEM_PROMPT, 
        temperature=0.3, 
        max_tokens=8192
    )
    
    return {
        "draft_report": report_body.strip(),
        "current_step": "verify",
        "logs": [f"[Writer] 深度研报初稿撰写完成！共约 {len(report_body)} 字符，准备进行防幻觉引用校验与顺位排序。"]
    }
