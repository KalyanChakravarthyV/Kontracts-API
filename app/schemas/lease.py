from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from app.models.lease import LeaseClassification


class LeaseBase(BaseModel):
    # Basic information
    lease_name: str = Field(..., description="Name/identifier for the lease")
    lessor_name: str = Field(..., description="Name of the lessor (vendor)")
    lessee_name: str = Field(..., description="Name of the lessee")

    # Contract management fields (merged from Contracts)
    contract_type: Optional[str] = Field(default=None, description="General contract type (lease, service, etc.)")
    status: str = Field(default="active", description="Contract status: active, expired, terminated, etc.")
    document_id: Optional[str] = Field(default=None, description="Link to associated document")

    # Lease terms
    commencement_date: date = Field(..., description="Lease commencement date")
    end_date: date = Field(..., description="Lease end date for calculating term")
    next_payment: Optional[datetime] = Field(default=None, description="Next payment due date")

    # Financial details
    periodic_payment: Decimal = Field(..., gt=0, description="Periodic lease payment amount")
    payment_frequency: str = Field(default="monthly", description="Payment frequency: monthly, quarterly, annual")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms description")
    initial_direct_costs: Decimal = Field(default=Decimal("0"), description="Initial direct costs")
    prepaid_rent: Decimal = Field(default=Decimal("0"), description="Prepaid rent amount")
    lease_incentives: Decimal = Field(default=Decimal("0"), description="Lease incentives received")
    residual_value: Decimal = Field(default=Decimal("0"), description="Residual value guarantee")

    # Discount rates (for lease accounting compliance)
    incremental_borrowing_rate: Decimal = Field(..., description="Incremental borrowing rate (IBR) as percent (e.g., 5 for 5%)")
    discount_rate: Optional[Decimal] = Field(default=None, description="Discount rate for IFRS 16 as percent (e.g., 5 for 5%)")

    # Classification
    classification: LeaseClassification = Field(default=LeaseClassification.OPERATING, description="Lease classification")


class LeaseCreate(LeaseBase):
    pass


class LeaseUpdate(BaseModel):
    lease_name: Optional[str] = None
    lessor_name: Optional[str] = None
    lessee_name: Optional[str] = None
    contract_type: Optional[str] = None
    status: Optional[str] = None
    document_id: Optional[str] = None
    commencement_date: Optional[date] = None
    end_date: Optional[date] = None
    next_payment: Optional[datetime] = None
    periodic_payment: Optional[Decimal] = None
    payment_frequency: Optional[str] = None
    payment_terms: Optional[str] = None
    initial_direct_costs: Optional[Decimal] = None
    prepaid_rent: Optional[Decimal] = None
    lease_incentives: Optional[Decimal] = None
    residual_value: Optional[Decimal] = None
    incremental_borrowing_rate: Optional[Decimal] = None
    discount_rate: Optional[Decimal] = None
    classification: Optional[LeaseClassification] = None


class LeaseResponse(LeaseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
