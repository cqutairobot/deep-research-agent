import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "research_archive.db"

def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化 SQLite 历史归档数据表"""
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS archived_reports (
            task_id TEXT PRIMARY KEY,
            user_query TEXT NOT NULL,
            research_depth TEXT DEFAULT 'standard',
            report_style TEXT DEFAULT 'consulting',
            created_at REAL,
            final_report TEXT,
            outline_json TEXT,
            citations_json TEXT,
            word_count INTEGER DEFAULT 0,
            summary TEXT DEFAULT ''
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_archived_created ON archived_reports(created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_archived_query ON archived_reports(user_query);")
        conn.commit()
    
    sync_output_files_to_db()

def sync_output_files_to_db():
    """将 legacy 的 backend/output/*.md 自动同步归档到 SQLite"""
    out_dir = Path(__file__).resolve().parent.parent.parent / "output"
    if not out_dir.exists():
        return
    import re
    import os
    try:
        with get_connection() as conn:
            for p in out_dir.glob("*.md"):
                tid = p.stem
                cursor = conn.execute("SELECT 1 FROM archived_reports WHERE task_id = ?", (tid,))
                if not cursor.fetchone():
                    content = p.read_text(encoding="utf-8")
                    if not content.strip():
                        continue
                    m_title = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                    title = m_title.group(1).strip() if m_title else tid
                    mtime = os.path.getmtime(p)
                    word_count = len(content)

                    chapter_matches = re.findall(r"^##\s+(?:第\s*(\d+)\s*章[：:]\s*)?(.+)$", content, re.MULTILINE)
                    outline = []
                    for c_idx, ch in enumerate(chapter_matches, 1):
                        c_num = int(ch[0]) if ch[0] else c_idx
                        outline.append({
                            "chapter_num": c_num,
                            "title": ch[1].strip(),
                            "focus": ch[1].strip(),
                            "search_queries": [],
                            "extracted_facts": []
                        })

                    m_sum = re.search(r"##\s+执行摘要[^\n]*\n+([\s\S]*?)(?=\n##|\Z)", content)
                    summary = m_sum.group(1).strip()[:200] if m_sum else ""

                    conn.execute("""
                    INSERT OR REPLACE INTO archived_reports 
                    (task_id, user_query, research_depth, report_style, created_at, final_report, outline_json, citations_json, word_count, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        tid,
                        title,
                        "standard",
                        "consulting",
                        mtime,
                        content,
                        json.dumps(outline, ensure_ascii=False),
                        "[]",
                        word_count,
                        summary
                    ))
            conn.commit()
    except Exception as e:
        print(f"[SQLite Warning] 同步 output/*.md 失败: {e}")

init_db()

def save_report_archive(
    task_id: str,
    user_query: str,
    research_depth: str,
    report_style: str,
    final_report: str,
    outline: List[Dict[str, Any]],
    citations: List[Dict[str, Any]],
    summary: str = ""
) -> bool:
    """持久化保存已完成的深度调研成果"""
    if not task_id or not final_report:
        return False

    word_count = len(final_report)
    outline_json = json.dumps(outline, ensure_ascii=False)
    citations_json = json.dumps(citations, ensure_ascii=False)
    created_at = time.time()

    try:
        with get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO archived_reports 
            (task_id, user_query, research_depth, report_style, created_at, final_report, outline_json, citations_json, word_count, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                task_id,
                user_query,
                research_depth,
                report_style,
                created_at,
                final_report,
                outline_json,
                citations_json,
                word_count,
                summary[:300] if summary else ""
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"[SQLite Error] 保存历史报告失败: {e}")
        return False

def list_archived_reports(
    limit: int = 50,
    offset: int = 0,
    search_query: str = ""
) -> List[Dict[str, Any]]:
    """分页与模糊查询历史归档列表"""
    try:
        with get_connection() as conn:
            if search_query and search_query.strip():
                pattern = f"%{search_query.strip()}%"
                cursor = conn.execute("""
                SELECT task_id, user_query, research_depth, report_style, created_at, word_count, summary
                FROM archived_reports
                WHERE user_query LIKE ? OR summary LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
                """, (pattern, pattern, limit, offset))
            else:
                cursor = conn.execute("""
                SELECT task_id, user_query, research_depth, report_style, created_at, word_count, summary
                FROM archived_reports
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
                """, (limit, offset))
            
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "task_id": r["task_id"],
                    "user_query": r["user_query"],
                    "research_depth": r["research_depth"],
                    "report_style": r["report_style"],
                    "created_at": r["created_at"],
                    "word_count": r["word_count"],
                    "summary": r["summary"]
                })
            return results
    except Exception as e:
        print(f"[SQLite Error] 查询历史报告列表失败: {e}")
        return []

def get_archived_report(task_id: str) -> Optional[Dict[str, Any]]:
    """根据任务 ID 读取单份历史研报全文及完整引证溯源矩阵"""
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
            SELECT task_id, user_query, research_depth, report_style, created_at, final_report, outline_json, citations_json, word_count, summary
            FROM archived_reports
            WHERE task_id = ?;
            """, (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "task_id": row["task_id"],
                "user_query": row["user_query"],
                "research_depth": row["research_depth"],
                "report_style": row["report_style"],
                "created_at": row["created_at"],
                "final_report": row["final_report"],
                "outline": json.loads(row["outline_json"] or "[]"),
                "citations": json.loads(row["citations_json"] or "[]"),
                "word_count": row["word_count"],
                "summary": row["summary"]
            }
    except Exception as e:
        print(f"[SQLite Error] 获取历史报告详情失败: {e}")
        return None

def delete_archived_report(task_id: str) -> bool:
    """删除指定的历史研报记录"""
    try:
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM archived_reports WHERE task_id = ?;", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"[SQLite Error] 删除历史报告失败: {e}")
        return False
