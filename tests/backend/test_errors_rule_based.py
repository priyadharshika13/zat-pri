"""
Tests for rule-based error explanation endpoint.

Validates error code lookup and explanation retrieval.
"""


def test_rule_based_error_explain(client, headers):
    """Test that rule-based error explanation works."""
    res = client.post(
        "/api/v1/errors/explain",
        json={"error_code": "ZATCA-2001"},
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "error_code" in body
    assert "human_explanation" in body
    assert "technical_reason" in body
    assert "fix_suggestion" in body


def test_rule_based_error_explain_from_message(client, headers):
    """Test that error code can be extracted from error message."""
    res = client.post(
        "/api/v1/errors/explain",
        json={"error_message": "Error ZATCA-2001: Tax calculation mismatch"},
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "error_code" in body
    assert "human_explanation" in body


def test_rule_based_error_explain_unknown_code(client, headers):
    """Test that unknown error code returns generic explanation."""
    res = client.post(
        "/api/v1/errors/explain",
        json={"error_code": "ZATCA-9999"},
        headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "error_code" in body
    assert "human_explanation" in body


def test_list_error_codes(client, headers):
    """Test that error codes list endpoint works."""
    res = client.get("/api/v1/errors/codes", headers=headers)
    assert res.status_code == 200
    codes = res.json()
    assert isinstance(codes, list)
    assert len(codes) > 0

