from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class LeaseClassification(str, enum.Enum):
    FINANCE = "finance"
    OPERATING = "operating"


class Lease(Base):
    __tablename__ = "leases"
    __table_args__ = {"schema": "kontracts"}

    id = Column(Integer, primary_key=True, index=True)

    # Basic information (merged from Contracts)
    lease_name = Column(String, nullable=False, index=True)  # Previously 'name' in Contracts
    lessor_name = Column(String, nullable=False)  # Previously 'vendor' in Contracts
    lessee_name = Column(String, nullable=False)

    # Contract management fields (from Contracts model)
    contract_type = Column(String, nullable=True)  # General contract type (lease, service, etc.)
    status = Column(String, default="active")  # active, expired, terminated, etc.
    document_id = Column(String, nullable=True)  # Link to associated document

    # Lease terms
    commencement_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    next_payment = Column(DateTime, nullable=True)  # From Contracts - next payment due date

    # Financial details
    periodic_payment = Column(Numeric(15, 2), nullable=False)  # Previously 'amount' in Contracts
    payment_frequency = Column(String, default="monthly")  # monthly, quarterly, annual
    payment_terms = Column(String, nullable=True)  # From Contracts - payment terms description
    initial_direct_costs = Column(Numeric(15, 2), default=0)
    prepaid_rent = Column(Numeric(15, 2), default=0)
    lease_incentives = Column(Numeric(15, 2), default=0)
    residual_value = Column(Numeric(15, 2), default=0)

    # Discount rates (for lease accounting compliance)
    incremental_borrowing_rate = Column(Numeric(8, 6), nullable=False)  # IBR for ASC 842
    discount_rate = Column(Numeric(8, 6), nullable=True)  # For IFRS 16

    # Classification
    classification = Column(SQLEnum(LeaseClassification), default=LeaseClassification.OPERATING)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    asc842_schedules = relationship("ASC842Schedule", back_populates="lease", cascade="all, delete-orphan")
    ifrs16_schedules = relationship("IFRS16Schedule", back_populates="lease", cascade="all, delete-orphan")
    schedule_entries = relationship("LeaseScheduleEntry", back_populates="lease", cascade="all, delete-orphan")


class LeaseScheduleEntry(Base):
    __tablename__ = "lease_schedule_entries"
    __table_args__ = {"schema": "kontracts"}

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("kontracts.leases.id"), nullable=False)
    schedule_type = Column(String, nullable=False)  # ASC842 or IFRS16
    period = Column(Integer, nullable=False)
    period_date = Column(Date, nullable=False)

    # Common fields
    lease_payment = Column(Numeric(15, 2), nullable=False)
    interest_expense = Column(Numeric(15, 2), nullable=False)
    principal_reduction = Column(Numeric(15, 2), nullable=False)
    lease_liability_beginning = Column(Numeric(15, 2), nullable=False)
    lease_liability_ending = Column(Numeric(15, 2), nullable=False)

    # ROU Asset tracking
    rou_asset_beginning = Column(Numeric(15, 2), nullable=False)
    amortization = Column(Numeric(15, 2), nullable=False)
    rou_asset_ending = Column(Numeric(15, 2), nullable=False)

    # Total expense (for operating leases)
    total_expense = Column(Numeric(15, 2))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lease = relationship("Lease", back_populates="schedule_entries")
