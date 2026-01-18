from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from io import BytesIO
import pandas as pd

from app.database import get_db
from app.models.lease import Lease, LeaseScheduleEntry
from app.models.schedule import ASC842Schedule, IFRS16Schedule
from app.schemas.schedule import ASC842ScheduleResponse, IFRS16ScheduleResponse, ScheduleEntryResponse
from app.services.asc842_calculator import ASC842Calculator
from app.services.ifrs16_calculator import IFRS16Calculator
from app.auth_utils import VerifyToken 

auth = VerifyToken()  # Create an instance of the VerifyToken class

router = APIRouter(prefix="/schedules", tags=["Schedules"], dependencies=[Depends(auth.verify)])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MEDIA_TYPE = "text/csv"


def _entries_to_frame(entries: List[LeaseScheduleEntry]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "period": entry.period,
                "period_date": entry.period_date,
                "lease_payment": entry.lease_payment,
                "interest_expense": entry.interest_expense,
                "principal_reduction": entry.principal_reduction,
                "lease_liability_beginning": entry.lease_liability_beginning,
                "lease_liability_ending": entry.lease_liability_ending,
                "rou_asset_beginning": entry.rou_asset_beginning,
                "amortization": entry.amortization,
                "rou_asset_ending": entry.rou_asset_ending,
                "total_expense": entry.total_expense,
            }
            for entry in entries
        ]
    )


def _schedule_summary_to_frame(schedule, schedule_type: str) -> pd.DataFrame:
    summary = {
        "schedule_type": schedule_type,
        "schedule_id": schedule.id,
        "lease_id": schedule.lease_id,
        "initial_rou_asset": schedule.initial_rou_asset,
        "initial_lease_liability": schedule.initial_lease_liability,
        "total_payments": schedule.total_payments,
        "total_interest": schedule.total_interest,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
    }
    if schedule_type == "ASC842":
        summary["total_amortization"] = schedule.total_amortization
    else:
        summary["total_depreciation"] = schedule.total_depreciation
    return pd.DataFrame([summary])


def _excel_response(frames: dict[str, pd.DataFrame], filename: str) -> StreamingResponse:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, frame in frames.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(output, media_type=EXCEL_MEDIA_TYPE, headers=headers)

def _csv_response(frame: pd.DataFrame, filename: str) -> Response:
    csv_data = frame.to_csv(index=False)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_data, media_type=CSV_MEDIA_TYPE, headers=headers)


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
    format: str = Query("json", description="Return json or excel"),
    db: Session = Depends(get_db),
):
    """Get ASC 842 schedule for a specific lease"""
    schedule = db.query(ASC842Schedule).filter(ASC842Schedule.lease_id == lease_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ASC 842 schedule not found for lease {lease_id}"
        )
    if format.lower() == "excel":
        entries = db.query(LeaseScheduleEntry).filter(
            LeaseScheduleEntry.lease_id == lease_id,
            LeaseScheduleEntry.schedule_type == "ASC842"
        ).order_by(LeaseScheduleEntry.period).all()
        frames = {
            "summary": _schedule_summary_to_frame(schedule, "ASC842"),
            "entries": _entries_to_frame(entries),
        }
        return _excel_response(frames, f"asc842_schedule_{lease_id}.xlsx")
    if format.lower() == "csv":
        return _csv_response(
            _schedule_summary_to_frame(schedule, "ASC842"),
            f"asc842_schedule_{lease_id}.csv",
        )
    return schedule


@router.get("/ifrs16/{lease_id}", response_model=IFRS16ScheduleResponse)
def get_ifrs16_schedule(
    lease_id: int,
    format: str = Query("json", description="Return json or excel"),
    db: Session = Depends(get_db),
):
    """Get IFRS 16 schedule for a specific lease"""
    schedule = db.query(IFRS16Schedule).filter(IFRS16Schedule.lease_id == lease_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IFRS 16 schedule not found for lease {lease_id}"
        )
    if format.lower() == "excel":
        entries = db.query(LeaseScheduleEntry).filter(
            LeaseScheduleEntry.lease_id == lease_id,
            LeaseScheduleEntry.schedule_type == "IFRS16"
        ).order_by(LeaseScheduleEntry.period).all()
        frames = {
            "summary": _schedule_summary_to_frame(schedule, "IFRS16"),
            "entries": _entries_to_frame(entries),
        }
        return _excel_response(frames, f"ifrs16_schedule_{lease_id}.xlsx")
    if format.lower() == "csv":
        return _csv_response(
            _schedule_summary_to_frame(schedule, "IFRS16"),
            f"ifrs16_schedule_{lease_id}.csv",
        )
    return schedule


@router.get("/entries/{lease_id}/asc842", response_model=List[ScheduleEntryResponse])
def get_asc842_entries(
    lease_id: int,
    format: str = Query("json", description="Return json or excel"),
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
    if format.lower() == "excel":
        frames = {"entries": _entries_to_frame(entries)}
        return _excel_response(frames, f"asc842_entries_{lease_id}.xlsx")
    if format.lower() == "csv":
        return _csv_response(
            _entries_to_frame(entries),
            f"asc842_entries_{lease_id}.csv",
        )
    return entries


@router.get("/entries/{lease_id}/ifrs16", response_model=List[ScheduleEntryResponse])
def get_ifrs16_entries(
    lease_id: int,
    format: str = Query("json", description="Return json or excel"),
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
    if format.lower() == "excel":
        frames = {"entries": _entries_to_frame(entries)}
        return _excel_response(frames, f"ifrs16_entries_{lease_id}.xlsx")
    if format.lower() == "csv":
        return _csv_response(
            _entries_to_frame(entries),
            f"ifrs16_entries_{lease_id}.csv",
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
