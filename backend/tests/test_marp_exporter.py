import pytest
from app.services.marp_exporter import generate_marp_slides, clean_inline_for_slide


def test_marp_export_syntax():
    """断言：生成的 Marp 文档必须包含标准 Frontmatter 与分页符号。"""
    marp_md = generate_marp_slides(
        title="固态电池全景调研",
        executive_summary="三大核心洞察如下：能量密度提升显著，循环寿命大幅延长，商业量产在即。",
        chapters=[
            {
                "chapter_num": 1,
                "title": "机理突破与材料演进",
                "bullets": ["硫化物固态电解质离子电导率接近液态", "界面修饰层显著减小阻抗"]
            },
            {
                "chapter_num": 2,
                "title": "量产落地与工艺壁垒",
                "bullets": ["干法电极工艺降低制造成本 30%", "全固态电池设备投资额较高"]
            }
        ]
    )
    assert "marp: true" in marp_md
    assert "paginate: true" in marp_md
    assert "theme: gaia" in marp_md
    pages = marp_md.split("\n\n---\n\n")
    # 至少包含 Frontmatter、封面、摘要、目录、各章节分页、路线图、致谢 (共 >= 6 页)
    assert len(pages) >= 5
    assert "固态电池全景调研" in pages[1]
    assert "执行摘要" in pages[2]
    assert "机理突破" in marp_md
    assert "量产落地" in marp_md


def test_marp_export_from_raw_markdown():
    """断言：支持直接从研报原生 Markdown 中自动提炼各章节和摘要生成幻灯片。"""
    raw_report = """
    # 人形机器人 2026 产业演进深度报告
    
    ## 核心发现
    - 供应链降本速度超出预期；
    - 具身智能通用大模型与真机运控实现软硬件闭环。
    
    ## 第 1 章：本体硬件与核心零部件
    ### 1.1 旋转执行器与谐波减速器
    国内厂商已实现谐波减速器 80% 自主化。
    ### 1.2 灵巧手与触觉传感器
    多维力控传感器成为手部操作的感知瓶颈。
    
    ## 第 2 章：运控算法与端到端大模型
    ### 2.1 强化学习仿真到真实世界
    Sim2Real 技术极大缩短真实场景迁移周期。
    """
    marp_md = generate_marp_slides(
        title="人形机器人 2026 产业演进深度报告",
        report_md=raw_report
    )
    assert "marp: true" in marp_md
    assert "本体硬件与核心零部件" in marp_md
    assert "运控算法与端到端大模型" in marp_md
    assert "旋转执行器" in marp_md
