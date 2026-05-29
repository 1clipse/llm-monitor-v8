from app.analyzer import analyze


def test_analyze_returns_risk_fields():
    result = analyze("hello world. this is a stable mock response")
    assert "risk_score" in result
    assert result["risk_label"] in {"LOW", "MEDIUM", "HIGH"}
    assert "model_probabilities" in result
