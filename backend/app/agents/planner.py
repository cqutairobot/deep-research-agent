import json
import re
from typing import Dict, Any, List
from app.agents.state import ResearchState, ChapterOutline
from app.core.config import call_llm

PLANNER_SYSTEM_PROMPT = """你是一位顶级的首席战略分析师与前沿智库研究规划专家。
你的任务是将用户的研究课题拆解为逻辑严密、层层递进的专业调研大纲，并为每个章节设计 2 个高命中率的针对性检索词。

大纲规划原则：
1. 根据研究深度的不同，自主规划最科学合理的章节数量：
   - 快速概览 (quick)：拆解 2~3 个最核心、最具代表性的关键章节；
   - 标准调研 (standard)：拆解 3~5 个层层递进的系统性章节；
   - 穷尽研报 (deep)：拆解 5~8 个全景深度章节（涵盖技术原理解析、核心参数对比、全球竞争格局、产业链上下游、代表厂商案例、商业化瓶颈与未来趋势）。
2. 各章节之间逻辑层层递进，杜绝同质化或空洞大话。
3. 输出必须严格为合法的 JSON 格式。

输出 JSON 格式模板：
{
  "clarification": "用一句话阐述本次调研的核心边界、行业语境与价值主张",
  "outline": [
    {
      "chapter_num": 1,
      "title": "章节标题（简练专业）",
      "focus": "本章重点需要查证的核心事实、数据指标与实体对象",
      "search_queries": ["精确检索词1", "精确检索词2"]
    }
  ]
}
"""

def plan_outline_node(state: ResearchState) -> Dict[str, Any]:
    """
    Planner 智能体节点：根据课题领域、深度模式以及目标风格策略，自主规划 2~8 个章节大纲
    """
    query = state.get("user_query", "")
    depth = state.get("research_depth", "standard")
    style = state.get("report_style", "consulting").lower().strip()
    custom_llm_cfg = state.get("custom_llm_config")
    
    if depth == "quick":
        depth_instruction = "当前为【快速概览】模式，请提炼 2~3 个最聚焦的核心章节。"
    elif depth == "deep":
        depth_instruction = "当前为【穷尽深度】模式，请多维度展开，规划 5~8 个详尽深度的章节大纲。"
    else:
        depth_instruction = "当前为【标准调研】模式，请系统拆解 3~5 个具有递进洞察价值的章节大纲。"

    # 风格指导原则
    if style in ["literature_review", "academic", "survey", "paper"]:
        style_instruction = (
            "【学术综述风格】：请按照科研顶刊综述结构规划：第一章为概念界定与理论演进脉络，"
            "中间章节必须建立方法学分类学(Taxonomy)并横评主流路线与假设，后续章节聚焦公开基准评测指标与尚未解决的开放性挑战(Open Challenges)。"
        )
    elif style in ["tutorial_docs", "tutorial", "cookbook", "guide"]:
        style_instruction = (
            "【开发者实操教程风格】：请按照工程落操指南结构规划：第一章必须为先决条件与开发运行环境准备(Prerequisites)，"
            "中间章节为主轴功能模块的分步实操与可运行代码范例，末章为生产环境架构优化与常见踩坑排错指南(Troubleshooting)。"
        )
    elif style in ["executive", "brief", "memo"]:
        style_instruction = (
            "【C-Suite 高管内参风格】：请按照董事会战略决策结构规划：第一章为技术成熟度与商业拐点研判，"
            "中间章节为主流方案权衡与市场空间测算，末章为战略投资回报(ROI)与风险对冲行动建议。"
        )
    elif style in ["briefing", "news", "report"]:
        style_instruction = (
            "【前沿特稿风格】：请按照科技深度新闻叙事规划：第一章为重大突破起因与演进时间轴，"
            "中间章节为产业巨头与多方利益博弈立场，末章为未来 6~12 个月行业连锁反应预测。"
        )
    else:
        style_instruction = (
            "【商业咨询风格】：请按照 MECE 咨询体系规划：第一章为核心技术机理与现状基准，"
            "中间章节为头部厂商方案对比与产业链传导，末章为商业落地瓶颈与未来趋势展望。"
        )

    prompt = f"""
    研究课题：{query}
    调研深度：{depth}
    
    【深度规划指引】：{depth_instruction}
    【风格组织原则】：{style_instruction}
    
    请针对上述课题，紧密结合指定的【风格组织原则】，自主规划最贴合该专业风格的章节大纲及针对性检索词。
    """
    
    try:
        llm_output = call_llm(
            prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            temperature=0.2,
            custom_llm_config=custom_llm_cfg
        )
        parsed = _parse_planner_json(llm_output)
    except Exception as e:
        print(f"[Planner Warning] JSON parse fallback: {e}")
        if style in ["literature_review", "academic"]:
            default_outline = [
                {"chapter_num": 1, "title": "理论演进与核心概念界定", "focus": "梳理学术研究脉络、理论边界与核心定义", "search_queries": [f"{query} 理论演进", f"{query} 概念界定"]},
                {"chapter_num": 2, "title": "主流技术路线与方法分类学 (Taxonomy)", "focus": "建立技术分类学树，对比各路线理论假设与性能权衡", "search_queries": [f"{query} 方法分类学", f"{query} 技术路线对比"]},
                {"chapter_num": 3, "title": "基准测试评估与开放研究挑战 (Open Challenges)", "focus": "分析主流基准指标、局限性与未来研究方向", "search_queries": [f"{query} 基准评测", f"{query} 开放挑战"]}
            ]
        elif style in ["tutorial_docs", "tutorial"]:
            default_outline = [
                {"chapter_num": 1, "title": "先决条件与运行环境准备 (Prerequisites)", "focus": "梳理系统依赖、安装配置与前置架构要求", "search_queries": [f"{query} 环境准备", f"{query} 安装配置"]},
                {"chapter_num": 2, "title": "核心模块分步实现与代码示例 (Step-by-Step)", "focus": "拆解实现步骤，提供可运行的核心代码片段与配置范例", "search_queries": [f"{query} 实操步骤", f"{query} 代码范例"]},
                {"chapter_num": 3, "title": "生产部署优化与常见排错指南 (Troubleshooting)", "focus": "总结生产最佳实践、常见踩坑与精准排查方案", "search_queries": [f"{query} 最佳实践", f"{query} 常见报错 解决"]}
            ]
        else:
            default_outline = [
                {"chapter_num": 1, "title": "核心概念与技术现状梳理", "focus": "梳理定义、核心指标与现状基准", "search_queries": [f"{query} 技术现状", f"{query} 核心指标"]},
                {"chapter_num": 2, "title": "市场竞争格局与主要厂商对比", "focus": "梳理头部厂商方案、市场份额与量产进展", "search_queries": [f"{query} 厂商对比", f"{query} 量产进展"]},
                {"chapter_num": 3, "title": "商业化瓶颈与未来趋势展望", "focus": "分析成本、供应链瓶颈及未来演进路径", "search_queries": [f"{query} 痛点 挑战", f"{query} 发展趋势"]}
            ]
        parsed = {
            "clarification": f"系统将围绕「{query}」展开多维度专业调研与深度论证。",
            "outline": default_outline
        }
    
    outline_data: List[ChapterOutline] = []
    for item in parsed.get("outline", []):
        outline_data.append({
            "chapter_num": item.get("chapter_num", len(outline_data) + 1),
            "title": item.get("title", f"第 {len(outline_data) + 1} 章"),
            "focus": item.get("focus", "重点事实查证"),
            "search_queries": item.get("search_queries", [item.get("title", query)]),
            "extracted_facts": []
        })

    clarification = parsed.get("clarification", f"围绕「{query}」展开深度研究。")
    log_msg = f"[Planner] 大模型分析完成：根据「{depth}」深度与「{style}」风格自主规划了 {len(outline_data)} 个专业章节维度。"

    return {
        "outline": outline_data,
        "clarification": clarification,
        "current_step": "research",
        "logs": [log_msg]
    }

def _parse_planner_json(text: str) -> Dict[str, Any]:
    """解析大纲 JSON 输出"""
    try:
        clean = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
        clean = re.sub(r'```$', '', clean.strip(), flags=re.MULTILINE)
        return json.loads(clean.strip())
    except Exception:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    raise ValueError("无法解析 Planner 返回的大纲 JSON 数据")
