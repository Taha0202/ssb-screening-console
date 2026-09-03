from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import Officer, Checkpoint
from app.core.security import get_password_hash
from app.schemas.officer import OfficerResponse, OfficerCreate, OfficerUpdate

router = APIRouter()

@router.get("", response_model=List[OfficerResponse])
def list_officers(
    checkpoint_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns personnel registry. Supports filtering by checkpoint_id and role.
    """
    query = db.query(Officer)
    if checkpoint_id:
        query = query.filter(Officer.checkpoint_id == checkpoint_id)
    if role:
        query = query.filter(Officer.role == role.upper())
    return query.order_by(Officer.badge_id.asc()).all()

@router.post("", response_model=OfficerResponse, status_code=status.HTTP_201_CREATED)
def create_officer(
    payload: OfficerCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new security officer / supervisor / analyst account.
    """
    existing = db.query(Officer).filter(
        Officer.badge_id == payload.badge_id.strip().upper()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Officer with badge ID '{payload.badge_id}' already exists."
        )

    cp_name = payload.checkpoint_location
    if payload.checkpoint_id:
        cp = db.query(Checkpoint).filter(Checkpoint.id == payload.checkpoint_id).first()
        if cp:
            cp_name = cp.name

    new_officer = Officer(
        badge_id=payload.badge_id.strip().upper(),
        full_name=payload.full_name.strip(),
        role=payload.role.upper(),
        checkpoint_id=payload.checkpoint_id,
        checkpoint_location=cp_name,
        password_hash=get_password_hash(payload.password),
        status=payload.status.upper()
    )
    db.add(new_officer)
    db.commit()
    db.refresh(new_officer)
    return new_officer

@router.get("/{officer_id}", response_model=OfficerResponse)
def get_officer_detail(
    officer_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns detail for a single officer by ID or Badge ID.
    """
    officer = db.query(Officer).filter(
        (Officer.id == officer_id) |
        (Officer.badge_id == officer_id)
    ).first()
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Officer '{officer_id}' not found."
        )
    return officer

@router.patch("/{officer_id}", response_model=OfficerResponse)
def update_officer(
    officer_id: str,
    payload: OfficerUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates officer assignment, role, or status.
    """
    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Officer '{officer_id}' not found."
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        officer.password_hash = get_password_hash(update_data.pop("password"))

    for field, val in update_data.items():
        if val is not None:
            setattr(officer, field, val.upper() if field in ["role", "status"] else val)

    if officer.checkpoint_id:
        cp = db.query(Checkpoint).filter(Checkpoint.id == officer.checkpoint_id).first()
        if cp:
            officer.checkpoint_location = cp.name

    db.commit()
    db.refresh(officer)
    return officer
