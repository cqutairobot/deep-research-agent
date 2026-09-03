import pytest
from app.services.slides_service import (
    extract_presentation_slides,
    generate_native_pptx,
    generate_interactive_html
)


def test_extract_presentation_slides():
    """断言：从研报中能结构化提炼封面、摘要、各章节卡片及落地路线"""
    report_md = """
    # 固态电池产业全景研报
    
    ## 核心发现
    - 能量密度提升达 400Wh/kg；
    - 界面阻抗问题取得突破性进展；
    - 2027 年有望率先应用于高端车型。
    
    ## 第 1 章：材料体系与工艺
    ### 1.1 硫化物固态电解质
    离子电导率显著优于氧化物路线。
    ### 1.2 锂金属负极技术
    需要抑制锂枝晶生长。
    
    ## 第 2 章：量产与设备供应链
    干法电极设备成为兵家必争之地。
    """
    slides = extract_presentation_slides("固态电池产业全景研报", report_md)
    assert len(slides) >= 5
    types = [s["type"] for s in slides]
    assert "cover" in types
    assert "summary" in types
    assert "chapter" in types
    assert "roadmap" in types
    assert "qa" in types
    
    # 检查封面标题
    assert slides[0]["title"] == "固态电池产业全景研报"
    # 检查摘要要点
    assert any("能量密度" in b for b in slides[1]["bullets"])


def test_generate_native_pptx():
    """断言：使用 python-pptx 生成原生 16:9 二进制演示文稿文件"""
    slides = [
        {"type": "cover", "title": "测试 PPTX 课题", "subtitle": "战略汇报", "meta": "2026年09月", "bullets": []},
        {"type": "summary", "title": "核心摘要", "subtitle": "核心洞察", "bullets": ["要点 1", "要点 2"]},
        {"type": "qa", "title": "Q&A", "subtitle": "交流致谢", "bullets": ["感谢聆听"]}
    ]
    pptx_io = generate_native_pptx(slides, "测试 PPTX 课题")
    pptx_bytes = pptx_io.getvalue()
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 10000
    # PPTX 本质为 ZIP 归档，前两个字节为 PK
    assert pptx_bytes[:2] == b"PK"


def test_generate_interactive_html():
    """断言：生成单文件自包含 HTML 幻灯片，包含全屏放映与键盘翻页逻辑"""
    slides = [
        {"type": "cover", "title": "测试 HTML 演示", "subtitle": "大屏放映", "meta": "2026年", "bullets": []},
        {"type": "chapter", "title": "第 1 章：核心论点", "subtitle": "论据展开", "bullets": ["论点 A", "论点 B"]}
    ]
    html_code = generate_interactive_html(slides, "测试 HTML 演示")
    assert "<!DOCTYPE html>" in html_code
    assert "slide-viewport" in html_code
    assert "toggleFullScreen" in html_code
    assert "测试 HTML 演示" in html_code
    assert "论点 A" in html_code
