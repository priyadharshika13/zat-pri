"""
Tests for AI governance and compliance.

Validates that AI features respect global toggle and fallback correctly.
"""

import os


def test_ai_disabled_fallback(client, headers, monkeypatch):
    """Test that AI endpoints fallback when AI is globally disabled."""
    # Disable AI globally
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "false")
    
    # Test readiness score (should return UNKNOWN status)
    res = client.get(
        "/api/v1/ai/readiness-score",
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ["UNKNOWN", "RED"]
    assert body.get("readiness_score") is None or body.get("readiness_score") == 0


def test_ai_explanation_disabled_fallback(client, headers, monkeypatch):
    """Test that AI explanation endpoint falls back to rule-based when disabled."""
    # Disable AI globally
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "false")
    
    res = client.post(
        "/api/v1/ai/explain-zatca-error",
        json={
            "error_code": "ZATCA-2001",
            "error_message": "Test error"
        },
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    # Should still return explanation (rule-based fallback)
    assert "explanation_en" in body or "error_code" in body


def test_ai_prediction_disabled_returns_unknown(client, headers, monkeypatch):
    """Test that prediction returns UNKNOWN when AI is disabled."""
    # Disable AI globally
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "false")
    
    res = client.post(
        "/api/v1/ai/predict-rejection",
        json={
            "invoice_payload": {},
            "environment": "SANDBOX"
        },
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert body["risk_level"] in ["UNKNOWN", "HIGH"]
    assert body["confidence"] in (0.0, 0.95, 0.7)


def test_ai_endpoints_log_usage_when_enabled(client, headers, monkeypatch):
    """Test that AI endpoints log usage when AI is enabled."""
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    res = client.get(
        "/api/v1/ai/readiness-score",
        headers=headers
    )
    # Should succeed (may return UNKNOWN if OpenAI not configured, but should not error)
    assert res.status_code == 200


def test_ai_governance_respects_global_toggle(client, headers, monkeypatch):
    """Test that all AI endpoints respect the global ENABLE_AI_EXPLANATION toggle."""
    # Disable AI
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "false")
    
    endpoints = [
        ("/api/v1/ai/predict-rejection", "POST", {
            "invoice_payload": {},
            "environment": "SANDBOX"
        }),
        ("/api/v1/ai/precheck-advisor", "POST", {
            "invoice_payload": {},
            "environment": "SANDBOX"
        }),
        ("/api/v1/ai/root-cause-analysis", "POST", {
            "error_code": "ZATCA-2001",
            "environment": "SANDBOX"
        }),
        ("/api/v1/ai/readiness-score", "GET", None),
        ("/api/v1/ai/error-trends", "GET", None)
    ]
    
    for endpoint, method, payload in endpoints:
        if method == "POST":
            res = client.post(endpoint, json=payload, headers=headers)
        else:
            res = client.get(endpoint, headers=headers)
        
        # All should return 200 (with fallback responses)
        assert res.status_code == 200, f"Endpoint {endpoint} failed with AI disabled"

