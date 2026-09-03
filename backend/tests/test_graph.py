import pytest
from app.agents.graph import create_research_graph, run_research_task
from app.agents.planner import plan_outline_node
from app.agents.researcher import research_worker_node
from app.agents.critic import critic_node
from app.agents.writer import synthesize_report_node
from app.agents.verifier import citation_verifier_node
from app.agents.state import ResearchState

from unittest.mock import patch

def test_planner_node():
    """测试 Planner 节点的大纲规划能力 (带 LLM 模拟或实测)"""
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
    
    mock_llm_response = """```json
    {
        "clarification": "重点聚焦固态电池产业链与量产时间线",
        "outline": [
            {
                "chapter_num": 1,
                "title": "技术路线与电解质材料体系对比",
                "focus": "离子电导率与界面阻抗",
                "search_queries": ["固态电池 硫化物 氧化物 离子电导率"]
            },
            {
                "chapter_num": 2,
                "title": "主要厂商产业化进度与装车量产时间表",
                "focus": "丰田、宁德时代、卫蓝新能源量产节点",
                "search_queries": ["丰田 固态电池 2027 量产", "宁德时代 凝聚态电池"]
            }
        ]
    }
    ```"""
    
    with patch("app.agents.planner.call_llm", return_value=mock_llm_response):
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
    
    mock_search_results = [
        {
            "title": "硫化物固态电池最新研究",
            "url": "https://example.com/battery-research",
            "content": "硫化物固态电解质室温离子电导率突破 1.0x10^-2 S/cm，处于行业领先地位。",
            "snippet": "硫化物固态电解质室温离子电导率突破 1.0x10^-2 S/cm",
            "score": 0.95
        }
    ]
    
    with patch("app.agents.researcher.search_web", return_value=mock_search_results), \
         patch("app.agents.researcher.compress_webpage_facts", return_value=["硫化物固态电解质室温离子电导率突破 1.0x10^-2 S/cm"]):
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
                "extracted_facts": ["硫化物离子电导率最高达 1.2x10^-2 S/cm (来源: Nature [^cite:1])"]
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
    
    with patch("app.agents.writer.call_llm", return_value="# 全球固态电池产业研究报告\n\n## 1. 技术路线对比\n硫化物离子电导率最高达 1.2x10^-2 S/cm[^cite:1]。"):
        writer_update = synthesize_report_node(state)
        assert "draft_report" in writer_update
        state["draft_report"] = writer_update["draft_report"]
        
        verifier_update = citation_verifier_node(state)
        assert "final_report" in verifier_update
        report = verifier_update["final_report"]
        assert len(report) > 50
        assert "[1]" in report
        assert "https://nature.com/articles/solid-state" in report
