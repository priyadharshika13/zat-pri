"""
Tests for AI Phase-3 endpoints (3.1-3.5).

Covers:
- Phase-3.1: Invoice Rejection Prediction
- Phase-3.2: Smart Pre-Check Advisor
- Phase-3.3: Root Cause Intelligence
- Phase-3.4: ZATCA Readiness Score
- Phase-3.5: Error & Trend Intelligence
"""

import os


def test_ai_rejection_prediction(client, headers, monkeypatch):
    """Test AI rejection prediction endpoint (Phase-3.1)."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    res = client.post(
        "/api/v1/ai/predict-rejection",
        json={
            "invoice_payload": {
                "invoice_number": "INV-TEST-001",
                "total": 100.0
            },
            "environment": "SANDBOX"
        },
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "risk_level" in body
    assert body["risk_level"] in ["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
    assert "confidence" in body
    assert "likely_reasons" in body
    assert "advisory_note" in body


def test_ai_precheck_advisor(client, headers, monkeypatch):
    """Test AI pre-check advisor endpoint (Phase-3.2)."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    res = client.post(
        "/api/v1/ai/precheck-advisor",
        json={
            "invoice_payload": {
                "invoice_number": "INV-TEST-001",
                "total": 100.0
            },
            "environment": "SANDBOX"
        },
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "warnings" in body
    assert isinstance(body["warnings"], list)
    assert "risk_score" in body
    assert "advisory_summary" in body


def test_ai_root_cause(client, headers, monkeypatch):
    """Test AI root cause analysis endpoint (Phase-3.3)."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    res = client.post(
        "/api/v1/ai/root-cause-analysis",
        json={
            "error_code": "ZATCA-2001",
            "error_message": "Tax mismatch",
            "rule_based_explanation": {
                "title": "VAT issue",
                "technical_reason": "Mismatch",
                "fix_suggestion": "Align VAT"
            },
            "environment": "SANDBOX"
        },
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "primary_cause" in body
    assert "secondary_causes" in body
    assert "prevention_checklist" in body
    assert "confidence" in body


def test_ai_readiness_score(client, headers, monkeypatch):
    """Test AI readiness score endpoint (Phase-3.4)."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    res = client.get(
        "/api/v1/ai/readiness-score?period=30d",
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "readiness_score" in body
    assert "status" in body
    assert body["status"] in ["GREEN", "AMBER", "RED", "UNKNOWN"]
    assert "risk_factors" in body
    assert "improvement_suggestions" in body
    assert "confidence" in body


def test_ai_error_trends(client, headers, monkeypatch):
    """Test AI error trends endpoint (Phase-3.5)."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    res = client.get(
        "/api/v1/ai/error-trends?period=30d&scope=tenant",
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "top_errors" in body
    assert "emerging_risks" in body
    assert "trend_summary" in body
    assert "recommended_actions" in body
    assert "confidence" in body


def test_ai_endpoints_require_authentication(client):
    """Test that AI endpoints require authentication."""
    res = client.post(
        "/api/v1/ai/predict-rejection",
        json={
            "invoice_payload": {},
            "environment": "SANDBOX"
        }
    )
    assert res.status_code == 401


def test_ai_endpoints_with_different_periods(client, headers, monkeypatch):
    """Test readiness score with different period parameters."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    for period in ["30d", "90d", "all"]:
        res = client.get(
            f"/api/v1/ai/readiness-score?period={period}",
            headers=headers
        )
        assert res.status_code == 200
        body = res.json()
        assert "readiness_score" in body
        assert "status" in body

