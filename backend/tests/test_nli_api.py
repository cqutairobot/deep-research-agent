from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_nli_evaluation():
    """断言：NLI 核验接口返回事实依据指数与论断判定清单。"""
    mock_llm_json = '''
    {
      "fact_grounding_score": 97.2,
      "entailment_rate": 95.0,
      "summary": "全篇论据严谨扎实，关键指标与前沿学术论文完全对齐。",
      "evaluations": [
        {
          "claim": "全固态软包电芯能量密度实测达 505Wh/kg。",
          "verdict": "Entailment",
          "confidence": 0.98,
          "rationale": "与信源 Nature Energy 论文数据完全一致。"
        }
      ]
    }
    '''
    with patch("app.services.nli_service.call_llm", return_value=mock_llm_json):
        res = client.post("/api/v1/research/nli/evaluate", json={
            "report": "全固态软包电芯能量密度实测达 505Wh/kg [^cite:1]。",
            "citations": [{"title": "Nature Energy", "snippet": "energy density of 505 Wh/kg was achieved.", "url": "https://nature.com/example"}]
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["fact_grounding_score"] >= 90
        assert data["evaluations"][0]["verdict"] == "Entailment"
