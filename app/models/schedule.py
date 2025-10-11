from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ASC842Schedule(Base):
    __tablename__ = "asc842_schedules"
    __table_args__ = {"schema": "kontracts"}

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("kontracts.leases.id"), nullable=False)

    # Initial measurements
    initial_rou_asset = Column(Numeric(15, 2), nullable=False)
    initial_lease_liability = Column(Numeric(15, 2), nullable=False)

    # Summary totals
    total_payments = Column(Numeric(15, 2), nullable=False)
    total_interest = Column(Numeric(15, 2), nullable=False)
    total_amortization = Column(Numeric(15, 2), nullable=False)

    # Schedule data stored as JSON for flexibility
    schedule_data = Column(JSON)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lease = relationship("Lease", back_populates="asc842_schedules")


class IFRS16Schedule(Base):
    __tablename__ = "ifrs16_schedules"
    __table_args__ = {"schema": "kontracts"}

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("kontracts.leases.id"), nullable=False)

    # Initial measurements
    initial_rou_asset = Column(Numeric(15, 2), nullable=False)
    initial_lease_liability = Column(Numeric(15, 2), nullable=False)

    # Summary totals
    total_payments = Column(Numeric(15, 2), nullable=False)
    total_interest = Column(Numeric(15, 2), nullable=False)
    total_depreciation = Column(Numeric(15, 2), nullable=False)

    # Schedule data stored as JSON for flexibility
    schedule_data = Column(JSON)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lease = relationship("Lease", back_populates="ifrs16_schedules")
