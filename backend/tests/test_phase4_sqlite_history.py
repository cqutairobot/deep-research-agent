import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.sqlite_store import (
    save_report_archive,
    get_archived_report,
    list_archived_reports,
    delete_archived_report
)

client = TestClient(app)

def test_sqlite_save_and_retrieve_archive():
    """测试 SQLite 持久化归档研报存储与读取"""
    task_id = "test_archive_task_001"
    query = "2026年全固态电池商业化落地与主要厂商进展"
    report_text = "# 全固态电池研报\n\n## 执行摘要\n核心数据分析 [1]...\n\n```mermaid\ngraph LR\nA-->B\n```\n\n## 📚 参考资料\n[1] 丰田技术白皮书"
    outline = [{"chapter_num": 1, "title": "技术机理", "focus": "电解质", "search_queries": ["电解质"], "extracted_facts": []}]
    citations = [{"id": 1, "url": "https://toyota.com", "title": "丰田技术白皮书", "snippet": "离子电导率高", "score": 0.98, "published_date": None}]

    # 1. 存储
    saved = save_report_archive(
        task_id=task_id,
        user_query=query,
        research_depth="deep",
        report_style="consulting",
        final_report=report_text,
        outline=outline,
        citations=citations,
        summary="全固态电池宏观调研"
    )
    assert saved is True

    # 2. 读取详情
    detail = get_archived_report(task_id)
    assert detail is not None
    assert detail["task_id"] == task_id
    assert detail["user_query"] == query
    assert detail["word_count"] == len(report_text)
    assert len(detail["outline"]) == 1
    assert len(detail["citations"]) == 1
    assert "mermaid" in detail["final_report"]
    
    # 清理测试记录
    delete_archived_report(task_id)

def test_sqlite_list_and_search_archive():
    """测试历史研报列表与模糊关键词检索"""
    t1 = "test_search_task_robot"
    t2 = "test_search_task_battery"
    save_report_archive(
        task_id=t1,
        user_query="具身智能灵巧手微电机驱动技术",
        research_depth="standard",
        report_style="academic",
        final_report="具身智能报告内容...",
        outline=[],
        citations=[]
    )
    save_report_archive(
        task_id=t2,
        user_query="低空经济 eVTOL 适航审定与商业运营",
        research_depth="quick",
        report_style="executive",
        final_report="低空经济研报内容...",
        outline=[],
        citations=[]
    )

    # 模糊检索 "灵巧手"
    results = list_archived_reports(limit=10, search_query="灵巧手")
    assert len(results) >= 1
    assert any(r["task_id"] == t1 for r in results)

    # 模糊检索 "低空经济"
    results_evtol = list_archived_reports(limit=10, search_query="低空经济")
    assert len(results_evtol) >= 1
    assert any(r["task_id"] == t2 for r in results_evtol)
    
    # 清理测试记录
    delete_archived_report(t1)
    delete_archived_report(t2)

def test_history_rest_api_endpoints():
    """测试 REST API /api/v1/research/history 全链路"""
    task_id = "test_rest_api_archive_002"
    save_report_archive(
        task_id=task_id,
        user_query="脑机接口临床进展与侵入式电极",
        research_depth="standard",
        report_style="consulting",
        final_report="# 脑机接口研报全文",
        outline=[],
        citations=[]
    )

    # 1. GET /history 列表
    resp = client.get("/api/v1/research/history?limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert any(it["task_id"] == task_id for it in data["items"])

    # 2. GET /history/{task_id} 详情
    detail_resp = client.get(f"/api/v1/research/history/{task_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["task_id"] == task_id
    assert detail_data["user_query"] == "脑机接口临床进展与侵入式电极"

    # 3. DELETE /history/{task_id}
    del_resp = client.delete(f"/api/v1/research/history/{task_id}")
    assert del_resp.status_code == 200

    # 4. 再次获取应为 404
    get_again = client.get(f"/api/v1/research/history/{task_id}")
    assert get_again.status_code == 404
