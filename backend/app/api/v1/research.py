import io
import re
import urllib.parse
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from app.services.task_manager import task_manager, TaskStatus
from app.agents.state import ChapterOutline
from app.core.config import call_llm
from app.tools.doc_parser import parse_uploaded_document, MAX_UPLOAD_SIZE_BYTES

router = APIRouter()

class CreateTaskRequest(BaseModel):
    query: str = Field(..., description="调研课题 / 核心命题", min_length=2)
    depth: str = Field("standard", description="调研深度 (quick | standard | deep)")
    style: str = Field("consulting", description="报告风格 (consulting | academic | executive)")
    auto_approve_outline: bool = Field(True, description="是否自动批准大纲")
    max_iterations: int = Field(2, description="最大反思循环轮数", ge=1, le=5)
    local_documents: Optional[List[Dict[str, Any]]] = Field(None, description="上传的本地私有文档库切片")
    owner_id: Optional[str] = Field(None, description="任务所属用户或租户ID (Bug 10)")

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
    task_id = task_manager.create_task(
        user_query=req.query,
        research_depth=req.depth,
        report_style=req.style,
        auto_approve_outline=req.auto_approve_outline,
        max_iterations=req.max_iterations,
        local_documents=req.local_documents,
        owner_id=req.owner_id
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
        
        docx_io = generate_editorial_docx(req.report, req.title)
        
        filename = f"{req.title}.docx"
        encoded_filename = urllib.parse.quote(filename)
        
        return StreamingResponse(
            docx_io,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出 Word 失败: {str(e)}")
