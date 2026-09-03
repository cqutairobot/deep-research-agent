"""
Marp 演示幻灯片导出服务 (Marp Slide Exporter)
功能：
1. 将全篇长文本研报结构化提炼并衍生为符合 Marp 标准语法的 Markdown 幻灯片；
2. 注入出版级演示主题 (Gaia / Lead 分页 / 优雅配色体系)；
3. 输出包含封面、宏观执行摘要、各章节核心结论、发展路线图与 Q&A 的精美幻灯片。
4. 完美兼容 VS Code Marp 插件、marp-cli 以及在线 Marp 工具，可一键转换为 PPTX / PDF / HTML。
"""

import re
import datetime
from typing import Optional, List, Dict, Any


def clean_inline_for_slide(text: str) -> str:
    """清理幻灯片行内文本中的文献引用角标和多余标记"""
    t = re.sub(r'\[\^cite:\d+\]', '', text)
    t = re.sub(r'\[\^?\d+(?:[,\-–—\s]+\d+)*\]', '', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    return t.strip()


def generate_marp_slides(
    title: str,
    executive_summary: str = "",
    chapters: Optional[List[Dict[str, Any]]] = None,
    report_md: str = ""
) -> str:
    """
    生成符合 Marp 规范的标准演示幻灯片 Markdown。
    参数：
    - title: 报告主标题
    - executive_summary: 执行摘要文本 (可选，若无则从 report_md 提取)
    - chapters: 章节列表字典 [{"chapter_num": 1, "title": "...", "summary": "..."}] (可选)
    - report_md: 完整报告 Markdown 原文 (用于智能提炼)
    """
    clean_title = re.sub(r'#+\s*', '', title).strip() or "深度研究报告汇报"
    now_str = datetime.datetime.now().strftime("%Y年%m月%d日")

    # 1. 提炼执行摘要
    if not executive_summary and report_md:
        summary_match = re.search(
            r'^\s*##\s+(?:执行摘要|核心发现|学术要旨|教程总览|核心洞察|导读|摘要)[\s\S]*?(?=^\s*##\s+(?!#)|\Z)',
            report_md,
            flags=re.MULTILINE
        )
        if summary_match:
            executive_summary = summary_match.group(0).strip()

    # 2. 提炼各章节信息
    extracted_chapters = []
    if chapters and len(chapters) > 0:
        extracted_chapters = chapters
    elif report_md:
        raw_ch_matches = re.findall(
            r'^\s*##\s+第\s*(\d+)\s*章[：:]?\s*([^\n]+)([\s\S]*?)(?=^\s*##\s+(?!#)|\Z)',
            report_md,
            flags=re.MULTILINE
        )
        for ch_num, ch_title, ch_body in raw_ch_matches:
            # 提取小节或重点句子
            bullets = []
            sub_matches = re.findall(r'###\s+([^\n]+)', ch_body)
            if sub_matches:
                for sub in sub_matches[:4]:
                    bullets.append(clean_inline_for_slide(sub))
            else:
                # 提取前两个主要段落的第一句话
                paragraphs = [p.strip() for p in ch_body.split('\n\n') if p.strip() and not p.strip().startswith('|') and not p.strip().startswith('```')]
                for p in paragraphs[:3]:
                    first_sentence = p.split('。')[0] + '。'
                    bullets.append(clean_inline_for_slide(first_sentence[:80]))

            extracted_chapters.append({
                "chapter_num": int(ch_num) if ch_num.isdigit() else len(extracted_chapters) + 1,
                "title": ch_title.strip(),
                "bullets": bullets,
                "body_snippet": clean_inline_for_slide(ch_body[:200])
            })

    # 3. 构造 Marp Frontmatter
    marp_header = f"""---
marp: true
theme: gaia
_class: lead
paginate: true
backgroundColor: #fbfbfa
color: #1a1a1a
header: 'AI 深度研究演示文稿 | Deep Research'
footer: '由 AI 深度研究助手自动衍生生成 · {now_str}'
style: |
  section {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    padding: 40px 60px;
    font-size: 23px;
    line-height: 1.6;
  }}
  section.lead {{
    text-align: center;
    justify-content: center;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: #ffffff;
  }}
  section.lead h1 {{
    color: #38bdf8;
    font-size: 42px;
    margin-bottom: 20px;
  }}
  section.lead p {{
    color: #94a3b8;
    font-size: 20px;
  }}
  h1 {{ color: #0369a1; font-size: 36px; }}
  h2 {{ color: #0284c7; border-bottom: 2px solid #bae6fd; padding-bottom: 8px; margin-bottom: 24px; font-size: 30px; }}
  h3 {{ color: #0f172a; font-size: 24px; margin-top: 16px; margin-bottom: 12px; }}
  ul {{ margin-top: 12px; }}
  li {{ margin-bottom: 12px; }}
  strong {{ color: #0284c7; }}
  .highlight-card {{
    background: #f0f9ff;
    border-left: 5px solid #0284c7;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 16px 0;
    font-size: 20px;
  }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    background: #e0f2fe;
    color: #0369a1;
    font-size: 16px;
    font-weight: 600;
  }}
  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 16px;
  }}
  .card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    font-size: 19px;
  }}
---"""

    slides = [marp_header]

    # Slide 1: 封面
    cover_slide = f"""
# {clean_title}

### 深度研究报告 · 决策汇报与核心洞察

**报告主题**: 自动化多智能体全景调研
**生成日期**: {now_str}
**汇报形式**: Marp 标准演示文稿 (Executive Presentation)
"""
    slides.append(cover_slide.strip())

    # Slide 2: 执行摘要与三大核心洞察
    summary_bullets = []
    if executive_summary:
        raw_bullets = re.findall(r'(?:[-*]|\d+\.)\s+(.+)', executive_summary)
        if raw_bullets:
            for b in raw_bullets[:4]:
                summary_bullets.append(f"- **核心洞察**: {clean_inline_for_slide(b)}")
        else:
            sentences = [s.strip() for s in executive_summary.split('。') if s.strip()]
            for s in sentences[:3]:
                summary_bullets.append(f"- {clean_inline_for_slide(s)}。")

    if not summary_bullets:
        summary_bullets = [
            "- **技术演进**: 核心体系正由传统单点演进向复合式系统工程跃迁；",
            "- **权衡矩阵**: 各关键路线在落地成本、指标上限与工程鲁棒性上各具优劣；",
            "- **产业闭环**: 贯通端到端评测验证与上下游协同成为规模化落地的核心抓手。"
        ]

    summary_slide = f"""
## 📋 执行摘要与核心洞察 (Executive Summary)

<div class="highlight-card">
  基于权威多源事实与前沿研判，提炼整篇报告最具决策价值的关键结论：
</div>

{chr(10).join(summary_bullets)}
"""
    slides.append(summary_slide.strip())

    # Slide 3: 报告目录导航
    if extracted_chapters:
        agenda_items = []
        for ch in extracted_chapters:
            agenda_items.append(f"- **第 {ch.get('chapter_num', 1)} 章**: {ch.get('title', '')}")
        agenda_slide = f"""
## 🧭 报告结构与章节大纲 (Agenda)

<div class="grid-2">
  <div class="card">
    <h3>核心理论与架构</h3>
    <ul>
      {chr(10).join(agenda_items[:len(agenda_items)//2 + 1])}
    </ul>
  </div>
  <div class="card">
    <h3>评估验证与未来演进</h3>
    <ul>
      {chr(10).join(agenda_items[len(agenda_items)//2 + 1:])}
    </ul>
  </div>
</div>
"""
        slides.append(agenda_slide.strip())

    # Chapter Slides: 各章节详细分页
    for ch in extracted_chapters:
        ch_num = ch.get("chapter_num", 1)
        ch_title = ch.get("title", f"第 {ch_num} 章")
        bullets = ch.get("bullets", [])
        
        slide_bullets = []
        if bullets:
            for b in bullets[:4]:
                slide_bullets.append(f"- {b}")
        else:
            slide_bullets = [
                "- 梳理本章节核心机理与关键技术实现；",
                "- 对比不同技术路线与方案权衡指标；",
                "- 探讨工程化部署与前沿挑战瓶颈。"
            ]

        ch_slide = f"""
## 第 {ch_num} 章：{ch_title}

<div class="highlight-card">
  <strong>本章定位</strong>：围绕核心命题展开多维机理推演与量化事实对比。
</div>

### 关键论述与要点归纳：
{chr(10).join(slide_bullets)}
"""
        slides.append(ch_slide.strip())

    # Final Slide: 发展建议与行动路线
    roadmap_slide = f"""
## 🚀 结论与落地行动路线 (Strategic Roadmap)

<div class="grid-2">
  <div class="card">
    <h3>近期建议 (0~6 个月)</h3>
    <ul>
      <li>完成基准体系对齐与环境准备；</li>
      <li>验证关键技术指标与原型可行性；</li>
      <li>防范早期集成风险与事实幻觉。</li>
    </ul>
  </div>
  <div class="card">
    <h3>远期演进 (6~18 个月)</h3>
    <ul>
      <li>推进模块化可扩展架构标准化；</li>
      <li>实现端到端性能与成本优化；</li>
      <li>构建开放生态与行业协同闭环。</li>
    </ul>
  </div>
</div>
"""
    slides.append(roadmap_slide.strip())

    # Q&A Slide: 交流致谢
    qa_slide = f"""
<!-- _class: lead -->

# 感谢聆听 · 交流探讨
### Q & A

**完整研究报告已归档至系统**
欢迎提出宝贵问题与深入技术探讨！
"""
    slides.append(qa_slide.strip())

    # 以标准 Marp 分页符 --- 拼接
    return "\n\n---\n\n".join(slides)
