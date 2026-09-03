from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import BlacklistedDocument

router = APIRouter()

class BlacklistCreateRequest(BaseModel):
    document_type: str  # 'PASSPORT', 'AADHAAR', 'DRIVING_LICENCE'
    document_number: str
    holder_name: Optional[str] = None
    reason: str

class BlacklistResponse(BaseModel):
    id: str
    document_type: str
    document_number: str
    holder_name: Optional[str] = None
    reason: str
    flagged_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/blacklist", response_model=List[BlacklistResponse])
def get_blacklisted_documents(
    doc_type: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    q = db.query(BlacklistedDocument)
    if doc_type:
        q = q.filter(BlacklistedDocument.document_type == doc_type.upper())
    if query:
        search = f"%{query}%"
        q = q.filter(
            (BlacklistedDocument.document_number.ilike(search)) |
            (BlacklistedDocument.holder_name.ilike(search))
        )
    return q.order_by(BlacklistedDocument.flagged_at.desc()).limit(limit).all()

@router.post("/blacklist", response_model=BlacklistResponse, status_code=status.HTTP_201_CREATED)
def add_blacklisted_document(
    req: BlacklistCreateRequest,
    db: Session = Depends(get_db)
):
    clean_num = req.document_number.strip().replace(" ", "").replace("-", "")
    existing = db.query(BlacklistedDocument).filter(
        BlacklistedDocument.document_number == clean_num
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document #{clean_num} is already registered in the reference blacklist."
        )

    new_entry = BlacklistedDocument(
        document_type=req.document_type.upper(),
        document_number=clean_num,
        holder_name=req.holder_name,
        reason=req.reason
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry
