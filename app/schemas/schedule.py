from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any


class ScheduleEntryResponse(BaseModel):
    period: int
    period_date: date
    lease_payment: Decimal
    interest_expense: Decimal
    principal_reduction: Decimal
    lease_liability_beginning: Decimal
    lease_liability_ending: Decimal
    rou_asset_beginning: Decimal
    amortization: Decimal
    rou_asset_ending: Decimal
    total_expense: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ASC842ScheduleResponse(BaseModel):
    id: int
    lease_id: int
    initial_rou_asset: Decimal
    initial_lease_liability: Decimal
    total_payments: Decimal
    total_interest: Decimal
    total_amortization: Decimal
    schedule_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class IFRS16ScheduleResponse(BaseModel):
    id: int
    lease_id: int
    initial_rou_asset: Decimal
    initial_lease_liability: Decimal
    total_payments: Decimal
    total_interest: Decimal
    total_depreciation: Decimal
    schedule_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
