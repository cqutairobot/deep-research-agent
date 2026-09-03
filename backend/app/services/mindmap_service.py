"""
因果机制与方案权衡知识图谱思维导图服务 (Causal & Tradeoff Mindmap Service)
利用大语言模型深入研报论据，提炼因果推演拓扑链、矛盾张力与技术方案权衡 (Trade-offs)。
输出标准 Mermaid 语法拓扑及结构化图谱节点。
"""

import re
import json
from typing import Dict, Any, List, Optional
from app.core.config import call_llm, CustomLLMConfig

_MINDMAP_CACHE: Dict[str, Dict[str, Any]] = {}


def generate_causal_mindmap(
    title: str,
    report: str,
    custom_llm_config: Optional[CustomLLMConfig] = None
) -> Dict[str, Any]:
    """
    大模型深入全篇研报，提炼因果机制与方案权衡知识图谱。
    """
    clean_title = (title or "前沿研报").replace("#", "").strip()
    clean_report = (report or "").strip()

    cache_key = f"{hash(clean_title)}::{hash(clean_report[:250])}::{len(clean_report)}"
    if cache_key in _MINDMAP_CACHE:
        return _MINDMAP_CACHE[cache_key]

    system_prompt = (
        "你是一位顶级系统架构师与科技智库首席科学家。"
        "你的任务是深入阅读研报，彻底跳出简单按章节标题列大纲的低幼形式，"
        "提炼出真正反映事物底层物理/工程因果传导机制、核心矛盾与技术权衡 (Trade-offs) 的【因果推演知识图谱】。"
        "输出必须且只能是一个严格合法的纯 JSON 对象，绝不能包含任何 Markdown 代码块外的文字。"
    )

    prompt = f"""请深入阅读以下研究报告，提取其因果推演脉络与技术方案权衡矩阵。

【研究课题】：{clean_title}
【研报精选正文】：
{clean_report[:6000]}

【抽取要求】：
1. 提炼出核心命题、2~3 条主要路线/分支、关键矛盾、技术权衡点 (Trade-offs) 与终局收敛解；
2. 输出一段严格合法的 Mermaid graph LR 代码（注意：节点文本不要使用括号或特殊符号，尽量用双引号包裹如 id["文字"]，避免语法错误）；
3. 输出结构化 nodes 与 edges 列表；
4. 必须输出以下纯 JSON 结构：
{{
  "title": "{clean_title}",
  "summary": "一句话概括本课题核心机理因果链条与终极权衡矛盾",
  "mermaid_code": "graph LR\\n    A[\\"课题核心矛盾\\"] -->|导致| B[\\"路线A\\"]\\n    ...",
  "nodes": [
    {{"id": "A", "label": "核心问题", "type": "challenge", "detail": "具体说明"}},
    {{"id": "B", "label": "技术分歧点", "type": "tradeoff", "detail": "具体说明"}}
  ],
  "edges": [
    {{"from": "A", "to": "B", "relation": "causes", "label": "制约"}}
  ]
}}
"""

    try:
        raw_res = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            custom_llm_config=custom_llm_config
        )

        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_res.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            parsed = json.loads(match.group(0))
            if "mermaid_code" in parsed and "nodes" in parsed and len(parsed["nodes"]) >= 4:
                parsed["status"] = "success"
                parsed["source"] = "llm"
                _MINDMAP_CACHE[cache_key] = parsed
                return parsed
    except Exception as e:
        print(f"[MindmapService] 大模型提炼因果图谱失败: {e}")

    fallback = _build_fallback_mindmap(clean_title, clean_report)
    _MINDMAP_CACHE[cache_key] = fallback
    return fallback


def _build_fallback_mindmap(title: str, report: str) -> Dict[str, Any]:
    """生成稳健的兜底因果拓扑脑图"""
    safe_t = title[:16].replace('"', '')
    mermaid_code = f"""graph LR
    Core["{safe_t} 核心命题"] -->|底层约束| Bottleneck["物理/工艺工程瓶颈"]
    Core -->|市场驱动| Demand["产业商业化窗口期"]
    
    Bottleneck -->|路线分歧| RouteA["前沿主流技术路线"]
    Bottleneck -->|路线分歧| RouteB["颠覆性替代路线"]
    
    RouteA -->|权衡张力| Tradeoff1["性能上限 vs BOM量产成本"]
    RouteB -->|权衡张力| Tradeoff2["理论优势 vs 产业链成熟度"]
    
    Tradeoff1 -->|技术破局| Sol1["工艺良率优化与关键材料降本"]
    Tradeoff2 -->|协同演进| Sol2["系统级软硬件融合与生态闭环"]
    
    Demand -->|终局收敛| Convergence["规模化临界点与马太效应"]
    Sol1 --> Convergence
    Sol2 --> Convergence
"""

    nodes = [
        {"id": "Core", "label": f"{safe_t} 核心命题", "type": "challenge", "detail": "产业面临的核心问题与技术演进方向"},
        {"id": "Bottleneck", "label": "物理/工艺工程瓶颈", "type": "challenge", "detail": "制造良率、原材料及系统集成物理约束"},
        {"id": "Demand", "label": "产业商业化窗口期", "type": "metric", "detail": "下游应用需求爆发与渗透率拐点"},
        {"id": "RouteA", "label": "前沿主流技术路线", "type": "route", "detail": "成熟度较高但面临边际递减的渐进路径"},
        {"id": "RouteB", "label": "颠覆性替代路线", "type": "route", "detail": "理论空间巨大但工程壁垒森严的新架构"},
        {"id": "Tradeoff1", "label": "性能上限 vs BOM量产成本", "type": "tradeoff", "detail": "单体性能与规模经济性之间的核心博弈"},
        {"id": "Tradeoff2", "label": "理论优势 vs 产业链成熟度", "type": "tradeoff", "detail": "实验室极佳指标与上下游配套匮乏的矛盾"},
        {"id": "Sol1", "label": "工艺良率优化与关键材料降本", "type": "solution", "detail": "中游制造工艺收敛与制造装备自主可控"},
        {"id": "Sol2", "label": "系统级软硬件融合与生态闭环", "type": "solution", "detail": "向算法、系统集成与数据飞轮寻找超额毛利"},
        {"id": "Convergence", "label": "规模化临界点与马太效应", "type": "convergence", "detail": "技术路线定型后头部企业确立长期定价壁垒"}
    ]

    edges = [
        {"from": "Core", "to": "Bottleneck", "relation": "causes", "label": "底层约束"},
        {"from": "Core", "to": "Demand", "relation": "causes", "label": "市场驱动"},
        {"from": "Bottleneck", "to": "RouteA", "relation": "branches", "label": "路线分歧"},
        {"from": "Bottleneck", "to": "RouteB", "relation": "branches", "label": "路线分歧"},
        {"from": "RouteA", "to": "Tradeoff1", "relation": "tradeoff", "label": "权衡张力"},
        {"from": "RouteB", "to": "Tradeoff2", "relation": "tradeoff", "label": "权衡张力"},
        {"from": "Tradeoff1", "to": "Sol1", "relation": "solves", "label": "技术破局"},
        {"from": "Tradeoff2", "to": "Sol2", "relation": "solves", "label": "协同演进"},
        {"from": "Demand", "to": "Convergence", "relation": "converges", "label": "终局收敛"},
        {"from": "Sol1", "to": "Convergence", "relation": "converges", "label": "终局收敛"},
        {"from": "Sol2", "to": "Convergence", "relation": "converges", "label": "终局收敛"}
    ]

    return {
        "title": title,
        "summary": f"系统解构「{safe_t}」从底层物理约束、路线分化、方案权衡到商业终局收敛的因果演进全景图。",
        "mermaid_code": mermaid_code,
        "nodes": nodes,
        "edges": edges,
        "status": "fallback",
        "source": "heuristic"
    }
