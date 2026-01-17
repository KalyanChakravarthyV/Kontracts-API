# Test Suite

Comprehensive test suite for the Lease Accounting API following Python and PostgreSQL best practices.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Unit tests for database models
├── test_api_leases.py       # API tests for lease endpoints
├── test_api_schedules.py    # API tests for schedule endpoints
└── test_calculators.py      # Integration tests for calculators
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api          # API tests only
pytest -m database     # Database tests only
```

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.database` - Database tests
- `@pytest.mark.calculator` - Calculator service tests
- `@pytest.mark.slow` - Slow-running tests

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/test_models.py

# Run a specific test class
pytest tests/test_models.py::TestLeaseModel

# Run a specific test function
pytest tests/test_models.py::TestLeaseModel::test_create_lease_operating

# Run tests matching a pattern
pytest -k "lease"

# Exclude slow tests
pytest -m "not slow"
```

## Test Database Configuration

### Ephemeral PostgreSQL (Testcontainers)

**IMPORTANT:** This project uses PostgreSQL-specific features (schemas, JSONB, functions like `gen_random_uuid()` and `now()`).

The test suite starts a persistent PostgreSQL container via `testcontainers` and applies Alembic migrations automatically.

Configure the container in `tests/.env.test`:

```bash
# tests/.env.test
TEST_POSTGRES_IMAGE=postgres:15-alpine
TEST_POSTGRES_DB=kontracts_test
TEST_POSTGRES_USER=kontracts
TEST_POSTGRES_PASSWORD=kontracts
```

The test suite automatically:
- Starts (or reuses) the container using `tests/.env.test`
- Creates the kontracts schema
- Runs Alembic migrations to set up the schema
- Rolls back transactions after each test for isolation

Note: Testcontainers reuse is enabled for the test PostgreSQL container. If you want to stop and remove it manually, use Docker to remove the container by name or label.

**Setup:**

1. Ensure Docker is running
2. Configure `tests/.env.test`
3. Run tests:

```bash
pytest
```

### Best Practices

1. **Separate Test Database**: Always use a dedicated test database
2. **Transaction Rollback**: Tests use transactions that rollback, ensuring isolation
3. **Clean State**: Each test starts with a clean database state
4. **Parallel Execution**: Tests can run in parallel with pytest-xdist

## Test Coverage

View coverage report:

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html
```

Target coverage: **>80%** for all modules

## Writing New Tests

### Model Tests

```python
@pytest.mark.unit
@pytest.mark.database
def test_my_model(db_session):
    model = MyModel(field="value")
    db_session.add(model)
    db_session.commit()
    assert model.id is not None
```

### API Tests

```python
@pytest.mark.api
def test_my_endpoint(client):
    response = client.get("/api/v1/endpoint")
    assert response.status_code == 200
```

### Calculator Tests

```python
@pytest.mark.integration
@pytest.mark.calculator
def test_calculation(db_session, sample_lease):
    calculator = MyCalculator(sample_lease)
    result = calculator.calculate()
    assert result > 0
```

## Fixtures

Common fixtures available in `conftest.py`:

- `engine` - Database engine (session scope)
- `db_session` - Database session with transaction rollback (function scope)
- `client` - FastAPI test client (function scope)
- `sample_lease_data` - Sample lease data dictionary
- `sample_lease` - Created lease instance in database
- `sample_finance_lease_data` - Sample finance lease data
- `sample_finance_lease` - Created finance lease in database
- `sample_user_data` - Sample user data
- `sample_user` - Created user in database
- `sample_journal_entry_data` - Sample journal entry data

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml
```

## PostgreSQL Best Practices Implemented

1. **Schema Isolation**: Tests use `kontracts` schema
2. **Transaction Rollback**: Each test runs in a transaction that rolls back
3. **Connection Pooling**: Proper connection pool management
4. **Cascade Deletes**: Tests verify cascade delete behavior
5. **Constraint Testing**: Tests verify database constraints
6. **Index Usage**: Tests can verify query performance

## Debugging Tests

```bash
# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Increase verbosity for SQL queries
# (set echo=True in conftest.py engine creation)
```

## Performance Tips

1. Use SQLite in-memory for unit tests (fast)
2. Use PostgreSQL for integration tests (realistic)
3. Run slow tests separately: `pytest -m "not slow"`
4. Use `pytest-xdist` for parallel execution:
   ```bash
   pip install pytest-xdist
   pytest -n auto
   ```

## Common Issues

### Import Errors

Make sure the project root is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Errors

Verify Docker is running and `tests/.env.test` is present with valid settings.

### Schema Issues

Ensure the kontracts schema exists:
```sql
CREATE SCHEMA IF NOT EXISTS kontracts;
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
