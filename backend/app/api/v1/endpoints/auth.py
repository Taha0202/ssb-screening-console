from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import Officer, Checkpoint
from app.core.security import verify_password
from app.schemas.user import LoginRequest, TokenResponse, UserResponse

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    officer = db.query(Officer).filter(Officer.badge_id == payload.badge_id.strip()).first()
    if not officer or not verify_password(payload.password, officer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Badge ID or Password. Please try again."
        )

    if officer.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Personnel account '{officer.badge_id}' is {officer.status}. Contact checkpoint supervisor."
        )

    # Update last login timestamp
    officer.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(officer)

    # Resolve Checkpoint Location Name
    cp_loc = officer.checkpoint_location
    if officer.checkpoint_id:
        cp = db.query(Checkpoint).filter(Checkpoint.id == officer.checkpoint_id).first()
        if cp:
            cp_loc = cp.name

    user_resp = UserResponse(
        id=officer.id,
        badge_id=officer.badge_id,
        full_name=officer.full_name,
        role=officer.role,
        checkpoint_id=officer.checkpoint_id,
        checkpoint_location=cp_loc or "Raxaul Checkpoint (Indo-Nepal)",
        status=officer.status
    )

    return TokenResponse(
        access_token=f"ssb_token_{officer.id}",
        token_type="bearer",
        user=user_resp
    )
