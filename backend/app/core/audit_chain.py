import hashlib
import json
from typing import Tuple, List, Optional, Any


GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def compute_record_hash(
    record_id: str,
    timestamp_str: Any,
    checkpoint_location: str,
    officer_id: str,
    document_type: str,
    document_number: str,
    overall_risk_score: float,
    risk_level: str,
    officer_decision: str,
    prev_log_hash: str
) -> str:
    """
    Computes a canonical SHA-256 hash linking this audit log entry to the previous entry.
    Ensures append-only cryptographic tamper evidence.
    """
    if hasattr(timestamp_str, "strftime"):
        norm_ts = timestamp_str.strftime("%Y-%m-%d %H:%M:%S")
    else:
        ts_raw = str(timestamp_str).replace("T", " ").rstrip("Z")
        if "+" in ts_raw:
            ts_raw = ts_raw.split("+")[0]
        norm_ts = ts_raw.split(".")[0].strip()

    payload = {
        "id": str(record_id),
        "timestamp": norm_ts,
        "checkpoint": str(checkpoint_location),
        "officer_id": str(officer_id or ""),
        "doc_type": str(document_type),
        "doc_number": str(document_number or ""),
        "score": round(float(overall_risk_score), 2),
        "risk_level": str(risk_level),
        "decision": str(officer_decision or "PENDING"),
        "prev_hash": str(prev_log_hash)
    }
    raw_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

def verify_audit_chain(logs: List[Any]) -> Tuple[bool, str, int, Optional[str]]:
    """
    Verifies that an ordered list of screening logs maintains tamper-evident hash continuity.
    Detects modified records, deleted records, reordered records, and broken parent links.
    Returns: (is_valid, message, total_records, first_invalid_record_id)
    """
    total = len(logs)
    if not logs:
        return True, "Audit log chain is empty and valid.", 0, None
    
    expected_prev_hash = GENESIS_HASH
    for index, log in enumerate(logs):
        # 1. Verify link to previous entry
        if log.prev_log_hash != expected_prev_hash:
            return (
                False,
                f"Hash chain link broken at record #{index + 1} (ID: {log.id}). Expected previous hash {expected_prev_hash[:12]}..., found {log.prev_log_hash[:12]}... (Possible deleted or reordered record).",
                total,
                log.id
            )
        
        # 2. Recompute canonical hash of record contents
        calculated_hash = compute_record_hash(
            record_id=log.id,
            timestamp_str=str(log.timestamp),
            checkpoint_location=log.checkpoint_location,
            officer_id=log.officer_id,
            document_type=log.document_type,
            document_number=log.document_number,
            overall_risk_score=log.overall_risk_score,
            risk_level=log.risk_level,
            officer_decision=log.officer_decision,
            prev_log_hash=log.prev_log_hash
        )

        if calculated_hash != log.record_hash:
            return (
                False,
                f"Cryptographic record tampering detected at record #{index + 1} (ID: {log.id}). Record hash mismatch!",
                total,
                log.id
            )
        
        expected_prev_hash = log.record_hash
        
    return (
        True,
        f"Audit chain verified successfully. All {total} records maintain cryptographic SHA-256 provenance.",
        total,
        None
    )
