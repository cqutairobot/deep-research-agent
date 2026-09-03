"""
NotebookLM 级双角色生动对谈播客服务 (Podcast Service)
1. 大模型编排双主持人（云希·观察员 + 晓晓·技术专家）深度对话剧本；
2. Edge-TTS 异步并发调用双神经音色分段合成；
3. 二进制流无缝拼接为完整 MP3，支持本地永久缓存与秒级分发。
"""

import os
import re
import json
import io
import asyncio
from typing import List, Dict, Any, Optional
import edge_tts
from app.core.config import call_llm, CustomLLMConfig
from app.services.audio_service import clean_text_for_tts, AUDIO_CACHE_DIR

# 播客双角色音色配置
VOICE_MAP = {
    "Yunxi": "zh-CN-YunxiNeural",       # 微软云希 - 沉稳睿智男声 (行业观察员)
    "Xiaoxiao": "zh-CN-XiaoxiaoNeural"   # 微软晓晓 - 知性清澈女声 (前沿技术专家)
}

# 确保音频缓存目录存在
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)


def generate_podcast_dialogue(
    title: str,
    report: str,
    custom_llm_config: Optional[CustomLLMConfig] = None
) -> List[Dict[str, str]]:
    """
    调用大语言模型，将研报核心论点改编为类似 Google NotebookLM 的双人生动对谈播客剧本。
    """
    clean_title = (title or "前沿深度研究").replace("#", "").strip()
    clean_rep = clean_text_for_tts(report)[:6000]

    system_prompt = (
        "你是一位全球顶级前沿科技与商业播客的总制作人兼金牌编剧（风格类似于 Google NotebookLM Deep Dive 播客）。"
        "你的任务是将一份硬核的高密度深度研报，改编为一期生动、扣人心弦、充满思辨张力的双主持人对谈播客剧本。"
        "角色设定：\n"
        "1. 云希 (Yunxi, 男声)：敏锐幽默的资深行业观察员兼主持人。善于从大众好奇心切入，抛出犀利问题与现实痛点，用接地气的形象比喻搭桥；\n"
        "2. 晓晓 (Xiaoxiao, 女声)：通透严谨的技术专家兼产业智库战略合伙人。直击底层物理与商业本质，用量化数据解密核心机理与行业窗口期。\n"
        "输出规范：必须且只能输出严格合法的纯 JSON 数组，绝不能包裹任何外部 Markdown 解释或多余字符。"
    )

    prompt = f"""请仔细研读以下深度研究报告，为这期播客创作一段 8 到 10 轮交互的精彩对谈剧本。

【研报主题】：{clean_title}
【研报精选要点】：
{clean_rep}

【剧本创作要求】：
1. 两人对话必须自然流畅、口语化，杜绝朗读公文式的腔调。可以恰当使用“有意思的是”、“关键恰恰在这里”、“举个极端点的例子”、“但市场真的买账吗”等真实对话气口；
2. 云希先开场，介绍今天的课题背景与行业最大痛点/争议，然后向晓晓抛出第一个关键问题；
3. 晓晓深入解剖核心技术路线的底层原理、对比优缺点、亮出硬核数据；
4. 两人探讨商业化量产落地的现实阻碍（成本、良率、产业链成熟度等），并对未来 3~5 年做出明确研判；
5. 最后以一段富有启发性的总结和对听众的致意结束；
6. 严格输出 JSON 数组格式，格式范例如下：
[
  {{
    "speaker": "Yunxi",
    "name": "云希",
    "role": "行业观察员",
    "text": "欢迎收听本期前沿研报对谈！晓晓，今天这份关于{clean_title[:15]}的报告，一上来就给全行业泼了一盆冷水，直接打破了过去几年的常规共识啊。"
  }},
  {{
    "speaker": "Xiaoxiao",
    "name": "晓晓",
    "role": "技术专家",
    "text": "没错云希！大家都盯着理论上的性能极限，但这份报告把底层的制造良率和BOM成本账本给彻底算透了。"
  }}
]
"""

    try:
        raw_res = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            custom_llm_config=custom_llm_config
        )

        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_res.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', cleaned)
        if match:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list) and len(parsed) >= 4:
                valid_turns = []
                for turn in parsed:
                    if isinstance(turn, dict) and "text" in turn:
                        spk = "Xiaoxiao" if str(turn.get("speaker", "")).lower().startswith("xiao") else "Yunxi"
                        valid_turns.append({
                            "speaker": spk,
                            "name": "晓晓" if spk == "Xiaoxiao" else "云希",
                            "role": "技术专家" if spk == "Xiaoxiao" else "行业观察员",
                            "text": str(turn["text"]).strip()
                        })
                if len(valid_turns) >= 4:
                    return valid_turns
    except Exception as e:
        print(f"[PodcastService] 大模型生成对谈剧本失败，启用结构化剧本保底: {e}")

    return _build_fallback_podcast_script(clean_title, clean_rep)


def _build_fallback_podcast_script(title: str, report_text: str) -> List[Dict[str, str]]:
    """兜底对谈剧本，确保无断崖式崩溃"""
    first_summary = report_text[:300].replace('\n', ' ')
    return [
        {
            "speaker": "Yunxi",
            "name": "云希",
            "role": "行业观察员",
            "text": f"大家好，欢迎收听本期前沿研报对谈！今天我们聚焦一个备受瞩目的核心命题——「{title}」。晓晓，最近无论是学术界还是产业资本，对这个方向的讨论都非常激烈啊。"
        },
        {
            "speaker": "Xiaoxiao",
            "name": "晓晓",
            "role": "技术专家",
            "text": f"是的云希。表面上看大家都在谈技术突破，但这份研报最深刻的地方在于，它直接穿透了概念包装，系统拆解了它的工程可行性与商业落地周期。"
        },
        {
            "speaker": "Yunxi",
            "name": "云希",
            "role": "行业观察员",
            "text": "那在具体的底层机理和主流技术路线选择上，目前产业内最大的分歧和权衡点到底在哪里呢？"
        },
        {
            "speaker": "Xiaoxiao",
            "name": "晓晓",
            "role": "技术专家",
            "text": "核心矛盾集中在性能上限与制造成本的妥协。单纯在实验室提升参数相对容易，但一旦进入规模化量产，良品率和供应链成熟度才是真正的试金石。"
        },
        {
            "speaker": "Yunxi",
            "name": "云希",
            "role": "行业观察员",
            "text": "这就解释了为什么很多初创企业早期估值很高，但到了量产爬坡阶段就会遭遇瓶颈。那从未来三到五年的时间窗口来看，你觉得决定胜负的关键胜负手是什么？"
        },
        {
            "speaker": "Xiaoxiao",
            "name": "晓晓",
            "role": "技术专家",
            "text": "我认为是谁能最快实现从单一硬件售卖向软硬件生态和算法飞轮的跃迁。具备闭环自我造血能力的企业，才更有机会跨越产业周期的鸿沟。"
        },
        {
            "speaker": "Yunxi",
            "name": "云希",
            "role": "行业观察员",
            "text": "非常精辟！感谢晓晓的深度拆解。以上就是本期对谈的核心干货，更多量化图表与详细论证，欢迎大家深入阅读本期完整研报。我们下期再见！"
        }
    ]


async def synthesize_podcast_mp3(script: List[Dict[str, str]], task_id: str) -> bytes:
    """
    分段异步合成云希与晓晓的台词音频，并顺序拼接为单一大文件 MP3 字节流。
    支持磁盘 MD5 缓存。
    """
    safe_tid = re.sub(r'[^a-zA-Z0-9_\-]', '_', task_id)
    cache_audio_path = os.path.join(AUDIO_CACHE_DIR, f"podcast_{safe_tid}.mp3")
    cache_script_path = os.path.join(AUDIO_CACHE_DIR, f"podcast_{safe_tid}_script.json")

    # 命中缓存直接返回
    if os.path.exists(cache_audio_path) and os.path.getsize(cache_audio_path) > 1024:
        with open(cache_audio_path, "rb") as f:
            return f.read()

    combined_buffer = io.BytesIO()

    for idx, turn in enumerate(script):
        speaker = turn.get("speaker", "Yunxi")
        voice = VOICE_MAP.get(speaker, VOICE_MAP["Yunxi"])
        text = clean_text_for_tts(turn.get("text", ""))

        if not text:
            continue

        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            chunk_io = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunk_io.write(chunk["data"])
            
            audio_bytes = chunk_io.getvalue()
            if audio_bytes:
                combined_buffer.write(audio_bytes)
        except Exception as e:
            print(f"[PodcastService] 合成台词第 {idx+1} 轮失败 ({speaker}): {e}")

    full_mp3_data = combined_buffer.getvalue()

    if len(full_mp3_data) > 0:
        try:
            with open(cache_audio_path, "wb") as f:
                f.write(full_mp3_data)
            with open(cache_script_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PodcastService] 写入播客缓存失败: {e}")

    return full_mp3_data


def get_podcast_metadata(task_id: str) -> Optional[Dict[str, Any]]:
    """读取已缓存的播客台词与元数据"""
    safe_tid = re.sub(r'[^a-zA-Z0-9_\-]', '_', task_id)
    cache_script_path = os.path.join(AUDIO_CACHE_DIR, f"podcast_{safe_tid}_script.json")
    cache_audio_path = os.path.join(AUDIO_CACHE_DIR, f"podcast_{safe_tid}.mp3")

    if os.path.exists(cache_script_path) and os.path.exists(cache_audio_path):
        try:
            with open(cache_script_path, "r", encoding="utf-8") as f:
                script = json.load(f)
            return {
                "task_id": task_id,
                "script": script,
                "audio_size": os.path.getsize(cache_audio_path),
                "ready": True
            }
        except Exception:
            pass
    return None
