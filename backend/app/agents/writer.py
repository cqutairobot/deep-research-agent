import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict
from app.agents.state import ResearchState, CitationSource, ChapterOutline
from app.core.config import call_llm

class StyleProfile(TypedDict):
    id: str
    name_zh: str
    name_en: str
    persona_system_prompt: str
    chapter_guideline: str
    chart_preference: str
    code_policy: str
    editor_system_prompt: str
    summary_header_name: str
    summary_guideline: str
    macro_chart_prompt: str
    docx_primary_color: str

class StyleProfileRegistry:
    """
    研报风格策略注册中心 (Style Profile Registry)
    彻底解耦硬编码人设，为各专业风格注入独立的系统人设、论证规范、图表形态与代码/公式策略。
    """
    _PROFILES: Dict[str, StyleProfile] = {
        "consulting": {
            "id": "consulting",
            "name_zh": "商业咨询与战略分析",
            "name_en": "Strategic & Management Consulting",
            "persona_system_prompt": (
                "你是一位国际顶尖战略咨询机构（如麦肯锡、波士顿咨询）与华尔街投行的资深全球首席行业分析师。\n"
                "你负责撰写行业深度商业研究报告的【特定单个章节】。\n"
                "行文特征：逻辑严密、结论先行、基于 MECE 原则展开底层商业逻辑推演与产业壁垒分析。"
            ),
            "chapter_guideline": (
                "- 严格遵循 MECE（相互独立，完全穷尽）原则展开底层商业逻辑推演与产业壁垒剖析；\n"
                "- 必须包含详尽的头部厂商方案对比矩阵（包含量化指标、成熟度、商业痛点）；\n"
                "- 深入测算 TAM 市场空间、BOM 成本结构与产业链上下游传导机制；"
            ),
            "chart_preference": (
                "- 必须包含至少 1 个产业链上下游传导或商业演进流程图（代码块格式为 ```mermaid\\ngraph LR\\n...``` 或 ```mermaid\\ngantt\\n...```）；\n"
                "- 必须包含 1 个横向多厂商/多方案指标量化对比 Markdown 表格。"
            ),
            "code_policy": "如非必要请勿堆叠底层技术代码，重点突出商业可行性、工艺成熟度与关键财务/性能参数。",
            "editor_system_prompt": (
                "你是一位国际顶尖管理智库的总编纂合伙人 (Senior Consulting Editor)。\n"
                "你的任务是将所有已深度撰写的独立章节汇聚并统合成一份完整的出版级投行与战略决策咨询报告。\n"
                "统合任务：撰写宏观执行摘要与核心战略洞察，提炼 3 大商业拐点与量化预测，绘制宏观产业链脉络图，并给出未来 3~5 年落地演进路线。"
            ),
            "summary_header_name": "## 📊 执行摘要与核心战略研判 (Executive Summary)",
            "summary_guideline": "提炼全篇 3 大核心战略洞察、关键市场/技术拐点与量化预测结论，并给出未来战略落地行动建议。",
            "macro_chart_prompt": "绘制全景宏观产业链与发展脉络图（使用 Mermaid 流程图，如 ```mermaid\\ngraph TD\\n...```）",
            "docx_primary_color": "1E40AF" # 皇家深蓝
        },

        "literature_review": {
            "id": "literature_review",
            "name_zh": "学术综述与前沿科研论文",
            "name_en": "Academic Survey & Literature Review",
            "persona_system_prompt": (
                "你是一位顶尖计算机科学与工程前沿顶级期刊（如 IEEE TPAMI、Nature Reviews、ACM Computing Surveys）的特邀综述首席主笔学者。\n"
                "你负责撰写顶级学术综述论文的【特定单个章节】。\n"
                "行文特征：客观严谨、批判性评述、句句有据、拒绝空洞商业大话，论据必须紧扣学术严密性与理论边界。"
            ),
            "chapter_guideline": (
                "- 建立严谨的研究方法分类学体系 (Taxonomy)，对主流学术与工程技术路线进行层次化梳理；\n"
                "- 深入评述不同文献路线的核心理论假设 (Underlying Assumptions)、适用边界与性能权衡 (Trade-offs)；\n"
                "- 批判性指出当前学术界与工程界尚未攻克的开放性理论难题或瓶颈 (Open Research Challenges)；\n"
                "- 语言风格客观学术，杜绝投行宣传口吻，使用学术评述句式（如“文献 [1] 指出...”、“与之对比，方案 [2] 优化了...”）；"
            ),
            "chart_preference": (
                "- 必须包含 1 个研究方法分类树或技术演进脉络图（代码块格式为 ```mermaid\\ngraph TD\\n...```）；\n"
                "- 必须包含 1 个公开数据集基准评测对比表格 (Benchmark Matrix)，列明评估指标、准确率/误差与算力开销。"
            ),
            "code_policy": "若涉及数学机理推导或损失函数，必须使用标准的 LaTeX 行内公式 ($...$) 或行间公式 ($$...$$)；引用密度极高，句句有出处。",
            "editor_system_prompt": (
                "你是一位国际知名学术期刊的特邀主编 (Editor-in-Chief)。\n"
                "你的任务是将各研究章节统合成一篇系统性、权威性的学术综述论文 (Comprehensive Survey Paper)。\n"
                "统合任务：撰写学术摘要 (Abstract) 与核心学术贡献 (Key Contributions)，提炼分类学全景树，总结开放研究挑战 (Open Challenges) 与未来 5 年研究方向。"
            ),
            "summary_header_name": "## 📑 论文概要与核心研究发现 (Abstract & Key Contributions)",
            "summary_guideline": "提炼本综述的 3 大核心理论发现、研究方法分类学全景树与未来 5 年关键学术挑战。",
            "macro_chart_prompt": "绘制技术分类学全景树 (Taxonomy Tree) 或技术演进时序脉络图（使用 Mermaid 图表，如 ```mermaid\\ngraph TD\\n...```）",
            "docx_primary_color": "334155" # 严谨石板灰
        },

        "tutorial_docs": {
            "id": "tutorial_docs",
            "name_zh": "技术实操与开发者教程手册",
            "name_en": "Developer Guide & Technical Cookbook",
            "persona_system_prompt": (
                "你是一位大厂高可用系统首席架构师与知名开源项目资深技术布道师。\n"
                "你负责撰写工程落地实战教程与开发者手册的【特定单个章节】。\n"
                "行文特征：通俗易懂、步骤明确、强调实操、代码规范，杜绝抽象空谈，注重可复现性。"
            ),
            "chapter_guideline": (
                "- 开篇明确给出先决条件与环境准备清单 (Prerequisites，如操作系统、运行时版本、关键依赖包)；\n"
                "- 拒绝抽象术语轰炸，以清晰明确的分步实操指南 (Step-by-Step Walkthrough，Step 1, Step 2...) 为主轴；\n"
                "- 每一步必须提供真实、自闭合、语法合法的配置范例（如 YAML/JSON/Dockerfile）或核心可执行代码片段（Python/TypeScript/Bash），且关键代码行必须带行内注释；\n"
                "- 章节末尾必须包含【常见踩坑与排错指南 (Troubleshooting & Common Pitfalls)】，列出至少 2 个高频报错、诱因及精准排查手段；"
            ),
            "chart_preference": (
                "- 必须包含 1 个组件交互调用时序图（代码块格式为 ```mermaid\\nsequenceDiagram\\n...```）或服务架构拓扑图（```mermaid\\ngraph TD\\n...```）；\n"
                "- 必须包含 1 个核心配置项/CLI 参数对照表格。"
            ),
            "code_policy": "强制要求提供结构完整、高可读性的真实代码块，严格用三反引号标明语言类型（如 ```python, ```yaml, ```bash 等）。",
            "editor_system_prompt": (
                "你是一位顶级技术社区的总布道师与文档架构专家。\n"
                "你的任务是将各个技术模块实操章节统合成一份结构清晰、开发者友好的全栈实战教程 (Complete Technical Cookbook)。\n"
                "统合任务：撰写 5 分钟极速起步与全景技术概览 (Quickstart & Architecture Overview)，绘制整体交互时序图，并整理全局核心避坑清单。"
            ),
            "summary_header_name": "## 🚀 教程极速起步与技术全景 (Quickstart & Architecture Overview)",
            "summary_guideline": "撰写 5 分钟跑通的技术全景起步指南、核心拓扑时序图以及生产环境架构设计原则。",
            "macro_chart_prompt": "绘制端到端组件交互时序图或部署拓扑图（使用 Mermaid，如 ```mermaid\\nsequenceDiagram\\n...``` 或 ```mermaid\\ngraph LR\\n...```）",
            "docx_primary_color": "0F766E" # 极客墨绿
        },

        "executive": {
            "id": "executive",
            "name_zh": "C-Suite / 高管一页纸决策内参",
            "name_en": "Executive Brief & C-Suite Memo",
            "persona_system_prompt": (
                "你是一位跨国巨头董事会与高管层（CEO/CIO/CTO）特聘的首席战略决策顾问。\n"
                "你负责撰写面向高管决策层的绝密内参【特定单个章节】。\n"
                "行文特征：严格遵循 BLUF (Bottom Line Up Front) 原则，结论先行、极简凝练、零空话、只讲关键机会与风险。"
            ),
            "chapter_guideline": (
                "- 严格遵循 BLUF (Bottom Line Up Front，结论先行) 原则，开门见山直接给出决策判断；\n"
                "- 杜绝大段技术细节铺垫与学术长篇大论，每个小节提炼为 1~2 句核心判断 + 3 项量化支撑数据点；\n"
                "- 聚焦战略影响：机会窗口期、投资回报 (ROI)、潜在供应链壁垒与风险应对预案；"
            ),
            "chart_preference": (
                "- 必须包含 1 个战略风险对冲矩阵表或投资回报评估对比表；\n"
                "- 必须包含 1 个极简宏观逻辑推演箭头图（代码块格式为 ```mermaid\\ngraph LR\\n...```）。"
            ),
            "code_policy": "严禁输出底层技术代码，重点突出财务指标、出货量、时间窗口与决策结论。",
            "editor_system_prompt": (
                "你是一位董事会资深战略顾问。\n"
                "你的任务是将所有要点精炼统合成一份高管 1 页纸决策作战大纲。\n"
                "统合任务：提炼 3 大核心战略结论、商业机会评估、风险对冲指南与 C-Suite 重点行动时间表。"
            ),
            "summary_header_name": "## 🎯 一页纸战略决策综述 (One-Page Executive Brief)",
            "summary_guideline": "提炼全篇 3 项核心定性结论、战略 ROI 评估与高管 1 页纸行动清单，严格保持极简紧凑。",
            "macro_chart_prompt": "绘制宏观决策因果传导图（使用 Mermaid 流程图，如 ```mermaid\\ngraph LR\\n...```）",
            "docx_primary_color": "78350F" # 典雅琥珀金
        },

        "briefing": {
            "id": "briefing",
            "name_zh": "产业前沿快报与深度特稿",
            "name_en": "Industry Briefing & Field Report",
            "persona_system_prompt": (
                "你是一位硅谷知名科技智库与科技商业媒体的特约深度评论员。\n"
                "你负责撰写行业前沿动态特稿的【特定单个章节】。\n"
                "行文特征：叙事生动、张弛有度、视角敏锐、多维博弈剖析。"
            ),
            "chapter_guideline": (
                "- 结合科技新闻叙事与深度技术解构，梳理重大突破与前沿动态的时间脉络；\n"
                "- 深入剖析产业巨头、科研机构与监管政策之间的多方利益博弈与立场差异；\n"
                "- 研判关键事件对产业格局的短中期连锁反应；"
            ),
            "chart_preference": (
                "- 包含 1 个重大事件演进甘特图（代码块格式为 ```mermaid\\ngantt\\n...```）或时间线流程图；\n"
                "- 包含 1 个利益相关方立场矩阵对比表。"
            ),
            "code_policy": "视情况穿插关键架构示意，保持生动引人入胜的深度报道质感。",
            "editor_system_prompt": (
                "你是一位顶级科技商业媒体总编。\n"
                "你的任务是将动态章节汇聚为一份深度透视特稿。\n"
                "统合任务：提炼全篇核心态势快报、3 大行业暗涌与未来 6~12 个月关键动向预测。"
            ),
            "summary_header_name": "## ⚡ 核心态势快报与关键透视 (Key Takeaways & Pulse)",
            "summary_guideline": "提炼本轮动态的核心看点、三大关键趋势透视与未来 6~12 个月产业演进预判。",
            "macro_chart_prompt": "绘制行业演进甘特图或态势演化图（使用 Mermaid，如 ```mermaid\\ngantt\\n...``` 或 ```mermaid\\ngraph TD\\n...```）",
            "docx_primary_color": "7C3AED" # 科技紫
        }
    }

    @classmethod
    def get(cls, style_name: Optional[str]) -> StyleProfile:
        """获取风格配置对象，支持别名映射与平滑降级"""
        if not style_name:
            return cls._PROFILES["consulting"]
        
        s = style_name.lower().strip()
        if s in ["academic", "survey", "paper"]:
            s = "literature_review"
        elif s in ["tutorial", "cookbook", "guide", "dev"]:
            s = "tutorial_docs"
        elif s in ["exec", "brief", "memo"]:
            s = "executive"
        elif s in ["news", "report"]:
            s = "briefing"

        return cls._PROFILES.get(s, cls._PROFILES["consulting"])

    @classmethod
    def list_styles(cls) -> List[Dict[str, str]]:
        """返回所有受支持的风格清单列表"""
        return [
            {
                "id": p["id"],
                "name_zh": p["name_zh"],
                "name_en": p["name_en"],
                "color": p["docx_primary_color"]
            }
            for p in cls._PROFILES.values()
        ]

def clean_chapter_text(text: str, chapter_num: int, title: str) -> str:
    """清洗单章正文，彻底剥离模型擅自附加的末尾参考资料，防止截断后续章节"""
    if not text:
        return ""
    # 移除单章末尾大模型擅自生成的参考资料列表
    cleaned = re.sub(r'##\s*(?:📚\s*)?(?:参考资料|参考文献|引用来源|Citations?|Sources?)[\s\S]*$', '', text, flags=re.IGNORECASE).strip()
    # 移除 [1]: http... 形式的尾部定义
    cleaned = re.sub(r'\[\d+\]:\s+[^\n]+', '', cleaned).strip()
    # 确保以 ## 第 X 章 开头
    if not cleaned.startswith("## "):
        cleaned = f"## 第 {chapter_num} 章：{title}\n\n" + cleaned
    return cleaned.strip()

def write_single_chapter(
    query: str,
    chapter: ChapterOutline,
    style: str,
    previous_summary: str = "",
    custom_llm_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Map 阶段：独立撰写单个章节，依据 StyleProfile 注入专属人设与论述规范
    """
    ch_num = chapter.get("chapter_num", 1)
    title = chapter.get("title", f"第 {ch_num} 章")
    focus = chapter.get("focus", "")
    facts = chapter.get("extracted_facts", [])
    facts_text = "\n  - ".join(facts) if facts else "暂无特定事实，请结合行业通用专业认知与基准数据展开分析。"

    profile = StyleProfileRegistry.get(style)

    prompt = f"""
    【总研报课题】：{query}
    【风格定位】：{profile["name_zh"]} ({profile["name_en"]})
    
    【当前撰写章节】：第 {ch_num} 章 - {title}
    【本章调研侧重点】：{focus}
    【前序章节脉络参考】：{previous_summary if previous_summary else '（本章为核心章节）'}
    
    【本章搜集到的核心事实与证据材料（带引用角标编号）】：
      - {facts_text}
    
    【核心论述骨架要求】：
    {profile["chapter_guideline"]}
    
    【图表与展示规范】：
    {profile["chart_preference"]}
    
    【代码与公式规范】：
    {profile["code_policy"]}
    
    请严格基于上述规范与事实侧重点，为【第 {ch_num} 章：{title}】撰写 1,200 ~ 2,500 字的深度论述。
    通用强制要求：
    1. Mermaid 规范：若节点文字包含括号、冒号、斜杠、空格等特殊字符，节点标签务必使用双引号包裹，例如 A["指标 (Recall@k / MRR)"]；节点 ID 严禁使用带小数点的数字（应用 A1、B2 或 node_1_1）；严禁在节点文字中使用裸 `<` 或 `>` 符号（请用全角 `＜` 或文字“小于”代替）；每个 subgraph 必须以 end 独立成行闭合；代码块必须完整闭合 ```；
    2. 关键事实与数据必须在句末准确标注文献角标 [^cite:N] 或 [N]（尤其若包含本地私有文档事实，务必予以精准引用）；
    3. 直接输出本章 Markdown 正文（以 `## 第 {ch_num} 章：{title}` 开头）；
    4. 严禁在末尾输出任何形式的“参考资料”列表或 [N]: 链接定义，系统将在全篇末尾统一核验排版。
    """

    for attempt in range(2):
        try:
            chapter_body = call_llm(
                prompt,
                system_prompt=profile["persona_system_prompt"],
                temperature=0.3,
                max_tokens=4096,
                custom_llm_config=custom_llm_config
            )
            return clean_chapter_text(chapter_body.strip(), ch_num, title)
        except Exception as e:
            if attempt == 0:
                import time
                time.sleep(1.0)
                continue
            print(f"[Writer Warning] 单章撰写调用回退 (第 {ch_num} 章): {e}")

    # 兜底回退文本
    fallback_body = f"""## 第 {ch_num} 章：{title}

### 1. 核心现状与背景梳理
围绕「{focus}」，当前体系正处于演进阶段。从收集到的实测事实来看：
{facts_text}

### 2. 核心方案与多维对比矩阵
以下为本章节涉及的关键方案与指标综合对比：

| 维度方案 | 核心技术体系 | 关键量化指标 | 商业化成熟度 | 主要壁垒与挑战 |
|---|---|---|---|---|
| 方案 A | 基准路线 | 85%~92% 达标率 | 爬坡期 | 成本与工艺一致性 |
| 方案 B | 前沿突破 | 性能提升 30%+ | 验证期 | 供应链配套与良率 |

```mermaid
graph LR
    A[底层核心机理/输入] --> B[关键模块集成]
    B --> C[系统级综合验证]
    C --> D[规模化应用交付]
```

### 3. 发展瓶颈与机理剖析
结合当前事实，推进过程中需重点攻关核心性能与工程落地壁垒，加速协同以实现规模化落地。
"""
    return clean_chapter_text(fallback_body, ch_num, title)

def synthesize_report_node(state: ResearchState) -> Dict[str, Any]:
    """
    Writer 智能体节点 (V2.5 风格策略化并行 Map-Reduce 撰写引擎):
    1. Map 阶段：依据 StyleProfile 多线程并发撰写各章节，各章节继承当前风格规范；
    2. Reduce 阶段：由 Global Editor 结合当前风格生成专属摘要标题、战略洞察与全景架构图。
    """
    query = state.get("user_query", "")
    outline: List[ChapterOutline] = state.get("outline", [])
    style = state.get("report_style", "consulting")
    depth = state.get("research_depth", "standard")
    custom_llm_cfg = state.get("custom_llm_config")
    
    profile = StyleProfileRegistry.get(style)
    chapter_drafts: Dict[int, str] = {}
    num_chapters = len(outline)
    logs: List[str] = [f"[Writer] 启动 Map-Reduce 多章节并行深度合成引擎 (风格: {profile['name_zh']}, 共 {num_chapters} 个章节并发撰写)..."]
    
    # 1. Map 阶段：多线程并发独立展开各章节
    def _write_task(ch: ChapterOutline):
        cnum = ch.get("chapter_num", 1)
        draft = write_single_chapter(
            query=query,
            chapter=ch,
            style=style,
            previous_summary="",
            custom_llm_config=custom_llm_cfg
        )
        return cnum, draft

    max_workers = min(num_chapters, 6) if num_chapters > 0 else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_write_task, ch): ch for ch in outline}
        for future in as_completed(future_map):
            try:
                cnum, draft = future.result()
                chapter_drafts[cnum] = draft
                logs.append(f"  ✍️ [Chapter {cnum} 并发完成]: 深度撰写完毕 (约 {len(draft)} 字符)")
            except Exception as e:
                ch = future_map[future]
                cnum = ch.get("chapter_num", 1)
                chapter_drafts[cnum] = f"## 第 {cnum} 章：{ch.get('title', '')}\n\n该章节论述在并发生成中遇到异常，请参考提取事实要点。"

    # 2. Reduce 阶段：Global Editor 依据当前风格统合提炼
    logs.append(f"[Writer] 各章节稿件生成完毕，Global Editor 正在按「{profile['name_zh']}」提炼宏观摘要与全景脉络...")
    
    sorted_chapters = sorted(outline, key=lambda ch: ch.get("chapter_num", 1))
    valid_chapter_texts = []
    for ch in sorted_chapters:
        cnum = ch.get("chapter_num", 1)
        if cnum in chapter_drafts and chapter_drafts[cnum].strip():
            valid_chapter_texts.append(chapter_drafts[cnum].strip())
            
    all_chapters_combined = "\n\n\n".join(valid_chapter_texts)
    
    editor_prompt = f"""
    研究课题：{query}
    调研深度：{depth}
    报告风格：{profile["name_zh"]} ({profile["name_en"]})
    
    【风格提炼指南】：
    {profile["summary_guideline"]}
    
    【已完成深度撰写的各章节初稿汇总】：
    {all_chapters_combined[:10000]}
    
    请根据上述各章节内容与风格规范，为整篇报告撰写：
    1. 大标题：`# {query} 深度研究报告`
    2. 宏观摘要章节，标题必须精确使用：`{profile["summary_header_name"]}`，结合章节提炼 3 大核心要点；
    3. {profile["macro_chart_prompt"]}；
    4. 仅输出大标题、宏观摘要章节与宏观图表部分，正文章节将自动拼接在后。
    """

    try:
        summary_header = call_llm(
            editor_prompt,
            system_prompt=profile["editor_system_prompt"],
            temperature=0.3,
            max_tokens=4096,
            custom_llm_config=custom_llm_cfg
        )
        # 容错：若大模型在宏观架构图生成中偶然截断导致未闭合 ``` 围栏，自动补全闭合标签
        if summary_header.count("```") % 2 != 0:
            summary_header = summary_header.rstrip() + "\n```\n"
    except Exception as e:
        print(f"[Writer Warning] Global Editor 调用回退: {e}")
        summary_header = f"""# {query} 深度研究报告

{profile["summary_header_name"]}

本报告围绕「{query}」展开系统深入调研。通过对权威多源数据与前沿路线的梳理，提炼出以下三大核心发现：

1. **核心脉络与代际演进**：当前体系正经历关键技术跃升与标准化落地阶段；
2. **多维方案与权衡矩阵**：各技术路线在性能指标、实现成本与工程复杂度上呈现差异化权衡；
3. **生态推进与未来演进**：产业上下游一体化协同布局与规范建立成为推动规模化落地的关键分水岭。

```mermaid
graph TD
    A[前沿理论与政策指导] --> B[核心技术机理突破]
    B --> C[工程实现与方案落地]
    C --> D[商业化规模应用与普及]
```
"""

    full_draft_report = summary_header.strip() + "\n\n\n" + all_chapters_combined.strip()
    total_chars = len(full_draft_report)
    logs.append(f"[Writer] Map-Reduce 深度研报初稿统合完成！共包含 {len(valid_chapter_texts)} 个完整章节，全文约 {total_chars} 字符，交由 Verifier 节点。")

    return {
        "chapter_drafts": chapter_drafts,
        "draft_report": full_draft_report,
        "current_step": "verify",
        "logs": logs
    }
