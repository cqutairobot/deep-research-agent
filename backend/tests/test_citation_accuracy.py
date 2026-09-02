import re
import pytest
from app.agents.graph import run_research_task
from app.agents.verifier import citation_verifier_node
from app.agents.state import ResearchState, CitationSource

def test_citation_accuracy_and_zero_hallucination():
    """
    引用精准度自动化核验测试 (严格对应规划书要求)：
    遍历全篇报告中出现的每一个 [N] 标记，比对对应 source_id 的真实来源是否存在，断言引用正确率为 100%。
    """
    # 模拟包含有效引用与虚构引用的状态
    mock_citations: list[CitationSource] = [
        {
            "id": 1,
            "title": "权威行业白皮书",
            "url": "https://example.com/whitepaper",
            "snippet": "2026年全球装车量预计突破10万台",
            "score": 0.95,
            "published_date": "2026-01-01"
        },
        {
            "id": 2,
            "title": "头部厂商年度财报",
            "url": "https://example.com/earnings",
            "snippet": "电芯能量密度实测突破500Wh/kg",
            "score": 0.92,
            "published_date": "2026-02-15"
        }
    ]
    
    state: ResearchState = {
        "task_id": "test_acc_1",
        "user_query": "新能源汽车与固态电池量产分析",
        "research_depth": "standard",
        "report_style": "consulting",
        "clarification": "",
        "outline": [],
        "citations": mock_citations,
        "current_step": "verify",
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "行业预计2026年装车突破10万台[1]，电芯能量密度突破500Wh/kg[2]，另外某些未经验证的数据声称成本降至0[999]。",
        "final_report": "",
        "logs": []
    }
    
    # 执行 Verifier 节点
    result = citation_verifier_node(state)
    verified_report = result["final_report"]
    
    # 1. 提取报告正文中的所有引用编号
    citations_section_pos = verified_report.find("## 📚 参考资料与可信数据来源")
    body_text = verified_report[:citations_section_pos] if citations_section_pos != -1 else verified_report
    
    cited_ids = [int(m.group(1)) for m in re.finditer(r'\[(\d+)\]', body_text)]
    valid_source_ids = {c["id"] for c in mock_citations}
    
    # 2. 严格断言：正文引用的每一个 ID 都必须 100% 属于合法来源库
    for cid in cited_ids:
        assert cid in valid_source_ids, f"发现虚构引用编号: [{cid}]"
        
    # 3. 严格断言：虚构编号 [999] 已被剔除或纠偏
    assert "[999]" not in body_text, "虚构引用 [999] 未被过滤"
    
    # 4. 验证末尾参考资料列表中包含有效引用的详情与链接
    for cid in cited_ids:
        assert f"[{cid}]" in verified_report
        matching_source = next(c for c in mock_citations if c["id"] == cid)
        assert matching_source["url"] in verified_report
