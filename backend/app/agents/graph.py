import uuid
from typing import Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, START, END

from app.agents.state import ResearchState
from app.agents.planner import plan_outline_node
from app.agents.researcher import research_worker_node
from app.agents.critic import critic_node
from app.agents.writer import synthesize_report_node
from app.agents.verifier import citation_verifier_node

def should_continue_research(state: ResearchState) -> Literal["researcher", "writer"]:
    """
    条件路由函数：判断是否需要根据 Critic 建议触发二阶深度检索循环
    """
    needs_more = state.get("needs_more_research", False)
    iter_count = state.get("iteration_count", 1)
    max_iter = state.get("max_iterations", 2)
    
    if needs_more and iter_count <= max_iter:
        return "researcher"
    return "writer"

def create_research_graph():
    """
    构建并编译 Deep Research Agent 的 Phase 2 高级带环状态图
    
    工作流程:
    START -> planner -> researcher -> critic 
                ^                        |
                |-(needs_more_research)--|
                                         v
                                       writer -> verifier -> END
    """
    builder = StateGraph(ResearchState)
    
    # 注册 5 大智能体节点
    builder.add_node("planner", plan_outline_node)
    builder.add_node("researcher", research_worker_node)
    builder.add_node("critic", critic_node)
    builder.add_node("writer", synthesize_report_node)
    builder.add_node("verifier", citation_verifier_node)
    
    # 编排基础流
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "critic")
    
    # 注册 Critic 之后的条件分支
    builder.add_conditional_edges(
        "critic",
        should_continue_research,
        {
            "researcher": "researcher",
            "writer": "writer"
        }
    )
    
    builder.add_edge("writer", "verifier")
    builder.add_edge("verifier", END)
    
    return builder.compile()

# 全局单例图
research_graph = create_research_graph()

def run_research_task(
    query: str,
    research_depth: str = "standard",
    report_style: str = "consulting",
    task_id: Optional[str] = None,
    max_iterations: int = 2
) -> ResearchState:
    """
    同步执行一次完整的深度调研任务 (支持多轮反思循环与引用核验)
    """
    tid = task_id or f"task_{uuid.uuid4().hex[:8]}"
    
    # 根据深度调节最大递归轮数
    if research_depth == "quick":
        max_iter = 1
    elif research_depth == "deep":
        max_iter = 3
    else:
        max_iter = max_iterations
    
    initial_state: ResearchState = {
        "task_id": tid,
        "user_query": query,
        "research_depth": research_depth,
        "report_style": report_style,
        "clarification": "",
        "outline": [],
        "citations": [],
        "current_step": "plan",
        "iteration_count": 1,
        "max_iterations": max_iter,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": [f"[System] 调研任务初始化完成，任务ID: {tid} (最大反思轮数: {max_iter})"]
    }
    
    final_state = research_graph.invoke(initial_state)
    return final_state
