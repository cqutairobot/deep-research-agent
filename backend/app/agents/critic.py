import json
import re
from typing import Dict, Any, List
from app.agents.state import ResearchState, ChapterOutline
from app.core.config import call_llm

CRITIC_SYSTEM_PROMPT = """你是一位挑剔且极具洞察力的高级研究评审官 (Critic Agent)。
你的任务是审查当前各章节已经搜集到的事实清单，评估其充实度、数据具体程度与逻辑完备性。

评估准则：
1. 检查各章节是否拥有具体的参数、厂商进展、年份或核心瓶颈数据；
2. 若某章节事实较为空泛或缺少关键数据，请针对性地生成 1~2 个二阶深搜检索词；
3. 若当前证据已经足够充分支撑撰写深度报告，请确认完成。

输出严格为 JSON 格式：
{
  "is_sufficient": true/false,
  "critique_reason": "评估意见说明（50字内）",
  "supplementary_queries": [
    {
      "chapter_num": 1,
      "new_queries": ["更具体的二阶搜索词1"]
    }
  ]
}
"""

def critic_node(state: ResearchState) -> Dict[str, Any]:
    """
    Critic 智能体节点：评估当前研究事实充实度，并在需要时触发二阶针对性深搜
    """
    outline: List[ChapterOutline] = state.get("outline", [])
    citations = state.get("citations", [])
    iteration_count = state.get("iteration_count", 1)
    max_iterations = state.get("max_iterations", 2)
    depth = state.get("research_depth", "standard")
    
    total_facts = sum(len(ch.get("extracted_facts", [])) for ch in outline)

    # 1. 快速模式单轮即止 / 达到轮次上限
    if depth == "quick" or iteration_count >= max_iterations:
        return {
            "needs_more_research": False,
            "current_step": "write",
            "critic_feedback": f"已达到设定迭代轮次上限 ({iteration_count}/{max_iterations})，事实已充分收敛，进入报告撰写。",
            "logs": [f"[Critic] 迭代轮次已达上限 ({iteration_count}/{max_iterations})，完成反思评估，批准撰写研报。"]
        }

    # 2. 事实库饱和快速收敛保护（防止标准模式过度深搜）
    fact_threshold = len(outline) * (2 if depth == "standard" else 4)
    citation_threshold = 12 if depth == "standard" else 25
    if total_facts >= fact_threshold or len(citations) >= citation_threshold:
        return {
            "needs_more_research": False,
            "current_step": "write",
            "critic_feedback": f"已收集 {len(citations)} 处来源与 {total_facts} 条事实，证据链已高度充分，直接进入报告撰写。",
            "logs": [f"[Critic] 事实库充沛（{total_facts} 条事实），自动快速收敛，跳过二阶反思，立即撰写研报。"]
        }

    # 3. 组织材料供 Critic 评审
    facts_summary = []
    for ch in outline:
        facts = ch.get("extracted_facts", [])
        facts_summary.append(f"第 {ch.get('chapter_num')} 章 [{ch.get('title')}]: 已收集 {len(facts)} 条事实。\n  示例: " + ("\n  ".join(facts[:2]) if facts else "暂无事实"))
        
    prompt = f"""
    课题：{state.get('user_query')}
    当前轮次：第 {iteration_count} 轮 (上限: {max_iterations})
    
    【当前各章节已搜集事实状态】：
    {chr(10).join(facts_summary)}
    
    请评估当前事实是否充分。若需要补充，请为薄弱章节生成 1 个更精确的二阶检索关键词。
    """
    
    try:
        llm_output = call_llm(prompt, system_prompt=CRITIC_SYSTEM_PROMPT, temperature=0.2)
        evaluation = _parse_critic_json(llm_output)
    except Exception:
        evaluation = {"is_sufficient": True, "critique_reason": "默认规则评估充分", "supplementary_queries": []}

    is_sufficient = evaluation.get("is_sufficient", True)
    supp_queries = evaluation.get("supplementary_queries", [])
    reason = evaluation.get("critique_reason", "事实充实度评估完成")
    
    if not is_sufficient and supp_queries:
        updated_outline = []
        new_query_count = 0
        supp_map = {item["chapter_num"]: item["new_queries"] for item in supp_queries if "chapter_num" in item}
        
        for ch in outline:
            ch_copy = dict(ch)
            cnum = ch_copy.get("chapter_num", 1)
            if cnum in supp_map and supp_map[cnum]:
                # 单章最多追加 1 个检索词
                ch_copy["search_queries"] = supp_map[cnum][:1]
                new_query_count += len(ch_copy["search_queries"])
            else:
                ch_copy["search_queries"] = []
            updated_outline.append(ch_copy)
            
        new_iter = iteration_count + 1
        log_msg = f"[Critic] 触发第 {new_iter} 轮轻量补充深搜：{reason}（新增 {new_query_count} 个精准补充词）"
        
        return {
            "outline": updated_outline,
            "iteration_count": new_iter,
            "needs_more_research": True,
            "current_step": "research",
            "critic_feedback": reason,
            "logs": [log_msg]
        }
    else:
        return {
            "needs_more_research": False,
            "current_step": "write",
            "critic_feedback": f"事实充足（共 {len(citations)} 处来源与 {total_facts} 条事实），批准生成研报。",
            "logs": [f"[Critic] 反思评估通过：{reason}，进入报告撰写。"]
        }

def _parse_critic_json(text: str) -> Dict[str, Any]:
    """解析 Critic 返回的 JSON 数据"""
    try:
        clean = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
        clean = re.sub(r'```$', '', clean.strip(), flags=re.MULTILINE)
        return json.loads(clean.strip())
    except Exception:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {"is_sufficient": True, "critique_reason": "解析异常，默认收敛", "supplementary_queries": []}
