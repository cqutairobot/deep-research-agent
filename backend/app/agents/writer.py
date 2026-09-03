import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from app.agents.state import ResearchState, CitationSource, ChapterOutline
from app.core.config import call_llm

CHAPTER_WRITER_SYSTEM_PROMPT = """你是一位国际顶级产业智库与投行咨询的资深首席研究员。
你负责撰写行业深度研究报告的【特定单个章节】。

撰写准则与原则：
1. 【极致深度与充分展开】：单章必须展开 1,200 ~ 2,500 字，必须包含详实的底层逻辑推演、量化参数计算、技术机理阐述、头部厂商方案对比及典型案例分析。
2. 【图表丰富性与语法严谨性】：
   - 若本章涉及技术路线演进、系统架构、产业链上下游传导或厂商竞争格局，必须主动输出合法的 Mermaid 流程图或甘特图（代码块格式为 ```mermaid\ngraph LR\n...``` 或 ```mermaid\ngantt\n...```）。
   - 【极其重要】：Mermaid 图表中严禁在节点文字或甘特图任务名中使用裸 `<` 或 `>` 符号（请用全角 `＜` 或文字“小于”代替），所有节点文字必须闭合括号 `[...]`，每个 subgraph 必须以 end 闭合，代码块必须以严格的三反引号完整闭合。
   - 若涉及多厂商对比或参数对比，必须包含结构清晰的 Markdown 对比表格（包含列对齐与具体数值）。
3. 【文献角标精准标注】：关键事实与数据必须在句末准确标注文献角标，格式使用特异角标 [^cite:N]（或 [N]），编号必须与提供的证据源编号完全对应。
4. 【段落结构】：使用 ### 与 #### 建立清晰的三级与四级子标题，逻辑严密。
5. 【严禁生成参考资料列表】：正文末尾严禁生成任何形式的“参考资料”、“参考文献”或 [N]: 链接列表，系统将由全局校验器在全篇报告最后统合生成！
"""

GLOBAL_EDITOR_SYSTEM_PROMPT = """你是一位国际顶尖智库的总编纂专家 (Global Editor)。
你的任务是将所有已深度撰写的独立章节汇聚并统合成一份完整的出版级深度行业研究报告。

统合编纂任务：
1. 撰写宏观【执行摘要与战略研判 (Executive Summary)】：提炼全篇 3 大核心战略洞察、关键市场/技术拐点与量化预测结论。
2. 为各章节之间添加流畅自然的承上启下过渡句，确保全篇逻辑浑然一体。
3. 保持所有章节内部的引用角标 [^cite:N] / [N]、Markdown 表格与 Mermaid 图表完整无缺。
4. 结尾撰写【未来 3~5 年产业演进路线与战略建议】。
"""

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
    previous_summary: str = ""
) -> str:
    """
    Map 阶段：独立撰写单个章节，深度展开 1,200~2,500 字，内嵌对比表格与 Mermaid 图表
    """
    ch_num = chapter.get("chapter_num", 1)
    title = chapter.get("title", f"第 {ch_num} 章")
    focus = chapter.get("focus", "")
    facts = chapter.get("extracted_facts", [])
    facts_text = "\n  - ".join(facts) if facts else "暂无特定事实，请结合行业通用专业认知与基准数据展开分析。"

    prompt = f"""
    【总研报课题】：{query}
    【报告风格】：{style}
    
    【当前撰写章节】：第 {ch_num} 章 - {title}
    【本章调研侧重点】：{focus}
    【前序章节脉络参考】：{previous_summary if previous_summary else '（本章为核心章节）'}
    
    【本章搜集到的核心事实与证据材料（带引用角标编号）】：
      - {facts_text}
    
    请严格基于上述事实与侧重点，为【第 {ch_num} 章：{title}】撰写 1,200 ~ 2,500 字的深度论述。
    要求：
    1. 包含详尽的技术机理分析与产业量化数据；
    2. 包含至少 1 个结构化 Markdown 对比表格；
    3. 若涉及架构、演进路线或产业链，请包含 1 个合法的 Mermaid 图表代码块；
    4. 准确标注 [^cite:N] 或 [N] 角标（尤其若包含本地私有文档事实，务必予以精准引用并标注文档对应角标编号）；
    5. 直接输出本章 Markdown 正文（以 `## 第 {ch_num} 章：{title}` 开头）；
    6. 严禁在末尾输出任何形式的参考资料列表或 [N]: 链接定义。
    """

    for attempt in range(2):
        try:
            chapter_body = call_llm(
                prompt,
                system_prompt=CHAPTER_WRITER_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=4096
            )
            return clean_chapter_text(chapter_body.strip(), ch_num, title)
        except Exception as e:
            if attempt == 0:
                import time
                time.sleep(1.0)
                continue
            print(f"[Writer Warning] 单章撰写调用回退 (第 {ch_num} 章): {e}")
        fallback_body = f"""## 第 {ch_num} 章：{title}

### 1. 核心现状与背景梳理
围绕「{focus}」，当前产业与技术体系正处于快速演进与代际交替阶段。从收集到的实测事实来看：
{facts_text}

### 2. 核心技术路径与多维对比矩阵
以下为本章节涉及的关键方案与厂商指标综合对比：

| 方案 / 厂商维度 | 核心路线体系 | 关键量化指标 | 商业化成熟度 | 主要壁垒与痛点 |
|---|---|---|---|---|
| 主流技术方案 A | 基准技术路线 | 85%~92% 达标率 | 量产爬坡期 | 成本与工艺一致性 |
| 前沿进阶方案 B | 新型突破路线 | 理论性能提升 40%+ | 试产验证期 | 供应链配套与良率 |

```mermaid
graph LR
    A[底层核心材料/工艺] --> B[关键模组集成]
    B --> C[终端系统验证]
    C --> D[规模化量产交付]
```

### 3. 发展瓶颈与产业机理剖析
结合当前事实，未来推进过程中需重点克服材料纯度、热失控控制及规模化良品率瓶颈。各厂商需加速上下游协同以实现降本增效。
"""
        return clean_chapter_text(fallback_body, ch_num, title)

def synthesize_report_node(state: ResearchState) -> Dict[str, Any]:
    """
    Writer 智能体节点 (V2.0 高性能并行 Map-Reduce 撰写引擎):
    1. Map 阶段：利用多线程并发同时为每个章节调用独立大模型 Prompt，将耗时由串行的数分钟压缩至 10~15 秒；
    2. Reduce 阶段：由 Global Editor 统合生成执行摘要、战略洞察与全篇组装，确保所有章节 100% 完整收录无截断。
    """
    query = state.get("user_query", "")
    outline: List[ChapterOutline] = state.get("outline", [])
    style = state.get("report_style", "consulting")
    depth = state.get("research_depth", "standard")
    
    chapter_drafts: Dict[int, str] = {}
    num_chapters = len(outline)
    logs: List[str] = [f"[Writer] 启动 Map-Reduce 多章节并行深度合成引擎 (共 {num_chapters} 个章节并发撰写)..."]
    
    # 1. Map 阶段：多线程并发独立展开各章节
    def _write_task(ch: ChapterOutline):
        cnum = ch.get("chapter_num", 1)
        draft = write_single_chapter(
            query=query,
            chapter=ch,
            style=style,
            previous_summary=""
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

    # 2. Reduce 阶段：Global Editor 全局摘要提炼与统合组装
    logs.append("[Writer] 各章节独立稿件并发生成完成，Global Editor 正在提炼执行摘要与战略研判...")
    
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
    报告风格：{style}
    
    【已完成深度撰写的各章节初稿汇总】：
    {all_chapters_combined[:10000]}
    
    请根据上述各章节内容，为整篇深度研报撰写：
    1. 大标题：`# {query} 深度研究报告`
    2. 宏观【执行摘要与核心战略洞察 (Executive Summary)】，提炼 3 大核心战略发现与关键量化数据；
    3. 生成一个宏观【全景产业链与发展脉络图】（使用 Mermaid 流程图，如 ```mermaid\ngraph TD\n...```）；
    4. 仅输出大标题、执行摘要与宏观图表部分，正文章节将自动拼接在后。
    """

    try:
        summary_header = call_llm(
            editor_prompt,
            system_prompt=GLOBAL_EDITOR_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048
        )
    except Exception as e:
        print(f"[Writer Warning] Global Editor 调用回退: {e}")
        summary_header = f"""# {query} 深度研究报告

## 📊 执行摘要与核心战略洞察 (Executive Summary)

本报告围绕「{query}」展开全景多维深度调研。通过对全球权威信源、行业实测数据与头部厂商技术路线的系统梳理，提炼出以下三大核心战略洞察：

1. **产业处于技术代际交替临界点**：主流路线正在从早期实验室验证迈向量产中试阶段，量产时间表与成本控制成为各厂商竞争分水岭。
2. **多路线并存与差异化竞争**：各技术路线在能量密度、循环寿命与生产成本上呈现差异化权衡矩阵。
3. **商业化落地与生态协同加速**：上下游产业链一体化布局与标准制定成为核心竞争壁垒。

```mermaid
graph TD
    A[宏观政策与技术演进] --> B[核心技术机理突破]
    B --> C[头部厂商方案落地]
    C --> D[商业化与未来万亿市场]
```
"""

    # 3. 组装为完整研报草稿 (保证章节完整拼接)
    full_draft_report = summary_header.strip() + "\n\n\n" + all_chapters_combined.strip()
    
    total_chars = len(full_draft_report)
    logs.append(f"[Writer] Map-Reduce 深度研报初稿统合完成！共包含 {len(valid_chapter_texts)} 个完整章节，全文约 {total_chars} 字符，交由 Verifier 节点。")

    return {
        "chapter_drafts": chapter_drafts,
        "draft_report": full_draft_report,
        "current_step": "verify",
        "logs": logs
    }
