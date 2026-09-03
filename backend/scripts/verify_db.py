import sqlite3
import json
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.audit_chain import verify_audit_chain
from app.core.database import SessionLocal
from app.db.models import (
    Checkpoint,
    Officer,
    DocumentType,
    ReferenceDocument,
    BlacklistedDocument,
    TravelerBiometric,
    ScreeningLog
)

def run_db_verification():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'sih_screening.db')
    print(f"Checking SQLite database at: {db_path}")
    if not os.path.exists(db_path):
        print("ERROR: Database file does not exist!")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Checkpoints
    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN status='ACTIVE' THEN 1 END) FROM checkpoints;")
    cp_count, cp_active = cur.fetchone()
    cur.execute("SELECT id, checkpoint_code, name, state, district, status FROM checkpoints;")
    checkpoints = cur.fetchall()
    
    # 2. Officers
    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN status='ACTIVE' THEN 1 END) FROM officers;")
    officer_count, officer_active = cur.fetchone()
    cur.execute("SELECT badge_id, full_name, role, checkpoint_id, checkpoint_location, status FROM officers;")
    officers = cur.fetchall()
    
    # 3. Document types
    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN enabled=1 THEN 1 END) FROM document_types;")
    doc_type_count, doc_type_enabled = cur.fetchone()
    cur.execute("SELECT code, name, enabled, parser_version FROM document_types;")
    doc_types = cur.fetchall()
    
    # 4. Reference documents
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT document_type) FROM reference_documents;")
    ref_docs_count, ref_doc_types = cur.fetchone()
    cur.execute("SELECT document_type, status, COUNT(*) FROM reference_documents GROUP BY document_type, status;")
    ref_docs_breakdown = cur.fetchall()
    
    # 5. Lookout / Watchlist records (Reference documents with status='BLACKLISTED' / 'SUSPICIOUS' + BlacklistedDocument table)
    cur.execute("SELECT COUNT(*) FROM blacklisted_documents;")
    direct_blacklist_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reference_documents WHERE status IN ('BLACKLISTED', 'SUSPICIOUS', 'REVOKED');")
    ref_watchlist_count = cur.fetchone()[0]
    
    # 6. Biometric vectors (TravelerBiometric table)
    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN status='ACTIVE' THEN 1 END) FROM traveler_biometrics;")
    biometric_count, biometric_active = cur.fetchone()
    
    # 7 & 8. Screening logs / Audit records
    cur.execute("SELECT COUNT(*) FROM screening_logs;")
    screening_logs_count = cur.fetchone()[0]
    
    # 9. Risk levels
    cur.execute("SELECT risk_level, COUNT(*) FROM screening_logs GROUP BY risk_level;")
    risk_breakdown = cur.fetchall()
    
    # 10. Decisions
    cur.execute("SELECT officer_decision, COUNT(*) FROM screening_logs GROUP BY officer_decision;")
    decision_breakdown = cur.fetchall()
    
    # 11. Per checkpoint screening logs
    cur.execute("SELECT checkpoint_location, COUNT(*) FROM screening_logs GROUP BY checkpoint_location ORDER BY COUNT(*) DESC;")
    cp_logs_breakdown = cur.fetchall()

    # 11b. Per document type screening logs
    cur.execute("SELECT document_type, COUNT(*) FROM screening_logs GROUP BY document_type ORDER BY COUNT(*) DESC;")
    doc_type_logs_breakdown = cur.fetchall()
    
    # 12. Foreign keys check
    cur.execute("PRAGMA foreign_key_check;")
    fk_errors = cur.fetchall()
    
    # 13. Audit chain verification via app.core.audit_chain module
    db = SessionLocal()
    try:
        logs = db.query(ScreeningLog).order_by(ScreeningLog.timestamp.asc()).all()
        is_valid, msg, total_records, first_invalid_id = verify_audit_chain(logs)
        chain_verification = {
            "is_valid": is_valid,
            "message": msg,
            "records_checked": total_records,
            "first_invalid_record": first_invalid_id
        }
    finally:
        db.close()
        conn.close()
        
    print("\n==================================================")
    print("PHASE 1 — ACTUAL DATABASE VERIFICATION REPORT")
    print("==================================================")
    print(f"1. Checkpoints: {cp_count} total ({cp_active} active)")
    for cp in checkpoints:
        print(f"   - [{cp[0]}] {cp[1]}: {cp[2]} ({cp[3]}, {cp[4]}) | Status: {cp[5]}")
        
    print(f"\n2. Officers / Personnel: {officer_count} total ({officer_active} active)")
    for o in officers:
        print(f"   - {o[0]}: {o[1]} | Role: {o[2]} | Checkpoint: {o[4]} (ID: {o[3]}) | Status: {o[5]}")
        
    print(f"\n3. Supported Document Types: {doc_type_count} configured ({doc_type_enabled} enabled)")
    for dt in doc_types:
        print(f"   - {dt[0]}: {dt[1]} (v{dt[3]}) | Enabled: {bool(dt[2])}")
        
    print(f"\n4. Reference Documents: {ref_docs_count} total across {ref_doc_types} types")
    for dt, st, cnt in ref_docs_breakdown:
        print(f"   - {dt} [{st}]: {cnt} records")
        
    print(f"\n5. Watchlist / Lookout Records:")
    print(f"   - Blacklisted Documents (direct table): {direct_blacklist_count}")
    print(f"   - Reference Watchlist/Lookout Entries: {ref_watchlist_count}")
    
    print(f"\n6. Enrolled Biometric Profiles (512-D Vectors): {biometric_count} total ({biometric_active} active)")
    print(f"\n7 & 8. Screening Logs / Cryptographic Audit Records: {screening_logs_count} entries")
    
    print("\n9. Risk Level Breakdown in Audit Trail:")
    for r, cnt in risk_breakdown:
        print(f"   - {r}: {cnt} records")
        
    print("\n10. Officer Decision Breakdown in Audit Trail:")
    for d, cnt in decision_breakdown:
        print(f"   - {d or 'PENDING'}: {cnt} records")
        
    print("\n11. Screening Logs Distribution per Checkpoint:")
    for cpl, cnt in cp_logs_breakdown:
        print(f"   - {cpl or 'Unassigned'}: {cnt} records")

    print("\n11b. Screening Logs Distribution per Document Type:")
    for dt, cnt in doc_type_logs_breakdown:
        print(f"   - {dt}: {cnt} records")
        
    print(f"\n12. Foreign Key Integrity Check: {'VALID (0 foreign key errors)' if not fk_errors else f'ERRORS: {fk_errors}'}")
    
    print(f"\n13. SHA-256 Audit Chain Continuity Verification:")
    print(f"   - Chain Is Valid: {chain_verification.get('is_valid')}")
    print(f"   - Total Records Checked: {chain_verification.get('records_checked')}")
    print(f"   - Verification Message: {chain_verification.get('message')}")
    print(f"   - First Invalid Record: {chain_verification.get('first_invalid_record')}")
    print("==================================================\n")

if __name__ == '__main__':
    run_db_verification()
