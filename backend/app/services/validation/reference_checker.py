import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import BlacklistedDocument, ReferenceDocument, TravelerBiometric
from app.core.config import DUPLICATE_FACE_THRESHOLD
from app.services.validation.format_rules import parse_date

def check_blacklist(db: Session, document_number: str, document_type: str = None) -> list[dict]:
    """
    Queries local reference database to check if document number matches
    a synthetic watchlist, stolen report, cancelled, or suspicious document entry.
    """
    flags = []
    if not document_number:
        return flags

    clean_num = str(document_number).strip().replace(" ", "").replace("-", "")
    
    seen_reasons = set()

    # 1. Query ReferenceDocuments (Expanded multi-checkpoint reference registry)
    ref_matches = db.query(ReferenceDocument).filter(
        ReferenceDocument.document_number.ilike(f"%{clean_num}%")
    ).all()

    for r_match in ref_matches:
        if r_match.status in ["BLACKLISTED", "REVOKED", "SUSPICIOUS"]:
            msg = f"Reference database match: Document #{r_match.document_number} flagged ({r_match.status}). Notice: {r_match.reason or 'Active lookout notice'}"
            if msg not in seen_reasons:
                seen_reasons.add(msg)
                flags.append({
                    "code": "BLACKLIST_MATCH" if r_match.status != "SUSPICIOUS" else "SUSPICIOUS_DOCUMENT_ALERT",
                    "message": msg,
                    "severity": "CRITICAL" if r_match.status == "BLACKLISTED" else "HIGH",
                    "source": "Reference"
                })

    # 2. Query BlacklistedDocuments (Direct lookout circular mirror)
    black_matches = db.query(BlacklistedDocument).filter(
        BlacklistedDocument.document_number.ilike(f"%{clean_num}%")
    ).all()

    for match in black_matches:
        msg = f"Reference database match: Document #{match.document_number} matches local synthetic watchlist. Notice: {match.reason}"
        if msg not in seen_reasons:
            seen_reasons.add(msg)
            flags.append({
                "code": "BLACKLIST_MATCH",
                "message": msg,
                "severity": "CRITICAL",
                "source": "Reference"
            })

    return flags

def check_expiry(expiry_date_str: str) -> list[dict]:
    """
    Validates whether the document has expired.
    """
    flags = []
    if not expiry_date_str:
        return flags

    dt = parse_date(expiry_date_str)
    if dt and dt < datetime.now():
        flags.append({
            "code": "DOCUMENT_EXPIRED",
            "message": f"Document expired on {dt.strftime('%d-%b-%Y')}. Invalid for border crossing.",
            "severity": "WARNING",
            "source": "Validation"
        })
    return flags

def check_duplicate_identity(
    db: Session,
    current_embedding: np.ndarray,
    current_doc_num: str,
    threshold: float = None
) -> tuple[bool, str | None]:
    """
    Compares current facial feature embedding against locally stored traveler biometrics.
    If similarity exceeds threshold under a different document number, triggers a duplicate identity flag.
    """
    if current_embedding is None or np.all(current_embedding == 0):
        return False, None

    thresh = threshold or DUPLICATE_FACE_THRESHOLD
    clean_curr = str(current_doc_num).strip().replace(" ", "").replace("-", "")

    records = db.query(TravelerBiometric).all()
    for rec in records:
        clean_rec = str(rec.document_number).strip().replace(" ", "").replace("-", "")
        if clean_rec != clean_curr:
            stored_emb = np.frombuffer(rec.face_embedding, dtype=np.float32)
            if len(stored_emb) == len(current_embedding):
                dot_prod = float(np.dot(current_embedding, stored_emb))
                norm1 = float(np.linalg.norm(current_embedding))
                norm2 = float(np.linalg.norm(stored_emb))
                if norm1 > 0 and norm2 > 0:
                    sim = ((dot_prod / (norm1 * norm2)) + 1.0) / 2.0 * 100.0
                    if sim >= thresh:
                        return True, rec.document_number

    return False, None
