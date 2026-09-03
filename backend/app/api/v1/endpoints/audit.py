import csv
import io
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import ScreeningLog
from app.core.security import mask_document_number, mask_name
from app.core.audit_chain import verify_audit_chain
from app.schemas.audit import ScreeningLogResponse, AuditChainVerificationResponse

router = APIRouter()

@router.get("/logs", response_model=List[ScreeningLogResponse])
def get_audit_logs(
    risk_level: Optional[str] = Query(None),
    officer_id: Optional[str] = Query(None),
    checkpoint_id: Optional[str] = Query(None),
    checkpoint_location: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Returns screening logs with masked sensitive document numbers and PII by default.
    Maintains cryptographic integrity while safeguarding personal identity data.
    Supports filtering by checkpoint, risk level, officer, decision, and date range.
    """
    query = db.query(ScreeningLog)

    if risk_level:
        query = query.filter(ScreeningLog.risk_level == risk_level.upper())
    if officer_id:
        query = query.filter(ScreeningLog.officer_id == officer_id)
    if checkpoint_id:
        query = query.filter(ScreeningLog.checkpoint_id == checkpoint_id)
    if checkpoint_location:
        query = query.filter(ScreeningLog.checkpoint_location.ilike(f"%{checkpoint_location}%"))
    if doc_type:
        query = query.filter(ScreeningLog.document_type == doc_type.upper())
    if decision:
        dec_upper = decision.upper()
        norm_map = {"APPROVE": "APPROVED", "APPROVED": "APPROVED", "REJECT": "REJECTED", "REJECTED": "REJECTED", "ESCALATE": "ESCALATED", "ESCALATED": "ESCALATED", "PENDING": "PENDING"}
        normalized_dec = norm_map.get(dec_upper, dec_upper)
        query = query.filter(ScreeningLog.officer_decision.in_([normalized_dec, dec_upper]))
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(ScreeningLog.timestamp >= dt_from)
        except Exception:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(ScreeningLog.timestamp <= dt_to)
        except Exception:
            pass

    logs = query.order_by(ScreeningLog.timestamp.desc()).limit(limit).all()
    return logs

@router.get("/logs/{log_id}", response_model=ScreeningLogResponse)
def get_audit_log_by_id(log_id: str, db: Session = Depends(get_db)):
    """
    Returns a single audit screening record by ID with masked PII.
    """
    log = db.query(ScreeningLog).filter(ScreeningLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening audit log '{log_id}' not found."
        )
    return log

@router.get("/export")
@router.get("/export/csv")
def export_audit_logs_csv(
    risk_level: Optional[str] = Query(None),
    officer_id: Optional[str] = Query(None),
    checkpoint_id: Optional[str] = Query(None),
    checkpoint_location: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Exports supervisor-safe screening logs as a CSV file attachment.
    All document numbers and names are masked to prevent PII leakage.
    """
    query = db.query(ScreeningLog)
    if risk_level:
        query = query.filter(ScreeningLog.risk_level == risk_level.upper())
    if officer_id:
        query = query.filter(ScreeningLog.officer_id == officer_id)
    if checkpoint_id:
        query = query.filter(ScreeningLog.checkpoint_id == checkpoint_id)
    if checkpoint_location:
        query = query.filter(ScreeningLog.checkpoint_location.ilike(f"%{checkpoint_location}%"))
    if doc_type:
        query = query.filter(ScreeningLog.document_type == doc_type.upper())
    if decision:
        dec_upper = decision.upper()
        norm_map = {"APPROVE": "APPROVED", "APPROVED": "APPROVED", "REJECT": "REJECTED", "REJECTED": "REJECTED", "ESCALATE": "ESCALATED", "ESCALATED": "ESCALATED", "PENDING": "PENDING"}
        normalized_dec = norm_map.get(dec_upper, dec_upper)
        query = query.filter(ScreeningLog.officer_decision.in_([normalized_dec, dec_upper]))
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(ScreeningLog.timestamp >= dt_from)
        except Exception:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(ScreeningLog.timestamp <= dt_to)
        except Exception:
            pass

    logs = query.order_by(ScreeningLog.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Standard supervisor CSV columns
    writer.writerow([
        "timestamp",
        "checkpoint",
        "officer",
        "document_type",
        "masked_document_number",
        "risk_score",
        "risk_level",
        "decision",
        "major_flags"
    ])

    for log in logs:
        # PII-safe masking
        masked_doc = mask_document_number(log.document_number or "", log.document_type or "")

        # Extract major flags
        flags_data = log.validation_flags_json or []
        flag_codes = [f.get("code", "") for f in flags_data if isinstance(f, dict) and f.get("code")]
        major_flags_str = "; ".join(flag_codes) if flag_codes else "CLEAN"

        writer.writerow([
            log.timestamp.isoformat() if log.timestamp else "",
            log.checkpoint_location or "Raxaul Checkpoint",
            log.officer_id or "SSB-7741",
            log.document_type or "UNKNOWN",
            masked_doc,
            f"{log.overall_risk_score:.1f}" if log.overall_risk_score is not None else "0.0",
            log.risk_level or "LOW",
            log.officer_decision or "PENDING",
            major_flags_str
        ])

    csv_content = output.getvalue()
    filename = f"ssb_audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )

@router.get("/verify-chain", response_model=AuditChainVerificationResponse)
def verify_log_integrity(db: Session = Depends(get_db)):
    """
    Verifies full SHA-256 cryptographic provenance and linkage of all screening logs.
    Detects record tampering, hash alterations, deletions, and link breakages.
    """
    logs = db.query(ScreeningLog).order_by(ScreeningLog.timestamp.asc()).all()
    is_valid, msg, total_records, first_invalid_id = verify_audit_chain(logs)
    now_iso = datetime.now(timezone.utc).isoformat()
    
    return AuditChainVerificationResponse(
        valid=is_valid,
        is_valid=is_valid,
        records_checked=total_records,
        total_records=total_records,
        verification_timestamp=now_iso,
        first_invalid_record=first_invalid_id,
        first_invalid_record_id=first_invalid_id,
        message=msg
    )
