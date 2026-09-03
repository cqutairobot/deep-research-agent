import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_REPORT = """# 全固态电池商业化推演报告

## 摘要
全固态电池作为下一代高能量密度电化学体系，正在经历从实验室原型向工程试产的关键过渡 [^cite:1]。

## 关键技术指标
| 技术路线 | 理论能量密度 | 循环寿命 | 关键瓶颈 |
|---|---|---|---|
| 硫化物 | 500 Wh/kg | 1500 次 | 界面阻抗、空气敏感度 |
| 氧化物 | 400 Wh/kg | 1000 次 | 刚性易碎、高阻抗 |

核心结论：2027 年有望迎来首批百 GWh 级商业化示范线交付 [^cite:2]。
"""

def test_docx_exporter_acceptance():
    """断言：Word 文档导出接口返回出版级 DOCX 文件流，包含合法 Zip 幻数 PK\\x03\\x04"""
    res = client.post("/api/v1/research/export/docx", json={
        "report": SAMPLE_REPORT,
        "title": "全固态电池商业化推演报告",
        "style": "consulting"
    })
    assert res.status_code == 200
    assert "openxmlformats-officedocument.wordprocessingml.document" in res.headers.get("content-type", "")
    assert res.content.startswith(b"PK\x03\x04")

def test_marp_exporter_acceptance():
    """断言：Marp 演示文稿导出包含标准 marp 元数据指令与分页符 ---"""
    res = client.post("/api/v1/research/export/marp", json={
        "report": SAMPLE_REPORT,
        "title": "全固态电池商业化推演报告"
    })
    assert res.status_code == 200
    text = res.text
    assert "marp: true" in text
    assert "---" in text
    assert "全固态电池" in text

def test_multimodal_api_suite_acceptance():
    """断言：多模态衍生接口矩阵（长图、因果脑图、社交金句、NLI 雷达）全部输出合规结构"""
    # 1. 长图结构化数据
    res_info = client.post("/api/v1/research/infographic/generate", json={
        "title": "全固态电池",
        "report": SAMPLE_REPORT
    })
    assert res_info.status_code == 200
    assert len(res_info.json()["metrics"]) == 3

    # 2. 因果脑图
    res_map = client.post("/api/v1/research/mindmap/generate", json={
        "title": "全固态电池",
        "report": SAMPLE_REPORT
    })
    assert res_map.status_code == 200
    assert "mermaid_code" in res_map.json()

    # 3. 社交金句
    res_quotes = client.post("/api/v1/research/social-quotes/generate", json={
        "title": "全固态电池",
        "report": SAMPLE_REPORT
    })
    assert res_quotes.status_code == 200
    assert "punchline" in res_quotes.json()

    # 4. NLI 事实雷达
    res_nli = client.post("/api/v1/research/nli/evaluate", json={
        "report": SAMPLE_REPORT,
        "citations": [{"title": "Nature", "snippet": "Solid-state battery 500 Wh/kg", "url": "https://nature.com"}]
    })
    assert res_nli.status_code == 200
    assert res_nli.json()["fact_grounding_score"] >= 90
