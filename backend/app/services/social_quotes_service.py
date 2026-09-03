"""
社交媒体爆款金句与多平台文案生成服务 (Social Quotes Service)
提炼颠覆性认知金句、量化预判与落地建议，并自适应适配 𝕏/Twitter、即刻/朋友圈、小红书三大平台发布排版。
"""

import re
import json
from typing import Dict, Any, List, Optional
from app.core.config import call_llm, CustomLLMConfig

_QUOTES_CACHE: Dict[str, Dict[str, Any]] = {}


def generate_social_quotes(
    title: str,
    report: str,
    custom_llm_config: Optional[CustomLLMConfig] = None
) -> Dict[str, Any]:
    """
    为研报提炼社交传播爆款金句与跨平台文案卡片。
    """
    clean_title = (title or "前沿研报").replace("#", "").strip()
    clean_report = (report or "").strip()

    cache_key = f"{hash(clean_title)}::{hash(clean_report[:200])}::{len(clean_report)}"
    if cache_key in _QUOTES_CACHE:
        return _QUOTES_CACHE[cache_key]

    system_prompt = (
        "你是一位专精科技与商业产业传播的顶级自媒体总编与内容极客。"
        "你的职责是从一份严肃高密度的专业万字研报中，精准提炼最具穿透力、颠覆认知的爆款社交金句与多渠道文案。"
        "要求观点犀利、逻辑严密、兼具专业度与病毒式传播力。"
        "输出必须且只能是一个严格合法的纯 JSON 对象，绝不能包含外部 Markdown 说明。"
    )

    prompt = f"""请仔细阅读以下深度研报，提炼爆款社交金句与跨平台发布文案。

【研报标题】：{clean_title}
【研报精选要点】：
{clean_report[:5000]}

【输出字段规范】：
请直接输出如下 JSON 格式：
{{
  "title": "{clean_title}",
  "punchline": "1 句颠覆常规认知的核心洞见金句（25~45 字，字字珠玑，发人深省）",
  "predictions": [
    "预判 1：关于技术路线演进的关键量化时间节点或突破",
    "预判 2：关于商业化落地、成本或市场规模的关键测算",
    "预判 3：关于产业链格局重塑或淘汰赛的关键研判"
  ],
  "action_advice": "1 句面向从业者或投资人的明确行动策略建议（20~35 字）",
  "platforms": {{
    "twitter_thread": "适合 X (Twitter) 发布的 Thread 格式文案（包含 1/3、2/3、3/3 编号与标签）",
    "jike_post": "适合即刻与微信朋友圈发布的极客风干货动态（带精炼 Emoji 与排版）",
    "xiaohongshu": "适合小红书发布的图文笔记文案（带吸引眼球的标题、重点高亮与热门标签）"
  }}
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
            if "punchline" in parsed and "predictions" in parsed and "platforms" in parsed:
                parsed["status"] = "success"
                parsed["source"] = "llm"
                _QUOTES_CACHE[cache_key] = parsed
                return parsed
    except Exception as e:
        print(f"[SocialQuotesService] 大模型提炼社交金句失败: {e}")

    fallback = _build_fallback_quotes(clean_title, clean_report)
    _QUOTES_CACHE[cache_key] = fallback
    return fallback


def _build_fallback_quotes(title: str, report: str) -> Dict[str, Any]:
    """保底社交金句与文案"""
    t_short = title[:20]
    punchline = f"「{t_short}」的竞争本质不是参数军备竞赛，而是量产良率、BOM成本与软硬一体生态的工程化收敛。"
    predictions = [
        "2026-2027年将迎来首个商业化拐点，单体成本有望实现 40% 以上的阶跃式下探。",
        "单纯硬件代工企业的边际毛利面临快速摊薄，价值链向中游算法模型与数据闭环集中。",
        "上下游专用装备制造与关键精密原材料将先于整机品牌释放盈利弹性。"
    ]
    advice = "警惕概念过度炒作，聚焦供应链工艺良率与真实世界客户复购率。"

    twitter_thread = (
        f"🧵 深度拆解「{title}」核心逻辑：\n\n"
        f"1/3 核心洞察：{punchline}\n\n"
        f"2/3 关键预判：\n- {predictions[0]}\n- {predictions[1]}\n\n"
        f"3/3 行动指南：{advice}\n\n"
        "#深度研报 #前沿科技 #商业洞察 #AI研报"
    )

    jike_post = (
        f"💡 今日研报高光精炼｜关于《{title}》\n\n"
        f"📌 颠覆性认知：\n{punchline}\n\n"
        f"⚡ 产业三大推演：\n"
        f"1. {predictions[0]}\n"
        f"2. {predictions[1]}\n"
        f"3. {predictions[2]}\n\n"
        f"🎯 关键建议：{advice}\n"
        "— 来自 Deep Research Agent 全景分析"
    )

    xiaohongshu = (
        f"🔥 终于有人把《{title}》讲透了！\n\n"
        f"读完近万字深度报告，这几句实在太扎心了：\n\n"
        f"✨ 一句话划重点：\n{punchline}\n\n"
        f"📊 行业未来三年趋势：\n"
        f"▫️ {predictions[0]}\n"
        f"▫️ {predictions[1]}\n"
        f"▫️ {predictions[2]}\n\n"
        f"💡 给从业者的真诚建议：\n{advice}\n\n"
        f"#前沿科技 #行业洞察 #科技趋势 #认知升级 #硬核科普"
    )

    return {
        "title": title,
        "punchline": punchline,
        "predictions": predictions,
        "action_advice": advice,
        "platforms": {
            "twitter_thread": twitter_thread,
            "jike_post": jike_post,
            "xiaohongshu": xiaohongshu
        },
        "status": "fallback",
        "source": "heuristic"
    }
