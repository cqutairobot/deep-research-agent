import pytest
from app.agents.graph import create_research_graph, run_research_task
from app.agents.planner import plan_outline_node
from app.agents.researcher import research_worker_node
from app.agents.critic import critic_node
from app.agents.writer import synthesize_report_node
from app.agents.verifier import citation_verifier_node
from app.agents.state import ResearchState

def test_planner_node():
    """测试 Planner 节点的大纲规划能力"""
    state: ResearchState = {
        "task_id": "test_planner_1",
        "user_query": "全球固态电池商业化进展与主要厂商壁垒对比",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [],
        "citations": [],
        "current_step": "plan",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }
    
    update = plan_outline_node(state)
    assert "outline" in update
    assert len(update["outline"]) >= 2
    assert "current_step" in update
    assert update["current_step"] == "research"
    assert len(update["logs"]) > 0

def test_researcher_node():
    """测试 Researcher 节点的检索与事实-引用编号绑定"""
    state: ResearchState = {
        "task_id": "test_research_1",
        "user_query": "固态电池测试",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [
            {
                "chapter_num": 1,
                "title": "技术路线对比",
                "focus": "离子电导率",
                "search_queries": ["固态电池 硫化物 离子电导率"],
                "extracted_facts": []
            }
        ],
        "citations": [],
        "current_step": "research",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }
    
    update = research_worker_node(state)
    assert "citations" in update
    assert len(update["citations"]) > 0
    assert "outline" in update
    assert len(update["outline"][0]["extracted_facts"]) > 0
    first_citation = update["citations"][0]
    assert first_citation["id"] == 1
    assert "url" in first_citation

def test_writer_and_verifier_nodes():
    """测试 Writer 初稿生成与 Verifier 校验器核验闭环"""
    state: ResearchState = {
        "task_id": "test_writer_1",
        "user_query": "固态电池测试",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [
            {
                "chapter_num": 1,
                "title": "技术路线对比",
                "focus": "离子电导率",
                "search_queries": [],
                "extracted_facts": ["硫化物离子电导率最高达 1.2x10^-2 S/cm (来源: Nature [1])"]
            }
        ],
        "citations": [
            {
                "id": 1,
                "url": "https://nature.com/articles/solid-state",
                "title": "Nature Energy Benchmark",
                "snippet": "Sulfide ionic conductivity reaches 1.2x10^-2 S/cm",
                "score": 0.95,
                "published_date": None
            }
        ],
        "current_step": "write",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }
    
    writer_update = synthesize_report_node(state)
    assert "draft_report" in writer_update
    state["draft_report"] = writer_update["draft_report"]
    
    verifier_update = citation_verifier_node(state)
    assert "final_report" in verifier_update
    report = verifier_update["final_report"]
    assert len(report) > 100
    assert "[1]" in report

def test_full_graph_end_to_end_phase2():
    """端到端集成测试：完整跑通 Phase 2 包含 Critic 反思与 Verifier 防幻觉的状态机闭环"""
    query = "全球固态电池商业化量产时间表与核心壁垒"
    final_state = run_research_task(query=query, research_depth="standard", report_style="consulting")
    
    assert final_state["current_step"] == "complete"
    assert len(final_state["outline"]) >= 2
    assert len(final_state["citations"]) >= 1
    assert len(final_state["final_report"]) > 300
    assert len(final_state["logs"]) >= 4
    # 验证包含了执行摘要与引用
    assert "执行摘要" in final_state["final_report"] or "Executive Summary" in final_state["final_report"]
    assert "参考资料" in final_state["final_report"] or "Citations" in final_state["final_report"]
