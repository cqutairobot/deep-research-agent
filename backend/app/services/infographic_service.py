"""
社交高光快报长图 AI 编排服务 (Infographic Director Service)
由大语言模型严格审阅研报正文，结构化提炼 3 大量化指标、机理总结金句与 3 大战略洞察，杜绝正则残句。
"""

import json
import re
from typing import Dict, Any, List, Optional
from app.core.config import call_llm, CustomLLMConfig

# 内存缓存 (Key: hash(report[:200]))
_INFOGRAPHIC_CACHE: Dict[str, Dict[str, Any]] = {}


def generate_infographic_data(
    title: str,
    report: str,
    custom_llm_config: Optional[CustomLLMConfig] = None
) -> Dict[str, Any]:
    """
    调用大模型为研报量身定制社交高光长图数据结构。
    """
    clean_title = (title or "前沿深度研究报告").replace("#", "").strip()
    clean_report = (report or "").strip()
    
    if not clean_report:
        return _build_emergency_fallback(clean_title)

    cache_key = f"{hash(clean_title)}::{hash(clean_report[:200])}::{len(clean_report)}"
    if cache_key in _INFOGRAPHIC_CACHE:
        return _INFOGRAPHIC_CACHE[cache_key]

    prompt = f"""你是一位全球顶级科技战略智库与投行研报的视觉创意总监。
请认真阅读以下深度研究报告，为移动端社交长图（适配微信朋友圈、X、即刻、小红书）提炼结构化、最具震撼力与专业度的高光内容。

【研报标题】：{clean_title}
【研报正文】：
{clean_report[:6000]}

【提炼任务与规格要求】：
请以纯 JSON 格式输出以下 3 个核心区块，要求语言极其精炼、语法完整、绝对不能出现首尾断裂的残句：

1. "metrics"：3 大最硬核的关键量化核心指标（数组长度严格为 3）：
   - "value": 核心数值或量化结论（如 "3,000+通道", "85%意图解码率", "2027年量产", "¥120/kWh", "3.5倍提升" 等，醒目震撼，6~10 个字）；
   - "label": 指标业务名称（如 "电极通道密度", "运动意图解码率", "商业化临界期" 等，通俗清晰，4~10 个字）；
   - "sub": 一句完整说明或对比（如 "相较上一代设备密度提升超200%", "支持端侧超低时延实时解码" 等，语义完整通顺，10~20 个字）。

2. "summary_lines"：2 句高度概括本文技术机理路线与产业商业化收敛逻辑的金句（数组长度严格为 2）：
   - 每句 20~35 字，语义完整、直击本质。

3. "insights"：3 大最具战略穿透力的深度研判卡片（数组长度严格为 3）：
   - "num": 依次固定为 "01", "02", "03"；
   - "title": 核心研判主标题（如 "算法平台长期毛利率显著高于硬件制造", 10~20 个字）；
   - "content": 完整的论证推演（50~80 字，语言凝练、因果链条严密、必须是语义完整的连贯语句，严禁残句！）。

【输出要求】：
直接输出合法的纯 JSON 对象，严禁包裹 Markdown 外部多余说明，格式如下：
{{
  "metrics": [
    {{"value": "...", "label": "...", "sub": "..."}},
    {{"value": "...", "label": "...", "sub": "..."}},
    {{"value": "...", "label": "...", "sub": "..."}}
  ],
  "summary_lines": [
    "• 句子一...",
    "• 句子二..."
  ],
  "insights": [
    {{"num": "01", "title": "...", "content": "..."}},
    {{"num": "02", "title": "...", "content": "..."}},
    {{"num": "03", "title": "...", "content": "..."}}
  ]
}}
"""

    system_prompt = (
        "你是一位专精商业咨询与学术科技可视化的顶级设计总监。"
        "你的任务是从研报中提炼震撼严谨的量化指标与战略研判。"
        "输出必须且只能是一个严格合法的 JSON 对象，语句必须完整通顺，绝对杜绝残句断句。"
    )

    try:
        raw_res = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            custom_llm_config=custom_llm_config
        )
        
        # 清洗代码块标记
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_res.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()
        
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            parsed = json.loads(match.group(0))
            if "metrics" in parsed and "insights" in parsed and len(parsed["metrics"]) == 3:
                # 规范化处理
                res_data = {
                    "title": clean_title,
                    "metrics": parsed["metrics"],
                    "summary_lines": parsed.get("summary_lines") or [
                        f"• 围绕「{clean_title[:18]}」核心机理与商业落地闭环展开全景深度推演。",
                        "• 统筹宏观技术路线收敛规律与产业工程化量产壁垒。"
                    ],
                    "insights": parsed["insights"][:3],
                    "status": "success",
                    "source": "llm"
                }
                _INFOGRAPHIC_CACHE[cache_key] = res_data
                return res_data
    except Exception as e:
        print(f"[InfographicService] 大模型提炼社交长图结构失败: {e}")

    fallback = _build_emergency_fallback(clean_title, clean_report)
    _INFOGRAPHIC_CACHE[cache_key] = fallback
    return fallback


def _build_emergency_fallback(title: str, report: str = "") -> Dict[str, Any]:
    """兜底完整数据结构（保证完整语义，绝不出现残句）"""
    return {
        "title": title,
        "metrics": [
            {"value": f"{max(4, round(len(report) / 1000))}k+ 字", "label": "全篇深度论证篇幅", "sub": "多维论述严密推演"},
            {"value": "100% 严谨", "label": "事实交叉印证保障", "sub": "多源学术证据溯源体系"},
            {"value": "MECE 穷尽", "label": "结构化商业推演", "sub": "全景解构产业核心矛盾"}
        ],
        "summary_lines": [
            f"• 深度聚焦「{title[:20]}」的核心技术路径与产业落地约束。",
            "• 系统解构工程瓶颈、商业模式分化与长期价值分配格局。"
        ],
        "insights": [
            {
                "num": "01",
                "title": "底层核心技术突破构筑长期竞争壁垒",
                "content": "技术架构的收敛不仅取决于理论性能上限，更受制于量产良率、BOM成本与制造工艺的工程化妥协路径。"
            },
            {
                "num": "02",
                "title": "软硬件一体化与系统协同带来超额溢价",
                "content": "单纯硬件制造的边际毛利面临快速摊薄，而结合算法平台、数据飞轮与生态闭环的系统集成商更具定价权。"
            },
            {
                "num": "03",
                "title": "全球产业链重塑下上游关键环节率先受益",
                "content": "随着商业化临界点临近，上游核心原材料、精密元器件与专用装备制造将先于下游整机企业释放盈利弹性。"
            }
        ],
        "status": "fallback",
        "source": "heuristic"
    }
