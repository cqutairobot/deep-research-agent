"""
Edge-TTS 异步音频流生成服务 (Audio Service)
功能：
1. 纯化清洗 Markdown 正文，彻底剥除 Markdown 标记、代码块、Mermaid 图表、LaTeX 公式与文献角标，防止 TTS 朗读非自然符号；
2. 提炼结构化音频广播稿 (Podcast Script)，生成 2~4 分钟高浓缩研报速听广播；
3. 基于 edge-tts 异步合成自然语音 (默认微软云希沉稳专业神经语音)；
4. 内置本地持久化音频缓存，相同任务或文本直接命中缓存秒级响应。
"""

import os
import re
import io
import hashlib
import asyncio
from typing import Optional, AsyncIterator
import edge_tts


# 默认高品质拟真音色 (微软云希 - 沉稳专业男声，晓晓 - 知性沉稳女声)
DEFAULT_VOICE = "zh-CN-YunxiNeural"
AUDIO_CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/audio_cache"))


def clean_text_for_tts(markdown_text: str) -> str:
    """
    纯化清洗 Markdown 文本，将格式化排版转换为适合 TTS 朗读的流畅自然语言。
    去除项目：
    - Markdown 各级标题标号 (#, ##, ### 等)
    - 围栏代码块 (```...```) 及内部所有代码
    - 裸 Mermaid 图表语句 (graph TD, flowchart, subgraph 等)
    - Markdown 表格标记 (| ... | 以及分割线 |---|)
    - LaTeX 行内与块级数学公式 ($$...$$, $...$, \\[...\\])
    - 文献引用角标 ([^cite:N], [N], [1][2] 等)
    - 超链接语法 ([文字](url) -> 保留“文字”)
    - 图片语法 (![alt](url) -> 彻底删除)
    - 加粗/斜体修饰符 (**, *, __, _)
    - 块引用标记 (>)
    - HTML 标签 (<br>, <div> 等)
    - 多余的连续空白行与特殊标点
    """
    if not markdown_text:
        return ""

    text = markdown_text

    # 1. 移除围栏代码块 (包括 ```mermaid ... ``` 与常规代码块)
    text = re.sub(r'```[\s\S]*?```', ' ', text)

    # 2. 移除 LaTeX 块级数学公式 ($$...$$ 或 \\[...\\])
    text = re.sub(r'\$\$[\s\S]*?\$\$', ' ', text)
    text = re.sub(r'\\\[[\s\S]*?\\\]', ' ', text)
    # 移除行内 LaTeX 公式 ($...$)
    text = re.sub(r'\$[^\$\n]+\$', ' ', text)

    # 3. 移除 Markdown 表格 (整行都是以 | 开头并包含 | 的内容)
    text = re.sub(r'^\s*\|.*\|\s*$', ' ', text, flags=re.MULTILINE)

    # 4. 移除裸 Mermaid 架构图行 (未加围栏的图表残留语句)
    text = re.sub(r'^\s*(graph\s+[A-Za-z]+|flowchart\s+[A-Za-z]+|subgraph|sequenceDiagram|gantt|classDiagram|mindmap)[\s\S]*?^\s*end\s*$', ' ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[A-Za-z0-9_\u4e00-\u9fa5]+\s*(-->|==>|-\.->|->>).*$', ' ', text, flags=re.MULTILINE)

    # 5. 移除文献引用角标，如 [^cite:1], [1], [1, 2], [1-3]
    text = re.sub(r'\[\^cite:\d+\]', '', text)
    text = re.sub(r'\[\^?\d+(?:[,\-–—\s]+\d+)*\]', '', text)
    # 移除末尾参考资料定义行，如 [1]: http...
    text = re.sub(r'^\s*\[\d+\]:.*$', '', text, flags=re.MULTILINE)

    # 6. 处理图片与链接
    # 图片 ![alt](url) -> 删除
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 超链接 [文本](url) -> 仅保留“文本”
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

    # 7. 移除标题前缀标号 (#, ##, ### 等)
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)

    # 8. 移除引用块前缀 > 
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)

    # 9. 移除无序与有序列表符号 (-, *, 1. 等) 替换为平缓短顿号或逗号
    text = re.sub(r'^\s*[-*+]\s+', '，', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '，', text, flags=re.MULTILINE)

    # 10. 移除加粗与斜体标记 (**, *, __, _)
    text = re.sub(r'[*_]{1,3}(.*?)[*_]{1,3}', r'\1', text)

    # 11. 移除 HTML 标签及特殊实体编码
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')

    # 12. 规范化空白与标点符号
    lines = [line.strip() for line in text.split('\n')]
    clean_lines = []
    for line in lines:
        l = re.sub(r'^[，,、。；;：:\s]+', '', line).strip()
        if l and not l.startswith('---'):
            clean_lines.append(l)

    result = '。'.join(clean_lines)
    # 收拢连续多个句号、逗号和空格
    result = re.sub(r'[。！!？?]+', '。', result)
    result = re.sub(r'[，,、]+', '，', result)
    result = re.sub(r'\s+', ' ', result)

    return result.strip()


def extract_podcast_script(title: str, report_md: str, max_chars: int = 2200) -> str:
    """
    基于全篇报告结构化提炼出一份约 2~3 分钟的音频广播播客脚本。
    结构：
    1. 播音开场白；
    2. 核心执行摘要提炼；
    3. 关键章节要点串讲；
    4. 结束总结。
    """
    clean_title = re.sub(r'#+\s*', '', title).strip() or "当前调研课题"
    
    # 提取宏观摘要部分 (执行摘要 / 核心发现 / 导读)
    summary_match = re.search(r'(?:执行摘要|核心发现|学术要旨|教程总览|核心洞察|导读|摘要)[\s\S]*?(?=##|\Z)', report_md)
    raw_summary = summary_match.group(0) if summary_match else ""
    clean_summary = clean_text_for_tts(raw_summary)

    # 提取各章节核心结论句
    chapters = re.findall(r'##\s+第\s*\d+\s*章[：:]?\s*([^\n]+)([\s\S]*?)(?=##|\Z)', report_md)
    chapter_points = []
    for ch_title, ch_body in chapters:
        c_clean = clean_text_for_tts(ch_body)
        if c_clean:
            # 取章节前 120 字作为要点
            first_sentence = c_clean[:120].rsplit('。', 1)[0]
            if first_sentence:
                chapter_points.append(f"关于{ch_title.strip()}：{first_sentence}。")

    script_parts = [
        f"欢迎收听深度研究报告音频播报。本期调研主题是：《{clean_title}》。",
    ]

    if clean_summary:
        script_parts.append(f"首先为您梳理核心发现：{clean_summary}")

    if chapter_points:
        script_parts.append("接下来是各章节的关键论述要点：" + "".join(chapter_points[:5]))

    script_parts.append("以上是本次研究报告的核心音频摘要，感谢您的收听。如需查阅完整图表与数据矩阵，请参考报告全文。")

    full_script = " ".join(script_parts)
    # 截断在 max_chars 以内
    if len(full_script) > max_chars:
        full_script = full_script[:max_chars].rsplit('。', 1)[0] + "。以上是本期核心摘要，感谢收听。"

    return full_script


def _get_cache_path(text: str, voice: str) -> str:
    """计算音频缓存文件路径"""
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    cache_key = hashlib.md5(f"{voice}::{text}".encode("utf-8")).hexdigest()
    return os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")


async def generate_audio_bytes(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """
    异步合成自然语音音频流，返回完整的 MP3 二进制数据 (自动命中本地磁盘缓存)
    """
    clean_script = clean_text_for_tts(text) if ("#" in text or "```" in text) else text
    if not clean_script.strip():
        clean_script = "报告内容暂无可朗读文本。"

    cache_file = _get_cache_path(clean_script, voice)
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1024:
        with open(cache_file, "rb") as f:
            return f.read()

    communicate = edge_tts.Communicate(clean_script, voice)
    audio_buffer = io.BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_bytes = audio_buffer.getvalue()

    # 写入本地缓存以备复用
    try:
        with open(cache_file, "wb") as f:
            f.write(audio_bytes)
    except Exception as e:
        print(f"[AudioService Warning] 写入音频缓存失败: {e}")

    return audio_bytes


async def generate_audio_stream(text: str, voice: str = DEFAULT_VOICE) -> AsyncIterator[bytes]:
    """
    流式异步生成音频切片 (用于边合成边播放的流式响应)
    """
    clean_script = clean_text_for_tts(text) if ("#" in text or "```" in text) else text
    if not clean_script.strip():
        clean_script = "报告内容暂无可朗读文本。"

    communicate = edge_tts.Communicate(clean_script, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]
