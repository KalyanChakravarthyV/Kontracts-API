from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.lease import Lease
from app.schemas.lease import LeaseCreate, LeaseUpdate, LeaseResponse
from app.auth import get_current_user

# , dependencies=[Depends(get_current_user)]
router = APIRouter(prefix="/leases", tags=["Leases"], dependencies=[Depends(get_current_user)])

@router.post("/", response_model=LeaseResponse, status_code=status.HTTP_201_CREATED)
def create_lease(
    lease_data: LeaseCreate,
    db: Session = Depends(get_db)
):
    """Create a new lease"""
    lease = Lease(**lease_data.model_dump())
    db.add(lease)
    db.commit()
    db.refresh(lease)
    return lease


@router.get("/", response_model=List[LeaseResponse])
def list_leases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all leases"""
    leases = db.query(Lease).offset(skip).limit(limit).all()
    return leases


@router.get("/{lease_id}", response_model=LeaseResponse)
def get_lease(
    lease_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific lease by ID"""
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with id {lease_id} not found"
        )
    return lease


@router.put("/{lease_id}", response_model=LeaseResponse)
def update_lease(
    lease_id: int,
    lease_data: LeaseUpdate,
    db: Session = Depends(get_db)
):
    """Update a lease"""
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with id {lease_id} not found"
        )

    update_data = lease_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lease, field, value)

    db.commit()
    db.refresh(lease)
    return lease


@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lease(
    lease_id: int,
    db: Session = Depends(get_db)
):
    """Delete a lease"""
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with id {lease_id} not found"
        )

    db.delete(lease)
    db.commit()
    return None
