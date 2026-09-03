import pytest
from unittest.mock import patch, MagicMock
from app.agents.writer import StyleProfileRegistry, write_single_chapter, synthesize_report_node
from app.agents.planner import plan_outline_node
from app.services.docx_exporter import generate_editorial_docx

def test_style_registry_lookup_and_aliases():
    assert StyleProfileRegistry.get("consulting")["id"] == "consulting"
    # 别名映射
    assert StyleProfileRegistry.get("academic")["id"] == "literature_review"
    assert StyleProfileRegistry.get("survey")["id"] == "literature_review"
    assert StyleProfileRegistry.get("tutorial")["id"] == "tutorial_docs"
    assert StyleProfileRegistry.get("cookbook")["id"] == "tutorial_docs"
    assert StyleProfileRegistry.get("exec")["id"] == "executive"
    assert StyleProfileRegistry.get("memo")["id"] == "executive"
    assert StyleProfileRegistry.get("news")["id"] == "briefing"
    # 未知回退
    assert StyleProfileRegistry.get("unknown_style_xyz")["id"] == "consulting"

def test_style_profile_features():
    lit = StyleProfileRegistry.get("literature_review")
    tut = StyleProfileRegistry.get("tutorial_docs")
    con = StyleProfileRegistry.get("consulting")
    exe = StyleProfileRegistry.get("executive")
    brf = StyleProfileRegistry.get("briefing")

    # 学术综述
    assert "Taxonomy" in lit["chapter_guideline"] or "分类学" in lit["chapter_guideline"]
    assert "LaTeX" in lit["code_policy"]
    assert "Open Research Challenges" in lit["chapter_guideline"] or "开放" in lit["chapter_guideline"]
    assert lit["docx_primary_color"] == "334155"

    # 开发者教程
    assert "Prerequisites" in tut["chapter_guideline"] or "先决条件" in tut["chapter_guideline"]
    assert "Step-by-Step" in tut["chapter_guideline"] or "步骤" in tut["chapter_guideline"]
    assert "Troubleshooting" in tut["chapter_guideline"] or "排错" in tut["chapter_guideline"]
    assert tut["docx_primary_color"] == "0F766E"

    # 商业咨询
    assert "MECE" in con["chapter_guideline"]
    assert "TAM" in con["chapter_guideline"]
    assert con["docx_primary_color"] == "1E40AF"

    # 高管简报
    assert "BLUF" in exe["chapter_guideline"]
    assert "严禁输出底层技术代码" in exe["code_policy"]
    assert exe["docx_primary_color"] == "78350F"

    # 前沿特稿
    assert "博弈" in brf["chapter_guideline"]
    assert "甘特图" in brf["chart_preference"]
    assert brf["docx_primary_color"] == "7C3AED"

@patch("app.agents.planner.call_llm")
def test_planner_style_instruction_adaptation(mock_call):
    mock_call.return_value = '{"clarification": "学术课题综述", "outline": [{"chapter_num": 1, "title": "学术综述第一章", "focus": "分类学", "search_queries": ["test"]}]}'

    state = {
        "user_query": "视觉大模型演进",
        "research_depth": "standard",
        "report_style": "literature_review",
        "custom_llm_config": None
    }
    res = plan_outline_node(state)
    assert len(res["outline"]) == 1
    assert res["outline"][0]["title"] == "学术综述第一章"
    
    # 验证 Prompt 中包含了学术综述专属指导
    call_prompt = mock_call.call_args[0][0]
    assert "学术综述" in call_prompt
    assert "Taxonomy" in call_prompt or "分类学" in call_prompt

@patch("app.agents.writer.call_llm")
def test_writer_style_injection(mock_call):
    mock_call.return_value = "## 第 1 章：实操环境搭建\n\n### 1. 先决条件\n配置如下代码。"
    chapter = {
        "chapter_num": 1,
        "title": "实操环境搭建",
        "focus": "Python 3.10 环境部署",
        "search_queries": ["install python"],
        "extracted_facts": ["需安装 torch==2.1.0 [^cite:1]"]
    }
    res = write_single_chapter(
        query="分布式训练环境准备",
        chapter=chapter,
        style="tutorial_docs"
    )
    assert res.startswith("## 第 1 章：实操环境搭建")
    mock_call.assert_called_once()
    system_prompt = mock_call.call_args[1]["system_prompt"]
    prompt = mock_call.call_args[0][0]
    
    # 验证注入了布道师人设与实操教程要求
    assert "技术布道师" in system_prompt or "架构师" in system_prompt
    assert "先决条件" in prompt or "Prerequisites" in prompt
    assert "Troubleshooting" in prompt or "排错" in prompt

def test_docx_export_style_theming():
    docx_io = generate_editorial_docx(
        report_md="# 测试\n## 第 1 章：导论\n内容论述。",
        title="前沿评测",
        style="tutorial_docs"
    )
    assert docx_io is not None
    assert docx_io.getbuffer().nbytes > 1000
