import os
import io
import re
import urllib.parse
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from app.services.task_manager import task_manager, TaskStatus
from app.agents.state import ChapterOutline
from app.core.config import call_llm, CustomLLMConfig, check_llm_connection
from app.tools.doc_parser import parse_uploaded_document, MAX_UPLOAD_SIZE_BYTES

router = APIRouter()

class CreateTaskRequest(BaseModel):
    query: str = Field(..., description="调研课题 / 核心命题", min_length=2)
    depth: str = Field("standard", description="调研深度 (quick | standard | deep)")
    style: str = Field("consulting", description="报告风格 (consulting | literature_review | tutorial_docs | executive | briefing | academic)")
    auto_approve_outline: bool = Field(True, description="是否自动批准大纲")
    max_iterations: int = Field(2, description="最大反思循环轮数", ge=1, le=5)
    local_documents: Optional[List[Dict[str, Any]]] = Field(None, description="上传的本地私有文档库切片")
    owner_id: Optional[str] = Field(None, description="任务所属用户或租户ID (Bug 10)")
    custom_llm_config: Optional[CustomLLMConfig] = Field(None, description="自定义模型网关配置 (OpenAI / Anthropic)")

    @field_validator("query")
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("调研课题不能为空且至少需 2 个字符")
        return v

class CreateTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ChapterOutlineItem(BaseModel):
    chapter_num: int
    title: str = Field(..., min_length=2, description="章节标题")
    focus: str = Field(..., min_length=2, description="调研侧重点")
    search_queries: List[str] = []
    extracted_facts: List[str] = []
    bound_documents: Optional[List[str]] = None

    @field_validator("title", "focus")
    def validate_non_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("章节标题与侧重点不能为空或少于 2 个字符 (Bug 20)")
        return v

class ApproveOutlineRequest(BaseModel):
    outline: List[ChapterOutlineItem] = Field(..., min_length=1, description="确认或修改后的章节大纲列表 (至少 1 章)")

    @field_validator("outline")
    def validate_outline_length(cls, v: List[ChapterOutlineItem]) -> List[ChapterOutlineItem]:
        if not v or len(v) < 1:
            raise ValueError("调研大纲至少需包含 1 个有效章节 (Bug 20)")
        return v

class ChatRequest(BaseModel):
    question: str = Field(..., description="用户追问内容")
    report_context: Optional[str] = Field(None, description="研报正文与事实上下文")
    task_id: Optional[str] = Field(None, description="所属任务ID")

class ChatResponse(BaseModel):
    answer: str

class ExportDocxRequest(BaseModel):
    report: str = Field(..., description="研报 Markdown 文本")
    title: str = Field("深度行业研究报告", description="研报标题")
    style: Optional[str] = Field("consulting", description="研报风格 (consulting | literature_review | tutorial_docs | executive | briefing)")

@router.post("/models/test-connection")
async def test_custom_model_connection(config: CustomLLMConfig):
    """测试自定义模型网络与鉴权连通性"""
    res = check_llm_connection(config.model_dump())
    return res

@router.get("/styles")
async def list_report_styles():
    """获取系统支持的所有研报风格元数据"""
    from app.agents.writer import StyleProfileRegistry
    return {"styles": StyleProfileRegistry.list_styles()}

@router.post("/upload")
async def upload_local_document(file: UploadFile = File(...)):
    # 限制流式读取大小 (Bug 9)
    file_bytes = await file.read(MAX_UPLOAD_SIZE_BYTES + 1024)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="上传文件大小超过 15MB 限制")
    
    try:
        parsed = parse_uploaded_document(file.filename or "uploaded_file", file_bytes)
        return parsed
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

@router.post("/tasks", response_model=CreateTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_research_task(req: CreateTaskRequest):
    custom_cfg = req.custom_llm_config.model_dump() if req.custom_llm_config else None
    task_id = task_manager.create_task(
        user_query=req.query,
        research_depth=req.depth,
        report_style=req.style,
        auto_approve_outline=req.auto_approve_outline,
        max_iterations=req.max_iterations,
        local_documents=req.local_documents,
        owner_id=req.owner_id,
        custom_llm_config=custom_cfg
    )
    return {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "message": "调研任务已创建，可通过 /stream 接口订阅实时事件流"
    }

@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return task

@router.get("/tasks")
async def list_all_tasks():
    return task_manager.list_tasks()

@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str, 
    request: Request,
    last_event_id: Optional[str] = Query(None)
):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
    last_id = last_event_id or request.headers.get("last-event-id")
    return EventSourceResponse(
        task_manager.subscribe_stream(task_id, last_event_id=last_id),
        media_type="text/event-stream"
    )

@router.post("/tasks/{task_id}/approve_outline")
async def approve_task_outline(task_id: str, req: ApproveOutlineRequest):
    raw_outline = [item.model_dump() for item in req.outline]
    success = task_manager.approve_outline(task_id, raw_outline)
    if not success:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        raise HTTPException(
            status_code=400,
            detail=f"任务当前状态为 {task['status']}，并非等待大纲确认状态"
        )
    return {"message": "大纲已确认，Agent 已恢复执行后续全网调研！"}

@router.post("/tasks/{task_id}/cancel")
async def cancel_research_task(task_id: str):
    success = task_manager.cancel_task(task_id)
    if not success:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        return {"message": f"任务当前处于终态 ({task['status']})，无需取消"}
    return {"message": f"任务 {task_id} 已取消"}

@router.post("/chat", response_model=ChatResponse)
async def chat_with_report(req: ChatRequest):
    report_text = req.report_context or ""
    if not report_text and req.task_id:
        task = task_manager.get_task(req.task_id)
        if task and "state" in task:
            report_text = task["state"].get("final_report", "")

    if not report_text:
        report_text = "（暂无具体研报上下文，请基于常识与事实回答）"

    prompt = f"""
你是一位资深的首席研究专家与智库分析师。
以下是已完成的深度研究报告全文及事实库：

【研报全文与事实来源】：
{report_text[:8000]}

【用户的具体追问 / 划词深挖请求】：
{req.question}

请严格基于上述报告中的论据、数据指标与核心逻辑，为用户提供条理清晰、有深度、具有建设性的专业解答。
若解答中的观点直接引自报告中的章节或执行摘要，请在句末附加段落定位锚点，格式为 `[⚓ 第X章]` 或 `[⚓ 执行摘要]`（例如 `[⚓ 第2章]`），以便用户一键直达研报正文对应段落。请使用 Markdown 格式直接回答。
"""
    try:
        answer = call_llm(
            prompt,
            system_prompt="你是一位客观、严谨、具有深厚洞察力的智库研究分析师。",
            temperature=0.3
        )
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"调用大模型追问失败: {str(e)}"}

@router.get("/history")
async def get_research_history(limit: int = 50, offset: int = 0, q: str = ""):
    """获取 SQLite 历史归档列表"""
    from app.db.sqlite_store import list_archived_reports
    items = list_archived_reports(limit=limit, offset=offset, search_query=q)
    return {"items": items, "total": len(items)}

@router.get("/history/{task_id}")
async def get_history_detail(task_id: str):
    """读取单份历史归档报告全文及完整引用源"""
    from app.db.sqlite_store import get_archived_report
    report = get_archived_report(task_id)
    if not report:
        raise HTTPException(status_code=404, detail="历史研报记录不存在")
    return report

@router.delete("/history/{task_id}")
async def delete_history_item(task_id: str):
    """删除指定的历史研报记录"""
    from app.db.sqlite_store import delete_archived_report
    success = delete_archived_report(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="删除失败或记录不存在")
    return {"message": "历史研报已成功删除", "task_id": task_id}

@router.post("/export/docx")
async def export_report_to_docx(req: ExportDocxRequest):
    """
    【顶级智库/商业咨询出版级 Word 文档导出】
    包含：中文字体规范、精装封面与元数据矩阵、标准页眉页脚、
    深蓝表头与斑马纹数据表格、架构图专属代码卡片、正文上标角标及原生超链接。
    """
    try:
        from app.services.docx_exporter import generate_editorial_docx
        
        docx_io = generate_editorial_docx(req.report, req.title, style=req.style or "consulting")
        
        filename = f"{req.title}.docx"
        encoded_filename = urllib.parse.quote(filename)
        
        return StreamingResponse(
            docx_io,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出 Word 失败: {str(e)}")


class ExportMarpRequest(BaseModel):
    report: str = Field(..., description="研报 Markdown 原文")
    title: str = Field("深度研究汇报", description="报告标题")


class GenerateAudioRequest(BaseModel):
    text: str = Field(..., description="需要朗读的文本或研报 Markdown")
    title: str = Field("深度研究播客", description="播报标题")
    voice: Optional[str] = Field("zh-CN-YunxiNeural", description="微软 Edge-TTS 音色")


def _get_task_report_and_title(task_id: str) -> tuple[str, str]:
    from app.db.sqlite_store import get_archived_report
    archived = get_archived_report(task_id)
    if archived and archived.get("final_report"):
        return archived["final_report"], archived.get("user_query") or "深度研究报告"
    
    active_task = task_manager.get_task(task_id)
    if active_task and active_task.final_report:
        return active_task.final_report, active_task.query or "深度研究报告"

    raise HTTPException(status_code=404, detail="未找到该任务的研报内容")


@router.get("/tasks/{task_id}/audio-summary")
async def get_task_audio_summary(task_id: str, voice: str = "zh-CN-YunxiNeural"):
    """
    【Edge-TTS 异步音频流生成与播客速听】
    自动纯化研报内容，剥离代码块与图表，提炼 2~3 分钟高浓缩广播稿，返回高品质 MP3 音频流。
    """
    try:
        from app.services.audio_service import extract_podcast_script, generate_audio_bytes
        report_text, title = _get_task_report_and_title(task_id)
        
        podcast_script = extract_podcast_script(title, report_text)
        audio_bytes = await generate_audio_bytes(podcast_script, voice=voice)
        
        encoded_filename = urllib.parse.quote(f"{title}_音频播报.mp3")
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成音频播客失败: {str(e)}")


@router.post("/export/audio")
async def export_custom_audio(req: GenerateAudioRequest):
    """直接将提交的文本/研报合成为 MP3 音频"""
    try:
        from app.services.audio_service import extract_podcast_script, generate_audio_bytes
        script = extract_podcast_script(req.title, req.text) if len(req.text) > 800 else req.text
        audio_bytes = await generate_audio_bytes(script, voice=req.voice or "zh-CN-YunxiNeural")
        
        encoded_filename = urllib.parse.quote(f"{req.title}.mp3")
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
                "Accept-Ranges": "bytes"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合成语音失败: {str(e)}")


@router.get("/tasks/{task_id}/export/marp")
async def export_task_marp(task_id: str):
    """
    【Marp 演示文稿导出】
    自动将指定研报衍生为标准 Marp 格式的 Markdown 幻灯片 (.md)。
    """
    try:
        from app.services.marp_exporter import generate_marp_slides
        report_text, title = _get_task_report_and_title(task_id)
        
        marp_md = generate_marp_slides(title, report_md=report_text)
        encoded_filename = urllib.parse.quote(f"{title}_演示幻灯片.md")
        
        return Response(
            content=marp_md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出 Marp 幻灯片失败: {str(e)}")


@router.get("/tasks/{task_id}/slides-data")
async def get_task_slides_data(task_id: str):
    """获取 Marp 演示文稿预览元数据与 Markdown 原文"""
    try:
        from app.services.marp_exporter import generate_marp_slides
        report_text, title = _get_task_report_and_title(task_id)
        
        marp_md = generate_marp_slides(title, report_md=report_text)
        page_count = len(marp_md.split("\n\n---\n\n"))
        
        return {
            "task_id": task_id,
            "title": title,
            "marp_markdown": marp_md,
            "page_count": page_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取幻灯片数据失败: {str(e)}")


@router.post("/export/marp")
async def export_custom_marp(req: ExportMarpRequest):
    """直接将提交的研报内容转化为 Marp 幻灯片文件并下载"""
    try:
        from app.services.marp_exporter import generate_marp_slides
        marp_md = generate_marp_slides(req.title, report_md=req.report)
        encoded_filename = urllib.parse.quote(f"{req.title}_演示幻灯片.md")
        
        return Response(
            content=marp_md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转化 Marp 失败: {str(e)}")


@router.post("/export/marp-preview")
async def preview_custom_marp(req: ExportMarpRequest):
    """预览提交的研报转化出的 Marp 幻灯片文本与页数"""
    try:
        from app.services.marp_exporter import generate_marp_slides
        marp_md = generate_marp_slides(req.title, report_md=req.report)
        page_count = len(marp_md.split("\n\n---\n\n"))
        
        return {
            "title": req.title,
            "marp_markdown": marp_md,
            "page_count": page_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览 Marp 失败: {str(e)}")


@router.get("/tasks/{task_id}/export/pptx")
async def export_task_pptx(task_id: str):
    """
    【原生 PowerPoint (.pptx) 演示文稿一键导出】
    端到端将研报转化为 16:9 出版级 Microsoft PowerPoint 演示文稿文件，无需第三方软件中转。
    """
    try:
        from app.services.slides_service import get_or_create_presentation_slides, generate_native_pptx
        report_text, title = _get_task_report_and_title(task_id)
        
        slides = get_or_create_presentation_slides(task_id, title, report_text)
        pptx_io = generate_native_pptx(slides, title)
        
        encoded_filename = urllib.parse.quote(f"{title}_演示文稿.pptx")
        return StreamingResponse(
            pptx_io,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出 PPTX 失败: {str(e)}")


@router.post("/export/pptx")
async def export_custom_pptx(req: ExportMarpRequest):
    """直接将提交的研报内容转化为原生 PowerPoint (.pptx) 并下载"""
    try:
        from app.services.slides_service import extract_presentation_slides, generate_native_pptx
        slides = extract_presentation_slides(req.title, req.report)
        pptx_io = generate_native_pptx(slides, req.title)
        
        encoded_filename = urllib.parse.quote(f"{req.title}_演示文稿.pptx")
        return StreamingResponse(
            pptx_io,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成 PPTX 失败: {str(e)}")


class PreparePresentationRequest(BaseModel):
    custom_llm_config: Optional[CustomLLMConfig] = None
    force_refresh: bool = False


@router.post("/tasks/{task_id}/presentation/prepare")
async def prepare_task_presentation(task_id: str, req: Optional[PreparePresentationRequest] = None):
    """
    【预生成/准备演示文稿数据】
    在后台调用 LLM 演讲总监完成提炼并写入磁盘缓存。
    前端可在此期间展示精美动态加载动画，生成完毕后直接秒开全屏大屏。
    """
    try:
        from app.services.slides_service import get_or_create_presentation_slides, SLIDES_CACHE_DIR
        report_text, title = _get_task_report_and_title(task_id)
        
        custom_cfg = req.custom_llm_config if req else None
        force_refresh = req.force_refresh if req else False
        
        if force_refresh:
            clean_tid = re.sub(r'[^a-zA-Z0-9_\-]', '', task_id) or "default"
            cache_path = os.path.join(SLIDES_CACHE_DIR, f"{clean_tid}_deck.json")
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
        
        slides = get_or_create_presentation_slides(
            task_id=task_id,
            title=title,
            report_md=report_text,
            custom_llm_cfg=custom_cfg,
            use_llm=True
        )
        
        return {
            "status": "ready",
            "task_id": task_id,
            "title": title,
            "slide_count": len(slides),
            "presentation_url": f"/api/v1/research/tasks/{task_id}/presentation"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成演示文稿失败: {str(e)}")


@router.get("/tasks/{task_id}/presentation")
async def get_task_live_presentation(task_id: str):
    """
    【交互式 HTML 大屏放映】
    直接在浏览器中全屏放映研报演示文稿，支持键盘翻页与手势触控。
    """
    try:
        from app.services.slides_service import get_or_create_presentation_slides, generate_interactive_html
        report_text, title = _get_task_report_and_title(task_id)
        
        slides = get_or_create_presentation_slides(task_id, title, report_text)
        html_content = generate_interactive_html(slides, title)
        
        return Response(content=html_content, media_type="text/html; charset=utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成在线演示失败: {str(e)}")


@router.get("/tasks/{task_id}/export/html-slides")
async def export_task_html_slides(task_id: str):
    """下载独立单文件 HTML 演示文稿文件，离线随时双击放映"""
    try:
        from app.services.slides_service import get_or_create_presentation_slides, generate_interactive_html
        report_text, title = _get_task_report_and_title(task_id)
        
        slides = get_or_create_presentation_slides(task_id, title, report_text)
        html_content = generate_interactive_html(slides, title)
        
        encoded_filename = urllib.parse.quote(f"{title}_网页演示文稿.html")
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载 HTML 幻灯片失败: {str(e)}")


@router.post("/export/html-slides")
async def export_custom_html_slides(req: ExportMarpRequest):
    """直接将提交的报告内容转为独立 HTML 演示文稿并下载"""
    try:
        from app.services.slides_service import extract_presentation_slides, generate_interactive_html
        slides = extract_presentation_slides(req.title, req.report)
        html_content = generate_interactive_html(slides, req.title)
        
        encoded_filename = urllib.parse.quote(f"{req.title}_网页演示文稿.html")
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成 HTML 幻灯片失败: {str(e)}")


class GlossaryRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=60, description="需要释义的专业名词或短语")
    context: Optional[str] = Field(None, description="选中文本所在的段落语境")
    custom_llm_config: Optional[CustomLLMConfig] = None


@router.post("/glossary")
async def explain_glossary_term(req: GlossaryRequest):
    """
    【专有名词划词即刻释义】
    结合研报语境秒级解析专有名词，输出通俗大白话。
    """
    try:
        from app.services.glossary_service import explain_term_in_context
        result = explain_term_in_context(
            term=req.term,
            context=req.context,
            custom_llm_config=req.custom_llm_config
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"词汇释义失败: {str(e)}")


@router.get("/tasks/{task_id}/metrics")
async def get_task_metrics_api(task_id: str):
    """
    【任务算力与 Token 成本明细看板】
    获取各 Agent 节点的 Token 输入/输出与预估法币花费。
    """
    try:
        return task_manager.get_task_metrics(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取算力指标失败: {str(e)}")


class RecommendationRequest(BaseModel):
    count: Optional[int] = Field(4, ge=2, le=8, description="推荐课题数量")
    custom_llm_config: Optional[CustomLLMConfig] = None


@router.post("/recommendations")
async def get_recommended_topics(req: Optional[RecommendationRequest] = None):
    """
    【AI 智能课题推荐刷新】
    调用大模型或多元课题库动态推荐前沿研究命题。
    """
    try:
        from app.services.recommendation_service import generate_recommendations
        count = req.count if req else 4
        custom_llm = req.custom_llm_config if req else None
        topics = generate_recommendations(custom_llm_config=custom_llm, count=count)
        return {"topics": topics, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐课题失败: {str(e)}")


class InfographicGenerateRequest(BaseModel):
    title: str = Field(..., description="研报标题")
    report: str = Field(..., description="研报正文")
    custom_llm_config: Optional[CustomLLMConfig] = None


@router.post("/infographic/generate")
async def generate_infographic_data_api(req: InfographicGenerateRequest):
    """
    【AI 社交高光快报长图结构化生成】
    调用大模型为研报量身提炼 3 大硬核量化指标、机理总结与 3 大战略研判。
    """
    try:
        from app.services.infographic_service import generate_infographic_data
        result = generate_infographic_data(
            title=req.title,
            report=req.report,
            custom_llm_config=req.custom_llm_config
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提炼社交长图内容失败: {str(e)}")


# ============================================================================
# 【阶段五核心升级】AI 认知深度与多模态交互全维度升华 Endpoints
# ============================================================================

class TaskEnhanceRequest(BaseModel):
    custom_llm_config: Optional[CustomLLMConfig] = None

class DirectMindmapRequest(BaseModel):
    title: str = Field(..., description="研报标题")
    report: str = Field(..., description="研报正文")
    custom_llm_config: Optional[CustomLLMConfig] = None

class DirectQuotesRequest(BaseModel):
    title: str = Field(..., description="研报标题")
    report: str = Field(..., description="研报正文")
    custom_llm_config: Optional[CustomLLMConfig] = None

class DirectNLIRequest(BaseModel):
    report: str = Field(..., description="研报正文")
    citations: Optional[List[Dict[str, Any]]] = None
    custom_llm_config: Optional[CustomLLMConfig] = None


# 1. NotebookLM 级双角色（云希+晓晓）生动对谈播客接口
@router.post("/tasks/{task_id}/podcast/generate")
async def generate_task_podcast(task_id: str, req: Optional[TaskEnhanceRequest] = None):
    """
    【双角色对谈播客生成】
    编排云希（男声）与晓晓（女声）生动对谈剧本，并合成完整 MP3 音频流。
    """
    try:
        from app.services.podcast_service import generate_podcast_dialogue, synthesize_podcast_mp3
        report_text, title = _get_task_report_and_title(task_id)
        custom_llm = req.custom_llm_config if req else None

        script = generate_podcast_dialogue(title, report_text, custom_llm_config=custom_llm)
        audio_bytes = await synthesize_podcast_mp3(script, task_id=task_id)

        return {
            "task_id": task_id,
            "title": title,
            "script": script,
            "audio_size": len(audio_bytes),
            "audio_url": f"/api/v1/research/tasks/{task_id}/podcast/audio",
            "status": "ready"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成双角色播客失败: {str(e)}")


@router.get("/tasks/{task_id}/podcast")
async def get_task_podcast(task_id: str):
    """获取已生成的双人播客台词剧本与音频状态"""
    try:
        from app.services.podcast_service import get_podcast_metadata
        meta = get_podcast_metadata(task_id)
        if not meta:
            raise HTTPException(status_code=404, detail="播客尚未生成，请先调用生成接口")
        meta["audio_url"] = f"/api/v1/research/tasks/{task_id}/podcast/audio"
        return meta
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取播客状态失败: {str(e)}")


@router.get("/tasks/{task_id}/podcast/audio")
async def stream_task_podcast_audio(task_id: str):
    """流式传输双角色对谈完整 MP3 音频"""
    try:
        from app.services.podcast_service import synthesize_podcast_mp3, get_podcast_metadata
        meta = get_podcast_metadata(task_id)
        if meta and meta.get("script"):
            audio_bytes = await synthesize_podcast_mp3(meta["script"], task_id=task_id)
        else:
            report_text, title = _get_task_report_and_title(task_id)
            from app.services.podcast_service import generate_podcast_dialogue
            script = generate_podcast_dialogue(title, report_text)
            audio_bytes = await synthesize_podcast_mp3(script, task_id=task_id)

        encoded_filename = urllib.parse.quote(f"{task_id}_双人播客.mp3")
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"传输播客音频失败: {str(e)}")


# 2. 因果机制与方案权衡知识图谱思维导图接口
@router.post("/tasks/{task_id}/mindmap/generate")
async def generate_task_causal_mindmap(task_id: str, req: Optional[TaskEnhanceRequest] = None):
    """基于指定任务报告提炼因果推演与方案权衡拓扑脑图"""
    try:
        from app.services.mindmap_service import generate_causal_mindmap
        report_text, title = _get_task_report_and_title(task_id)
        custom_llm = req.custom_llm_config if req else None
        data = generate_causal_mindmap(title, report_text, custom_llm_config=custom_llm)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提炼因果思维导图失败: {str(e)}")


@router.post("/mindmap/generate")
async def generate_direct_causal_mindmap(req: DirectMindmapRequest):
    """直接基于提交的文本生成因果思维导图"""
    try:
        from app.services.mindmap_service import generate_causal_mindmap
        data = generate_causal_mindmap(req.title, req.report, custom_llm_config=req.custom_llm_config)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成因果思维导图失败: {str(e)}")


# 3. 社交媒体爆款金句与多平台文案接口
@router.post("/tasks/{task_id}/social-quotes")
async def generate_task_social_quotes(task_id: str, req: Optional[TaskEnhanceRequest] = None):
    """为指定任务报告提炼社交爆款金句与 X / 即刻 / 小红书适配文案"""
    try:
        from app.services.social_quotes_service import generate_social_quotes
        report_text, title = _get_task_report_and_title(task_id)
        custom_llm = req.custom_llm_config if req else None
        data = generate_social_quotes(title, report_text, custom_llm_config=custom_llm)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提炼社交金句失败: {str(e)}")


@router.post("/social-quotes/generate")
async def generate_direct_social_quotes(req: DirectQuotesRequest):
    """直接基于提交的文本提炼社交爆款金句"""
    try:
        from app.services.social_quotes_service import generate_social_quotes
        data = generate_social_quotes(req.title, req.report, custom_llm_config=req.custom_llm_config)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成社交金句失败: {str(e)}")


# 4. 文献 NLI 语义蕴含裁判与抗幻觉雷达接口
@router.post("/tasks/{task_id}/nli-radar")
async def evaluate_task_nli_radar(task_id: str, req: Optional[TaskEnhanceRequest] = None):
    """对任务研报的关键论断进行 NLI 语义蕴含判定，输出事实依据指数"""
    try:
        from app.services.nli_service import evaluate_report_grounding
        report_text, title = _get_task_report_and_title(task_id)
        
        # 尝试提取任务关联的 citations
        citations = []
        task = task_manager.tasks.get(task_id)
        if task and hasattr(task, "state") and task.state and hasattr(task.state, "citations"):
            citations = [c.dict() if hasattr(c, "dict") else c for c in task.state.citations]
        
        custom_llm = req.custom_llm_config if req else None
        data = evaluate_report_grounding(report_text, citations=citations, custom_llm_config=custom_llm)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算 NLI 蕴含雷达失败: {str(e)}")


@router.post("/nli/evaluate")
async def evaluate_direct_nli(req: DirectNLIRequest):
    """直接对文本与信源切片执行 NLI 蕴含度判定"""
    try:
        from app.services.nli_service import evaluate_report_grounding
        data = evaluate_report_grounding(req.report, citations=req.citations, custom_llm_config=req.custom_llm_config)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行 NLI 语义核验失败: {str(e)}")






