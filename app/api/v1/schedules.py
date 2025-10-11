from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.lease import Lease, LeaseScheduleEntry
from app.models.schedule import ASC842Schedule, IFRS16Schedule
from app.schemas.schedule import ASC842ScheduleResponse, IFRS16ScheduleResponse, ScheduleEntryResponse
from app.services.asc842_calculator import ASC842Calculator
from app.services.ifrs16_calculator import IFRS16Calculator

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.post("/asc842/{lease_id}", response_model=ASC842ScheduleResponse, status_code=status.HTTP_201_CREATED)
def generate_asc842_schedule(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Generate ASC 842 lease schedule for a specific lease"""
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with id {lease_id} not found"
        )

    # Check if schedule already exists
    existing_schedule = db.query(ASC842Schedule).filter(ASC842Schedule.lease_id == lease_id).first()
    if existing_schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ASC 842 schedule already exists for lease {lease_id}. Delete it first to regenerate."
        )

    calculator = ASC842Calculator(lease)
    schedule = calculator.generate_schedule(db)
    return schedule


@router.post("/ifrs16/{lease_id}", response_model=IFRS16ScheduleResponse, status_code=status.HTTP_201_CREATED)
def generate_ifrs16_schedule(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Generate IFRS 16 lease schedule for a specific lease"""
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with id {lease_id} not found"
        )

    # Check if schedule already exists
    existing_schedule = db.query(IFRS16Schedule).filter(IFRS16Schedule.lease_id == lease_id).first()
    if existing_schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"IFRS 16 schedule already exists for lease {lease_id}. Delete it first to regenerate."
        )

    calculator = IFRS16Calculator(lease)
    schedule = calculator.generate_schedule(db)
    return schedule


@router.get("/asc842/{lease_id}", response_model=ASC842ScheduleResponse)
def get_asc842_schedule(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Get ASC 842 schedule for a specific lease"""
    schedule = db.query(ASC842Schedule).filter(ASC842Schedule.lease_id == lease_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ASC 842 schedule not found for lease {lease_id}"
        )
    return schedule


@router.get("/ifrs16/{lease_id}", response_model=IFRS16ScheduleResponse)
def get_ifrs16_schedule(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Get IFRS 16 schedule for a specific lease"""
    schedule = db.query(IFRS16Schedule).filter(IFRS16Schedule.lease_id == lease_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IFRS 16 schedule not found for lease {lease_id}"
        )
    return schedule


@router.get("/entries/{lease_id}/asc842", response_model=List[ScheduleEntryResponse])
def get_asc842_entries(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed schedule entries for ASC 842 lease"""
    entries = db.query(LeaseScheduleEntry).filter(
        LeaseScheduleEntry.lease_id == lease_id,
        LeaseScheduleEntry.schedule_type == "ASC842"
    ).order_by(LeaseScheduleEntry.period).all()

    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ASC 842 schedule entries found for lease {lease_id}"
        )
    return entries


@router.get("/entries/{lease_id}/ifrs16", response_model=List[ScheduleEntryResponse])
def get_ifrs16_entries(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed schedule entries for IFRS 16 lease"""
    entries = db.query(LeaseScheduleEntry).filter(
        LeaseScheduleEntry.lease_id == lease_id,
        LeaseScheduleEntry.schedule_type == "IFRS16"
    ).order_by(LeaseScheduleEntry.period).all()

    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No IFRS 16 schedule entries found for lease {lease_id}"
        )
    return entries


@router.delete("/asc842/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asc842_schedule(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Delete ASC 842 schedule and entries for a lease"""
    schedule = db.query(ASC842Schedule).filter(ASC842Schedule.lease_id == lease_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ASC 842 schedule not found for lease {lease_id}"
        )

    # Delete schedule entries
    db.query(LeaseScheduleEntry).filter(
        LeaseScheduleEntry.lease_id == lease_id,
        LeaseScheduleEntry.schedule_type == "ASC842"
    ).delete()

    # Delete schedule
    db.delete(schedule)
    db.commit()
    return None


@router.delete("/ifrs16/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ifrs16_schedule(
    lease_id: int,
    db: Session = Depends(get_db),
):
    """Delete IFRS 16 schedule and entries for a lease"""
    schedule = db.query(IFRS16Schedule).filter(IFRS16Schedule.lease_id == lease_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IFRS 16 schedule not found for lease {lease_id}"
        )

    # Delete schedule entries
    db.query(LeaseScheduleEntry).filter(
        LeaseScheduleEntry.lease_id == lease_id,
        LeaseScheduleEntry.schedule_type == "IFRS16"
    ).delete()

    # Delete schedule
    db.delete(schedule)
    db.commit()
    return None
