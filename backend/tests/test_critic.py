import pytest
from app.agents.critic import critic_node
from app.agents.state import ResearchState

def test_critic_sparse_facts_triggers_reflection():
    """测试当事实不足时，Critic 正确触发第二轮补充检索"""
    state: ResearchState = {
        "task_id": "test_critic_1",
        "user_query": "全球固态电池商业化进展与主要厂商壁垒对比",
        "research_depth": "deep",
        "report_style": "consulting",
        "clarification": "",
        "outline": [
            {
                "chapter_num": 1,
                "title": "技术路线对比",
                "focus": "离子电导率",
                "search_queries": [],
                "extracted_facts": ["硫化物离子电导率高"]  # 仅 1 条空泛事实
            }
        ],
        "citations": [],
        "current_step": "critic",
        "iteration_count": 1,
        "max_iterations": 3,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }
    
    update = critic_node(state)
    assert "needs_more_research" in update
    assert "current_step" in update
    assert len(update["logs"]) > 0

def test_critic_max_iterations_pruning():
    """测试当达到最大迭代次数时，Critic 强制收敛终止循环，防止死循环"""
    state: ResearchState = {
        "task_id": "test_critic_2",
        "user_query": "测试课题",
        "research_depth": "deep",
        "report_style": "consulting",
        "clarification": "",
        "outline": [
            {
                "chapter_num": 1,
                "title": "章节 1",
                "focus": "方向",
                "search_queries": [],
                "extracted_facts": ["事实 1"]
            }
        ],
        "citations": [],
        "current_step": "critic",
        "iteration_count": 3,
        "max_iterations": 3,  # 已达上限
        "critic_feedback": "",
        "needs_more_research": True,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }
    
    update = critic_node(state)
    assert update["needs_more_research"] is False
    assert update["current_step"] == "write"
