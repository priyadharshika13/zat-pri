# Test Suite Documentation

## Overview

Comprehensive automated test suite for ZATCA Compliance API with high confidence testing without calling real external services.

## Test Structure

### Test Files

- `test_health_comprehensive.py` - Health endpoint tests
- `test_auth_comprehensive.py` - Authentication tests
- `test_plans_comprehensive.py` - Plans and subscription tests
- `test_invoice_safety.py` - Production safety guards (Phase 9)
- `test_invoice_processing.py` - Invoice processing with mocked services
- `test_retention.py` - Retention and compliance policy tests

### Fixtures (conftest.py)

- `async_client` - Async HTTP test client
- `db` - Function-scoped database session
- `test_tenant` - Test tenant fixture
- `test_api_key` - Test API key fixture
- `trial_plan` - Trial plan fixture
- `paid_plan` - Paid plan (Starter) fixture
- `test_subscription_trial` - Trial subscription
- `test_subscription_paid` - Paid subscription
- `mock_zatca_client` - Mocked ZATCA client
- `mock_httpx_client` - Mocked httpx for external calls

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=backend.app --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/backend/test_health_comprehensive.py
```

### Run Specific Test

```bash
pytest tests/backend/test_auth_comprehensive.py::test_valid_api_key
```

### Run with Verbose Output

```bash
pytest -v
```

## Test Coverage

Target: **> 80% coverage** for core logic

Current coverage areas:
- ✅ Health endpoints
- ✅ Authentication
- ✅ Plans and subscriptions
- ✅ Invoice safety guards
- ✅ Invoice processing (mocked)
- ✅ Retention service

## Mocking Rules

### External Services

**NEVER call real external services:**
- ZATCA APIs are mocked via `mock_zatca_client`
- AI provider (OpenRouter) is mocked via `mock_openrouter_service`
- HTTP calls are mocked via `mock_httpx_client`

### Mocking Patterns

```python
# Mock ZATCA client
with patch('app.integrations.zatca.sandbox.ZATCASandboxClient') as mock:
    mock_instance = AsyncMock()
    mock_instance.submit_for_clearance = AsyncMock(return_value={...})
    mock.return_value = mock_instance
```

## Test Isolation

- Each test uses a fresh database session
- Tests are independent (no order dependency)
- Fixtures use get-or-create pattern for UNIQUE constraints
- No shared state between tests

## Test Categories

### Unit Tests
- Test individual functions/methods
- Mock all dependencies
- Fast execution

### Integration Tests
- Test API endpoints
- Use test database
- Mock external services only

## Writing New Tests

### Example: Testing an Endpoint

```python
@pytest.mark.asyncio
async def test_my_endpoint(async_client, headers):
    """Test description."""
    response = await async_client.get("/api/v1/endpoint", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Example: Testing with Mocks

```python
@pytest.mark.asyncio
async def test_with_mock(async_client, mock_zatca_client):
    """Test with mocked external service."""
    with patch('app.services.my_service') as mock_service:
        mock_service.return_value = {"result": "success"}
        response = await async_client.post("/api/v1/endpoint")
        assert response.status_code == 200
```

## Best Practices

1. **Clear Test Names**: Use descriptive names like `test_trial_plan_production_blocked`
2. **Arrange-Act-Assert**: Structure tests clearly
3. **Test Behavior**: Assert behavior, not implementation
4. **Isolation**: Each test should be independent
5. **Mocking**: Mock external services, not internal logic
6. **Coverage**: Aim for > 80% coverage on core logic

## Troubleshooting

### Database Issues

If tests fail with database errors:
- Ensure test database is in-memory SQLite
- Check that fixtures are properly scoped
- Verify UNIQUE constraints are handled

### Async Issues

If async tests fail:
- Ensure `@pytest.mark.asyncio` decorator is used
- Use `async_client` fixture for async endpoints
- Check that mocks are async-compatible

### Import Errors

If imports fail:
- Ensure backend directory is in Python path (handled in conftest.py)
- Check that all dependencies are installed
- Verify virtual environment is activated
- Run tests from project root: `pytest` or use `scripts/run_tests.sh`

## Continuous Integration

Tests should run in CI/CD pipeline:
- Run on every commit
- Fail build if tests fail
- Generate coverage reports
- Block merge if coverage < 80%

## Notes

- All external services are mocked
- Tests use in-memory SQLite database
- No real API keys or secrets needed
- Tests are deterministic and fast

