"""
Tests for invoice submission and processing.

Validates invoice submission flow and response structure.
"""

from datetime import datetime


def test_invoice_submission(client, headers):
    """Test that invoice submission works correctly."""
    payload = {
        "mode": "PHASE_1",
        "environment": "SANDBOX",
        "invoice_number": "INV-TEST-001",
        "invoice_date": datetime.now().isoformat(),
        "seller_name": "Test Seller",
        "seller_tax_number": "123456789012345",
        "line_items": [
            {
                "name": "Test Item",
                "quantity": 1.0,
                "unit_price": 100.0,
                "tax_rate": 15.0,
                "tax_category": "S"
            }
        ],
        "total_tax_exclusive": 100.0,
        "total_tax_amount": 15.0,
        "total_amount": 115.0
    }
    
    res = client.post("/api/v1/invoices", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["invoice_number"] == "INV-TEST-001"
    assert "mode" in data
    assert "environment" in data


def test_invoice_submission_invalid_data(client, headers):
    """Test that invalid invoice data is rejected."""
    payload = {
        "mode": "PHASE_1",
        "environment": "SANDBOX",
        "invoice_number": "",  # Invalid: empty invoice number
        "invoice_date": datetime.now().isoformat(),
        "seller_name": "Test Seller",
        "seller_tax_number": "123456789012345",
        "line_items": [],
        "total_tax_exclusive": 100.0,
        "total_tax_amount": 15.0,
        "total_amount": 115.0
    }
    
    res = client.post("/api/v1/invoices", json=payload, headers=headers)
    assert res.status_code in (400, 422)  # Validation error


def test_invoice_submission_missing_required_fields(client, headers):
    """Test that missing required fields are rejected."""
    payload = {
        "mode": "PHASE_1",
        "environment": "SANDBOX"
        # Missing required fields
    }
    
    res = client.post("/api/v1/invoices", json=payload, headers=headers)
    assert res.status_code in (400, 422)  # Validation error

