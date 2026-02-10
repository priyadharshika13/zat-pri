"""
Tests for health check endpoint.

Validates that the health endpoint returns correct status information.
"""


def test_health_check(client):
    """Test that health check endpoint returns correct status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"  # Based on actual endpoint implementation
    assert "version" in data
    assert "environment" in data

