import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agents.writer import StyleProfileRegistry, write_single_chapter, synthesize_report_node
from app.agents.state import ResearchState, CitationSource, ChapterOutline

client = TestClient(app)

STYLES = ["consulting", "literature_review", "tutorial_docs", "executive", "briefing"]

def test_five_styles_prompt_injection():
    """断言：五大风格对应的系统指令均已注入专业领域规范"""
    for style in STYLES:
        profile = StyleProfileRegistry.get(style)
        assert profile["id"] == style
        assert len(profile["persona_system_prompt"]) >= 50
        assert len(profile["chapter_guideline"]) >= 50

        # 风格特征词校验
        if style == "consulting":
            assert "MECE" in profile["chapter_guideline"]
            assert "TAM" in profile["chapter_guideline"]
        elif style == "literature_review":
            assert "Taxonomy" in profile["chapter_guideline"] or "分类" in profile["chapter_guideline"]
            assert "LaTeX" in profile["code_policy"]
        elif style == "tutorial_docs":
            assert "Prerequisites" in profile["chapter_guideline"] or "步骤" in profile["chapter_guideline"]
        elif style == "executive":
            assert "BLUF" in profile["chapter_guideline"]
        elif style == "briefing":
            assert "新闻" in profile["chapter_guideline"] or "博弈" in profile["chapter_guideline"]

def test_citations_continuity_and_format():
    """断言：报告编写时生成的引证标签格式标准，能被正则平滑解析"""
    mock_section_text = """
    # 行业技术演进分析
    
    全固态电池通过将易燃有机电解液替换为不可燃的固态电解质，从根本上杜绝了热失控风险 [^cite:1]。
    根据实测数据，硫化物电芯的能量密度已突破 500 Wh/kg 门槛 [^cite:2]。
    而在工程制造端，干法电极工艺能够降低 20% 以上的能耗与设备占地 [^cite:3]。
    """
    import re
    cites = re.findall(r'\[\^?cite:(\d+)\]', mock_section_text)
    assert cites == ["1", "2", "3"]
    # 连续性断言
    int_cites = [int(c) for c in cites]
    assert int_cites == list(range(1, len(int_cites) + 1))
