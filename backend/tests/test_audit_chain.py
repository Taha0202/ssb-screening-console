import pytest  # type: ignore
from app.core.audit_chain import compute_record_hash, verify_audit_chain, GENESIS_HASH
from app.core.security import mask_document_number, mask_name, sanitize_for_log

class MockScreeningLog:
    def __init__(self, id, timestamp, checkpoint, officer_id, doc_type, doc_num, score, risk_level, decision, prev_hash, rec_hash):
        self.id = id
        self.timestamp = timestamp
        self.checkpoint_location = checkpoint
        self.officer_id = officer_id
        self.document_type = doc_type
        self.document_number = doc_num
        self.overall_risk_score = score
        self.risk_level = risk_level
        self.officer_decision = decision
        self.prev_log_hash = prev_hash
        self.record_hash = rec_hash

def test_audit_chain_valid():
    # Build 3 valid chained records
    h1 = compute_record_hash("log1", "2026-08-28 10:00:00", "Raxaul", "off_1", "PASSPORT", "K1234567", 12.0, "LOW", "APPROVED", GENESIS_HASH)
    log1 = MockScreeningLog("log1", "2026-08-28 10:00:00", "Raxaul", "off_1", "PASSPORT", "K1234567", 12.0, "LOW", "APPROVED", GENESIS_HASH, h1)

    h2 = compute_record_hash("log2", "2026-08-28 10:05:00", "Raxaul", "off_1", "PASSPORT", "K9876543", 78.0, "HIGH", "REJECTED", h1)
    log2 = MockScreeningLog("log2", "2026-08-28 10:05:00", "Raxaul", "off_1", "PASSPORT", "K9876543", 78.0, "HIGH", "REJECTED", h1, h2)

    h3 = compute_record_hash("log3", "2026-08-28 10:10:00", "Raxaul", "off_1", "AADHAAR", "234567890128", 15.0, "LOW", "APPROVED", h2)
    log3 = MockScreeningLog("log3", "2026-08-28 10:10:00", "Raxaul", "off_1", "AADHAAR", "234567890128", 15.0, "LOW", "APPROVED", h2, h3)

    is_valid, msg, total, inv_id = verify_audit_chain([log1, log2, log3])
    assert is_valid is True
    assert total == 3
    assert inv_id is None

def test_audit_chain_record_content_tampered():
    h1 = compute_record_hash("log1", "2026-08-28 10:00:00", "Raxaul", "off_1", "PASSPORT", "K1234567", 12.0, "LOW", "APPROVED", GENESIS_HASH)
    log1 = MockScreeningLog("log1", "2026-08-28 10:00:00", "Raxaul", "off_1", "PASSPORT", "K1234567", 12.0, "LOW", "APPROVED", GENESIS_HASH, h1)

    # Corrupt log1's score after hashing
    log1.overall_risk_score = 99.0

    is_valid, msg, total, inv_id = verify_audit_chain([log1])
    assert is_valid is False
    assert "tampering detected" in msg.lower()
    assert inv_id == "log1"

def test_audit_chain_deleted_or_reordered():
    h1 = compute_record_hash("log1", "2026-08-28 10:00:00", "Raxaul", "off_1", "PASSPORT", "K1234567", 12.0, "LOW", "APPROVED", GENESIS_HASH)
    log1 = MockScreeningLog("log1", "2026-08-28 10:00:00", "Raxaul", "off_1", "PASSPORT", "K1234567", 12.0, "LOW", "APPROVED", GENESIS_HASH, h1)

    h2 = compute_record_hash("log2", "2026-08-28 10:05:00", "Raxaul", "off_1", "PASSPORT", "K9876543", 78.0, "HIGH", "REJECTED", h1)
    log2 = MockScreeningLog("log2", "2026-08-28 10:05:00", "Raxaul", "off_1", "PASSPORT", "K9876543", 78.0, "HIGH", "REJECTED", h1, h2)

    # Reorder logs: [log2, log1]
    is_valid, msg, total, inv_id = verify_audit_chain([log2, log1])
    assert is_valid is False
    assert "chain link broken" in msg.lower() or "expected previous hash" in msg.lower()

def test_hash_calculation_deterministic():
    """Ensures identical audit record payload always yields the exact same SHA-256 hash."""
    h1 = compute_record_hash("rec_100", "2026-08-28 12:00:00", "Raxaul", "SSB-7741", "PASSPORT", "P1234567", 25.5, "LOW", "APPROVED", GENESIS_HASH)
    h2 = compute_record_hash("rec_100", "2026-08-28 12:00:00", "Raxaul", "SSB-7741", "PASSPORT", "P1234567", 25.5, "LOW", "APPROVED", GENESIS_HASH)
    assert h1 == h2
    assert len(h1) == 64

def test_pii_masking_helpers():
    """Validates masking of sensitive identity numbers according to national conventions."""
    # Passport: P1234567 -> P*****67
    assert mask_document_number("P1234567", "PASSPORT") == "P*****67"
    assert mask_document_number("Z9982341", "PASSPORT") == "Z*****41"

    # Aadhaar: 123456789012 -> XXXX XXXX 9012
    assert mask_document_number("123456789012", "AADHAAR") == "XXXX XXXX 9012"
    assert mask_document_number("9928 1102 4431", "AADHAAR") == "XXXX XXXX 4431"

    # Driving Licence: DL-1420110098231 -> DL-14****8231
    assert "DL" in mask_document_number("DL-1420110098231", "DRIVING_LICENCE")
    assert "****" in mask_document_number("DL-1420110098231", "DRIVING_LICENCE")

    # Name masking
    assert mask_name("Rajesh Kumar") == "R***** K****"
    assert mask_name(None) == "—"

    # Log sanitizer
    sanitized = sanitize_for_log("Screening Passport P1234567 for traveler Aadhaar 123456789012")
    assert "P1234567" not in sanitized
    assert "123456789012" not in sanitized

