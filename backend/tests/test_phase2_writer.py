import pytest
from unittest.mock import patch, MagicMock
from app.agents.state import ResearchState, ChapterOutline, CitationSource
from app.agents.writer import synthesize_report_node, write_single_chapter
from app.agents.verifier import citation_verifier_node

def test_hierarchical_multi_chapter_writer_structure():
    """测试 Map-Reduce 逐章深度合成引擎结构 (章节独立展开 + Global Editor 统合)"""
    outline: list[ChapterOutline] = [
        {
            "chapter_num": 1,
            "title": "全球固态电池技术路径与主流机理对比",
            "focus": "对比硫化物、氧化物与聚合物电解质性能基准",
            "search_queries": ["固态电池 硫化物 氧化物 能量密度"],
            "extracted_facts": [
                "硫化物电解质室温离子电导率高达 10^-2 S/cm [来源: 丰田技术白皮书 [1]]",
                "氧化物体系空气稳定性好但界面阻抗偏高 [来源: 清陶能源发布会 [2]]"
            ]
        },
        {
            "chapter_num": 2,
            "title": "主要厂商商业化量产时间表与产能规划",
            "focus": "梳理头部车企与电池厂中试线与量产节点",
            "search_queries": ["丰田 宁德时代 量产 时间表"],
            "extracted_facts": [
                "丰田计划 2027~2028 年实现全固态电池小规模装车 [来源: 丰田官方公报 [3]]",
                "宁德时代全固态电池计划 2027 年达到小批量生产水平 [来源: 财联社 [4]]"
            ]
        }
    ]

    state: ResearchState = {
        "task_id": "test_phase2_task",
        "user_query": "全球固态电池商业化进展与主要厂商壁垒对比",
        "research_depth": "deep",
        "report_style": "consulting",
        "clarification": "",
        "outline": outline,
        "citations": [
            {"id": 1, "url": "https://toyota.com", "title": "丰田技术白皮书", "snippet": "硫化物电解质室温离子电导率高", "score": 0.98, "published_date": None},
            {"id": 2, "url": "https://qingtao.com", "title": "清陶能源发布会", "snippet": "氧化物体系空气稳定性好", "score": 0.95, "published_date": None},
            {"id": 3, "url": "https://toyota-news.com", "title": "丰田官方公报", "snippet": "2027~2028年小规模装车", "score": 0.95, "published_date": None},
            {"id": 4, "url": "https://cls.cn", "title": "财联社", "snippet": "2027年小批量生产", "score": 0.95, "published_date": None}
        ],
        "chapter_drafts": {},
        "current_step": "research",
        "local_documents": [],
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "事实充分",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }

    # 执行 Writer 节点
    result = synthesize_report_node(state)
    
    assert "draft_report" in result
    assert "chapter_drafts" in result
    draft_report = result["draft_report"]
    
    # 验证 Map 产物与 Reduce 产物
    assert len(result["chapter_drafts"]) == 2
    assert "第 1 章" in draft_report
    assert "第 2 章" in draft_report
    assert "执行摘要" in draft_report or "Executive Summary" in draft_report
    assert "|" in draft_report # 验证包含 Markdown 表格
    assert "mermaid" in draft_report.lower() # 验证包含 Mermaid 图表

def test_writer_and_verifier_pipeline_with_mermaid():
    """测试 Writer + Verifier 完整链条：防幻觉角标重排 + 包含 Mermaid 图表"""
    state: ResearchState = {
        "task_id": "test_pipeline_task",
        "user_query": "具身智能灵巧手技术",
        "research_depth": "standard",
        "report_style": "academic",
        "clarification": "",
        "outline": [
            {
                "chapter_num": 1,
                "title": "灵巧手电机与腱绳驱动对比",
                "focus": "分析空心杯电机与腱绳传动效率",
                "search_queries": ["灵巧手 电机 传动"],
                "extracted_facts": ["空心杯电机功率密度高响应快 [来源: 机器人前沿 [1]]"]
            }
        ],
        "citations": [
            {"id": 1, "url": "https://robotics.org/1", "title": "机器人前沿", "snippet": "空心杯电机功率密度高响应快", "score": 0.98, "published_date": None}
        ],
        "chapter_drafts": {},
        "current_step": "research",
        "local_documents": [],
        "iteration_count": 1,
        "max_iterations": 2,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }

    writer_out = synthesize_report_node(state)
    state.update(writer_out)
    
    verifier_out = citation_verifier_node(state)
    state.update(verifier_out)

    final_report = state.get("final_report", "")
    assert len(final_report) > 500
    assert "📚 参考资料" in final_report
    assert "[1]" in final_report
    assert "```mermaid" in final_report
