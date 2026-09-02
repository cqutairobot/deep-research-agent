import pytest
from app.agents.verifier import citation_verifier_node
from app.agents.state import ResearchState, CitationSource

def test_citation_verifier_correct_refs():
    """测试真实存在的引用标号正常保留"""
    state: ResearchState = {
        "task_id": "test_ver_1",
        "user_query": "测试",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [],
        "citations": [
            {
                "id": 1,
                "title": "权威期刊 1",
                "url": "https://example.com/1",
                "snippet": "丰田宣布2027年量产",
                "score": 0.95,
                "published_date": None
            },
            {
                "id": 2,
                "title": "权威财报 2",
                "url": "https://example.com/2",
                "snippet": "宁德时代突破500Wh/kg",
                "score": 0.9,
                "published_date": None
            }
        ],
        "current_step": "verify",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "丰田规划于2027年小规模装车[1]，宁德时代样品能量密度达到500Wh/kg[2]。",
        "final_report": "",
        "logs": []
    }
    
    update = citation_verifier_node(state)
    assert "final_report" in update
    report = update["final_report"]
    assert "[1]" in report
    assert "[2]" in report
    assert "https://example.com/1" in report
    assert "https://example.com/2" in report

def test_citation_verifier_hallucination_fixing():
    """测试虚构标号（如 [99]）被检测并纠偏"""
    state: ResearchState = {
        "task_id": "test_ver_2",
        "user_query": "测试",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [],
        "citations": [
            {
                "id": 1,
                "title": "真实来源",
                "url": "https://example.com/real",
                "snippet": "真实论据",
                "score": 0.9,
                "published_date": None
            }
        ],
        "current_step": "verify",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "根据不存在的文献说明[99]，该技术预计明年普及[1]。",
        "final_report": "",
        "logs": []
    }
    
    update = citation_verifier_node(state)
    report = update["final_report"]
    assert "[99]" not in report  # 虚构标号已被剔除或纠偏
    assert "[1]" in report
    assert len(update["logs"]) > 0
