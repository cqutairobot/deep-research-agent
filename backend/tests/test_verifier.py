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

def test_citation_verifier_hallucination_removal():
    """测试虚构标号（如 [99]）被直接剔除，且绝不绑定到其他合法引用上 (Bug 7)"""
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
                "title": "真实来源 1",
                "url": "https://example.com/real1",
                "snippet": "真实论据 1",
                "score": 0.9,
                "published_date": None
            }
        ],
        "current_step": "verify",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "根据不存在的虚构报告[99]，该技术预计明年普及[1]。",
        "final_report": "",
        "logs": []
    }
    
    update = citation_verifier_node(state)
    report = update["final_report"]
    # 虚构标号已被直接剔除，且没有被错误重命名为其他合法来源 (Bug 7)
    assert "[99]" not in report
    assert "[1]" in report
    assert "真实来源 1" in report
    assert len(update["citations"]) == 1

def test_citation_verifier_disambiguation_and_years():
    """测试 [^cite:N] 特异标记与正文年份 [2024]、代码块数组 [0] 的消歧保护 (Bug 8)"""
    state: ResearchState = {
        "task_id": "test_ver_3",
        "user_query": "测试",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [],
        "citations": [
            {
                "id": 10,
                "title": "技术规范 10",
                "url": "https://example.com/spec10",
                "snippet": "全固态能量密度突破",
                "score": 0.95,
                "published_date": None
            }
        ],
        "current_step": "verify",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "行业在 [2024] 年取得了重要进展[^cite:10]，且定义了数组 `const arr = list[0];`。",
        "final_report": "",
        "logs": []
    }

    update = citation_verifier_node(state)
    report = update["final_report"]
    # 年份 [2024] 保持原样，不被当作引用编号重排
    assert "[2024]" in report
    # 代码块中 list[0] 保持原样
    assert "list[0]" in report
    # [^cite:10] 被顺位重排为连续的第一个引用 [1]
    assert "[1]" in report
    assert "https://example.com/spec10" in report
