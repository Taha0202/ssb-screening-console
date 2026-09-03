from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import Checkpoint
from app.schemas.checkpoint import CheckpointResponse, CheckpointCreate, CheckpointUpdate

router = APIRouter()

@router.get("", response_model=List[CheckpointResponse])
def list_checkpoints(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    """
    Returns all registered border screening checkpoints.
    Supports filtering by operational status ('ACTIVE', 'INACTIVE', 'MAINTENANCE').
    """
    query = db.query(Checkpoint)
    if status_filter:
        query = query.filter(Checkpoint.status == status_filter.upper())
    return query.order_by(Checkpoint.checkpoint_code.asc()).all()

@router.post("", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
def create_checkpoint(
    payload: CheckpointCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new border screening checkpoint unit.
    Ensures unique checkpoint_code.
    """
    existing = db.query(Checkpoint).filter(
        Checkpoint.checkpoint_code == payload.checkpoint_code.strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Checkpoint code '{payload.checkpoint_code}' already exists."
        )

    new_cp = Checkpoint(
        checkpoint_code=payload.checkpoint_code.strip().upper(),
        name=payload.name.strip(),
        location=payload.location.strip(),
        state=payload.state.strip(),
        district=payload.district.strip(),
        status=payload.status.upper()
    )
    db.add(new_cp)
    db.commit()
    db.refresh(new_cp)
    return new_cp

@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
def get_checkpoint_detail(
    checkpoint_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns detail for a single checkpoint by ID or unique code.
    """
    cp = db.query(Checkpoint).filter(
        (Checkpoint.id == checkpoint_id) |
        (Checkpoint.checkpoint_code == checkpoint_id)
    ).first()
    if not cp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint '{checkpoint_id}' not found."
        )
    return cp

@router.patch("/{checkpoint_id}", response_model=CheckpointResponse)
def update_checkpoint(
    checkpoint_id: str,
    payload: CheckpointUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates checkpoint parameters or status.
    """
    cp = db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
    if not cp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint '{checkpoint_id}' not found."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(cp, field, val.upper() if field == "status" else val)

    db.commit()
    db.refresh(cp)
    return cp
