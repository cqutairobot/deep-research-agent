import operator
from typing import List, Dict, Optional, Annotated, Any
from typing_extensions import TypedDict

class CitationSource(TypedDict):
    """可信引用源定义"""
    id: int                     # 引用序号 [1], [2], [3]
    url: str                    # 原始来源链接（或本地文件路径）
    title: str                  # 网页标题或本地文档名称
    snippet: str                # 提取的原始支持论据片段
    score: float                # 相关性得分
    published_date: Optional[str]

class ChapterOutline(TypedDict):
    """章节调研大纲与任务定义"""
    chapter_num: int            # 章节序号 1, 2, 3...
    title: str                  # 章节标题
    focus: str                  # 调研侧重点
    search_queries: List[str]   # 针对本章规划的检索词
    extracted_facts: List[str]  # 本章搜集到的核心事实要点 (经 Map-Reduce 压缩)
    bound_documents: Optional[List[str]] # 针对本章指定绑定的专属私有文档文件名列表

class ResearchState(TypedDict):
    """LangGraph 状态机核心状态 Schema (Phase 5 升级版)"""
    task_id: str                              # 任务全局唯一 ID
    user_query: str                           # 用户原始研究命题
    research_depth: str                       # 调研深度: quick | standard | deep
    report_style: str                         # 风格: consulting | literature_review | tutorial_docs | executive | briefing
    custom_llm_config: Optional[Dict[str, Any]] # 自定义大模型网关参数 (OpenAI / Anthropic)
    clarification: str                        # 意图澄清或范围说明
    outline: List[ChapterOutline]             # 规划的章节大纲任务列表
    citations: List[CitationSource]           # 全局引用溯源库
    current_step: str                         # 当前执行阶段
    
    # 本地私有文档库 (Hybrid RAG)
    local_documents: List[Dict[str, Any]]     # 用户上传的私有文档切片库
    
    # 反思与递归控制
    iteration_count: int                      # 当前已执行的调研轮次 (初始 1)
    max_iterations: int                       # 最大递归上限
    critic_feedback: str                      # Critic 评估建议与事实矛盾/缺失说明
    needs_more_research: bool                 # 是否需要触发下一轮深搜
    
    # 报告与校验产物
    chapter_drafts: Optional[Dict[int, str]]  # 各章节独立深度稿件 (Map 产物)
    draft_report: str                         # 初稿报告全文 (Reduce 统合产物)
    final_report: str                         # 最终通过防幻觉校验的研报全文
    metrics: Optional[Dict[str, Any]]         # 算力与 Token 消耗追踪指标 (Prompt/Completion/Cost)
    logs: Annotated[List[str], operator.add]  # 实时运行日志流水
