# Lease Accounting API

A FastAPI-based application for generating ASC 842 and IFRS 16 lease accounting schedules with PostgreSQL persistence.

## Features

- **ASC 842 Compliance**: Generate lease schedules compliant with US GAAP ASC 842
- **IFRS 16 Compliance**: Generate lease schedules compliant with IFRS 16
- **Finance & Operating Leases**: Support for both lease classifications under ASC 842
- **Payment Management**: Track and manage lease payments with status tracking and summaries
- **PostgreSQL Persistence**: All lease data, schedules, and payments stored in PostgreSQL
- **RESTful API**: Clean API design with automatic documentation
- **Docker Deployment**: Complete containerization with Docker and docker-compose

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Server**: Uvicorn 0.30.6
- **Database**: PostgreSQL with SQLAlchemy 2.0.45
- **Migrations**: Alembic 1.13.3
- **Validation**: Pydantic 2.12.5
- **Data Processing**: Pandas 2.3.3, NumPy 2.4.0
- **Deployment**: Docker & Docker Compose
- **Python**: 3.11+

## Domain Knowledge

### Lease Accounting Standards

#### ASC 842 (US GAAP)
- Finance Leases: Front-loaded expense recognition (interest + amortization)
- Operating Leases: Straight-line total expense recognition (interest + amortization combined)
- Right-of-Use (ROU) Asset and Lease Liability recognition
- Incremental Borrowing Rate (IBR) for present value calculations

#### IFRS 16 (International)
- Single model approach (all leases treated similarly)
- Straight-line depreciation of ROU Asset
- Interest expense using effective interest method
- Front-loaded expense pattern
- Uses discount rate (typically IBR) for present value calculations

## Project Structure

```
lease-accounting-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── leases.py          # Lease CRUD endpoints
│   │       ├── schedules.py       # Schedule generation endpoints
│   │       └── payments.py        # Payment management endpoints
│   ├── models/
│   │   ├── lease.py               # Lease ORM models
│   │   ├── schedule.py            # Schedule ORM models
│   │   └── journals.py            # Payment and journal ORM models
│   ├── schemas/
│   │   ├── lease.py               # Pydantic schemas for leases
│   │   ├── schedule.py            # Pydantic schemas for schedules
│   │   └── journals.py            # Pydantic schemas for payments
│   ├── services/
│   │   ├── asc842_calculator.py   # ASC 842 calculation logic
│   │   └── ifrs16_calculator.py   # IFRS 16 calculation logic
│   ├── database.py                # Database configuration
│   └── main.py                    # FastAPI application
├── alembic/                       # Database migrations
├── tests/                         # Test files
├── Dockerfile                     # Docker image configuration
├── docker-compose.yml             # Docker Compose setup
├── pyproject.toml                 # Python dependencies
└── README.md
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker

1. Clone the repository and navigate to the project directory:
```bash
cd lease-accounting-api
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Start the application:
```bash
docker-compose up -d
```

4. Access the API:
- API: http://localhost:8001
- Interactive docs: http://localhost:8001/docs
- Alternative docs: http://localhost:8001/redoc

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install .
```

3. Set up PostgreSQL and update the DATABASE_URL in .env

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn app.main:app --reload
```

## Development Guidelines

- Keep business logic in `app/services/`, not in API endpoints.
- Use Pydantic models for request/response validation.
- Use type hints for function parameters and returns.
- Add short comments only when logic is non-obvious.

## API Usage Examples

### 1. Create a Lease

```bash
curl -X POST "http://localhost:8001/api/v1/leases/" \
  -H "Content-Type: application/json" \
  -d '{
    "lease_name": "Office Building Lease",
    "lessor_name": "ABC Properties",
    "lessee_name": "XYZ Corporation",
    "commencement_date": "2024-01-01",
    "lease_term_months": 60,
    "periodic_payment": 10000.00,
    "payment_frequency": "monthly",
    "initial_direct_costs": 5000.00,
    "prepaid_rent": 10000.00,
    "lease_incentives": 2000.00,
    "residual_value": 0.00,
    "incremental_borrowing_rate": 0.05,
    "discount_rate": 0.05,
    "classification": "operating"
  }'
```

### 2. Generate ASC 842 Schedule

```bash
curl -X POST "http://localhost:8001/api/v1/schedules/asc842/1"
```

### 3. Generate IFRS 16 Schedule

```bash
curl -X POST "http://localhost:8001/api/v1/schedules/ifrs16/1"
```

### 4. Get Schedule Details

```bash
# Get ASC 842 schedule entries
curl "http://localhost:8001/api/v1/schedules/entries/1/asc842"

# Get IFRS 16 schedule entries
curl "http://localhost:8001/api/v1/schedules/entries/1/ifrs16"
```

### 5. List All Leases

```bash
curl "http://localhost:8001/api/v1/leases/"
```

### 6. Create a Payment

```bash
curl -X POST "http://localhost:8001/api/v1/payments/" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "lease-001",
    "amount": 5000.00,
    "due_date": "2025-11-15T00:00:00",
    "status": "Scheduled"
  }'
```

### 7. Mark Payment as Paid

```bash
curl -X POST "http://localhost:8001/api/v1/payments/{payment_id}/mark-paid"
```

### 8. Get Payment Summary for Contract

```bash
curl "http://localhost:8001/api/v1/payments/contract/lease-001/summary"
```

## API Endpoints

### Leases
- `POST /api/v1/leases/` - Create a new lease
- `GET /api/v1/leases/` - List all leases
- `GET /api/v1/leases/{lease_id}` - Get specific lease
- `PUT /api/v1/leases/{lease_id}` - Update lease
- `DELETE /api/v1/leases/{lease_id}` - Delete lease

### Schedules
- `POST /api/v1/schedules/asc842/{lease_id}` - Generate ASC 842 schedule
- `POST /api/v1/schedules/ifrs16/{lease_id}` - Generate IFRS 16 schedule
- `GET /api/v1/schedules/asc842/{lease_id}` - Get ASC 842 schedule summary
- `GET /api/v1/schedules/ifrs16/{lease_id}` - Get IFRS 16 schedule summary
- `GET /api/v1/schedules/entries/{lease_id}/asc842` - Get ASC 842 detailed entries
- `GET /api/v1/schedules/entries/{lease_id}/ifrs16` - Get IFRS 16 detailed entries
- `DELETE /api/v1/schedules/asc842/{lease_id}` - Delete ASC 842 schedule
- `DELETE /api/v1/schedules/ifrs16/{lease_id}` - Delete IFRS 16 schedule

### Payments
- `POST /api/v1/payments/` - Create a new payment
- `GET /api/v1/payments/` - List all payments with filtering and sorting
- `GET /api/v1/payments/{payment_id}` - Get specific payment
- `PUT /api/v1/payments/{payment_id}` - Update payment
- `DELETE /api/v1/payments/{payment_id}` - Delete payment
- `POST /api/v1/payments/{payment_id}/mark-paid` - Mark payment as paid
- `GET /api/v1/payments/contract/{contract_id}/summary` - Get payment summary for contract

#### Payment Filtering & Sorting
Query parameters for `GET /api/v1/payments/`:
- `contract_id` - Filter by contract/lease ID
- `status` - Filter by payment status (Scheduled, Paid, etc.)
- `sort_by` - Sort by any field (default: due_date)
- `sort_order` - Sort order: asc or desc (default: asc)
- `skip` - Number of records to skip (pagination)
- `limit` - Maximum records to return (default: 100, max: 1000)

## Database Schema

### Leases Table
Stores lease contract information including terms, payments, and discount rates.

### ASC842 Schedules Table
Stores summary information for ASC 842 calculations.

### IFRS16 Schedules Table
Stores summary information for IFRS 16 calculations.

### Lease Schedule Entries Table
Stores detailed period-by-period amortization schedules for both standards.

### Payments Table
Stores payment records for leases and contracts with tracking information:
- Payment amounts and due dates
- Payment status (Scheduled, Paid, Overdue, etc.)
- Paid date tracking
- Association with contracts/leases

### Key Calculations

#### Present Value of Lease Payments
```
PV = PMT × [(1 - (1 + r)^-n) / r] + RV / (1 + r)^n
```

Where:
- PMT = Periodic payment
- r = Periodic discount rate
- n = Number of periods
- RV = Residual value

#### Initial Measurements
```
Lease Liability = PV of lease payments
ROU Asset = Lease Liability + Initial Direct Costs + Prepaid Rent - Lease Incentives
```

#### Finance Lease (ASC 842)
```
Interest Expense = Beginning Lease Liability × Periodic Rate
Principal Reduction = Payment - Interest Expense
Amortization = ROU Asset / Lease Term (straight-line)
Total Expense = Interest Expense + Amortization
```

#### Operating Lease (ASC 842)
```
Total Lease Cost = Sum of all payments + Initial Direct Costs
Straight-line Expense = Total Lease Cost / Lease Term
Amortization = Straight-line Expense - Interest Expense
Interest Expense = Beginning Lease Liability × Periodic Rate
```

#### IFRS 16
```
Interest Expense = Beginning Lease Liability × Discount Rate
Depreciation = ROU Asset / Lease Term (straight-line)
Total Expense = Interest Expense + Depreciation
```

## Business Logic Notes

### Payment Frequencies
- Monthly: 12 periods per year
- Quarterly: 4 periods per year
- Annual: 1 period per year
- Periodic rate = annual rate / periods per year

### Lease Classification (ASC 842)
- Finance lease if any of:
  - Transfer of ownership at end
  - Purchase option reasonably certain to exercise
  - Lease term ≥ major part of economic life (typically 75%)
  - PV of payments ≥ substantially all of fair value (typically 90%)
  - Asset is specialized with no alternative use
- Operating lease if none of the above criteria are met

## Debugging Calculations

- Check intermediate values (PV, initial liability, initial ROU asset).
- Verify periodic rates are derived from annual rates and payment frequency.
- Ensure running balances decrease properly over the lease term.
- Confirm total interest + principal equals total payments.
- Verify ending liability approaches zero.

## Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_USER`: Database user (`kontracts_user`)
- `POSTGRES_PASSWORD`: Database password (`kontracts_user_pwd`)
- `POSTGRES_DB`: Database name (`Kontracts`)

## Environment Setup Notes

- Docker Compose sets up PostgreSQL automatically.
- Local development requires a PostgreSQL instance and a configured `.env`.
- Do not commit `.env` files; use `.env.example` as a template.

## Common Tasks

### Adding a New Lease Field
1. Update ORM model in `app/models/lease.py`.
2. Update Pydantic schema in `app/schemas/lease.py`.
3. Generate an Alembic migration and apply it.
4. Update calculation services if the field affects calculations.

### Adding a New Calculation Standard
1. Add a new calculator service in `app/services/`.
2. Add ORM models for the schedule type.
3. Add Pydantic schemas for the schedule type.
4. Add API endpoints in `app/api/v1/schedules.py`.
5. Create and apply a migration.

## Testing

Interactive API documentation is available at `/docs` where you can test all endpoints directly in your browser.

## Known Limitations

- Variable lease payments are not supported yet.
- Lease modifications require deleting and recreating schedules.
- Short-term lease exemption (<12 months) is not supported.
- Low-value asset exemption is not supported.
- Residual value guarantees are simplified in calculations.
- Sale-leaseback transactions are not supported.
- Payment frequency changes during a lease term are not supported.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
