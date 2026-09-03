# ==============================================================================
# SYNTHETIC DEMONSTRATION DATA — NOT REAL GOVERNMENT RECORDS
# All seeded checkpoints, personnel credentials, reference documents, and lookout entries
# are synthetic benchmark fixtures for evaluation and demonstration purposes only.
# ==============================================================================

import uuid
from datetime import datetime, timezone
from app.core.database import Base, engine, SessionLocal
from app.db.models import (
    Checkpoint,
    Officer,
    DocumentType,
    ReferenceDocument,
    BlacklistedDocument,
    ScreeningLog
)
from app.core.security import get_password_hash
from app.core.audit_chain import compute_record_hash, GENESIS_HASH

SYNTHETIC_CHECKPOINTS = [
    {
        "code": "CP-RAXAUL-01",
        "name": "Raxaul Checkpoint Unit A",
        "location": "Raxaul Land Port, Indo-Nepal Border",
        "state": "Bihar",
        "district": "East Champaran",
        "status": "ACTIVE"
    },
    {
        "code": "CP-RANIGANJ-01",
        "name": "Raniganj Integrated Checkpost",
        "location": "Raniganj ICP, Indo-Bangladesh Border",
        "state": "West Bengal",
        "district": "Paschim Bardhaman",
        "status": "ACTIVE"
    },
    {
        "code": "CP-PANITANKI-01",
        "name": "Panitanki Land Port Unit",
        "location": "Panitanki Border Crossing, Indo-Nepal Border",
        "state": "West Bengal",
        "district": "Darjeeling",
        "status": "ACTIVE"
    },
    {
        "code": "CP-JAIGAON-01",
        "name": "Jaigaon Transit Gate",
        "location": "Jaigaon Checkpoint, Indo-Bhutan Frontier",
        "state": "West Bengal",
        "district": "Alipurduar",
        "status": "ACTIVE"
    },
    {
        "code": "CP-JOGBANI-01",
        "name": "Jogbani Screening Unit",
        "location": "Jogbani Transit Post, Indo-Nepal Border",
        "state": "Bihar",
        "district": "Araria",
        "status": "ACTIVE"
    }
]

SYNTHETIC_DOCUMENT_TYPES = [
    {"code": "PASSPORT", "name": "Passport (ICAO 9303 TD3)", "enabled": True, "parser_version": "2.0.0"},
    {"code": "AADHAAR", "name": "Aadhaar Card (UIDAI Verhoeff)", "enabled": True, "parser_version": "2.0.0"},
    {"code": "DRIVING_LICENSE", "name": "Driving Licence (Sarathi Format)", "enabled": True, "parser_version": "2.0.0"},
    {"code": "VOTER_ID", "name": "Voter Identity Card (EPIC)", "enabled": True, "parser_version": "1.0.0"},
    {"code": "VISA", "name": "Transit Visa / Travel Permit", "enabled": False, "parser_version": "1.0.0"},
    {"code": "OTHER", "name": "Other Border Identity Document", "enabled": False, "parser_version": "1.0.0"}
]

SYNTHETIC_BLACKLIST_RECORDS = [
    # Passports (1 letter + 7 digits)
    {"type": "PASSPORT", "number": "Z9982341", "name": "VIKRAM CHOUDHARY", "status": "BLACKLISTED", "source": "MHA_LOOKOUT", "reason": "STOLEN: Reported stolen at transit checkpoint (MHA Alert)."},
    {"type": "PASSPORT", "number": "P4412093", "name": "RAJESH KUMAR", "status": "BLACKLISTED", "source": "MHA_LOOKOUT", "reason": "WATCHLIST: Identity associated with fraudulent border documentation ring."},
    {"type": "PASSPORT", "number": "K9876543", "name": "ANIL VERMA", "status": "BLACKLISTED", "source": "INTERPOL_SLTD", "reason": "REPORTED LOST: Passenger filed official lost passport report."},
    {"type": "PASSPORT", "number": "M3319082", "name": "SUNIL MEHTA", "status": "BLACKLISTED", "source": "INTERPOL_SLTD", "reason": "STOLEN: Interpol Stolen and Lost Travel Documents (SLTD) database notice."},
    {"type": "PASSPORT", "number": "A1209348", "name": "DEEPAK YADAV", "status": "SUSPICIOUS", "source": "BORDER_INTEL", "reason": "WATCHLIST: Impersonation suspect flagged by regional immigration control."},
    {"type": "PASSPORT", "number": "R8821094", "name": "SURESH GUPTA", "status": "REVOKED", "source": "PASSPORT_OFFICE", "reason": "REVOKED: Cancelled travel credentials under Section 10(3) Passports Act."},
    {"type": "PASSPORT", "number": "J5501923", "name": "MANOJ PANDEY", "status": "BLACKLISTED", "source": "MHA_LOOKOUT", "reason": "WATCHLIST: Fraud alert notice from external transit post."},
    {"type": "PASSPORT", "number": "T7712390", "name": "KAVITA SHARMA", "status": "EXPIRED", "source": "PASSPORT_OFFICE", "reason": "REPORTED LOST: Lost passport notice filed at New Delhi airport."},
    {"type": "PASSPORT", "number": "N6654120", "name": "RAVI THAKUR", "status": "BLACKLISTED", "source": "INTERPOL_SLTD", "reason": "STOLEN: Diplomatic pouch missing document report."},
    {"type": "PASSPORT", "number": "L4439012", "name": "POOJA MISHRA", "status": "SUSPICIOUS", "source": "SYNTHETIC_BENCHMARK", "reason": "SYNTHETIC TEST CASE: High-risk scenario calibration benchmark."},

    # Aadhaar Cards (12 digits)
    {"type": "AADHAAR", "number": "992811024431", "name": "AMIT SHARMA", "status": "BLACKLISTED", "source": "UIDAI_DEDUPLICATION", "reason": "WATCHLIST: Duplicate biometric conflict flagged during national deduplication."},
    {"type": "AADHAAR", "number": "881234901235", "name": "VIVEK TIWARI", "status": "EXPIRED", "source": "UIDAI_BENCHMARK", "reason": "REPORTED LOST: Physical e-Aadhaar printed card lost in border transit."},
    {"type": "AADHAAR", "number": "774901238492", "name": "SANDEEP KUMAR", "status": "BLACKLISTED", "source": "POLICE_STOLEN", "reason": "STOLEN: Wallet theft reported with physical identity proof."},
    {"type": "AADHAAR", "number": "661092837415", "name": "PRIYA JOSHI", "status": "REVOKED", "source": "UIDAI_BENCHMARK", "reason": "WATCHLIST: Cancelled UIDAI identifier due to suspected synthetic identity forgery."},
    {"type": "AADHAAR", "number": "552901847291", "name": "ROHIT PATEL", "status": "SUSPICIOUS", "source": "SYNTHETIC_BENCHMARK", "reason": "SYNTHETIC TEST CASE: UIDAI Verhoeff validation benchmark record."},
    {"type": "AADHAAR", "number": "443819028345", "name": "NEHA BHATIA", "status": "EXPIRED", "source": "LOCAL_AFFIDAVIT", "reason": "REPORTED LOST: Lost identity card affidavit submitted."},

    # Driving Licences (Indian state code + numbers)
    {"type": "DRIVING_LICENCE", "number": "DL-1420110098231", "name": "SANJAY GUPTA", "status": "REVOKED", "source": "SARATHI_REVOKED", "reason": "WATCHLIST: Revoked commercial transport licence flagged for fraudulent endorsements."},
    {"type": "DRIVING_LICENCE", "number": "KA-0120190001234", "name": "MOHIT SINGH", "status": "BLACKLISTED", "source": "SARATHI_REVOKED", "reason": "STOLEN: Stolen driving licence used in unauthorized vehicle crossing."},
    {"type": "DRIVING_LICENCE", "number": "MH-0220180099112", "name": "AJAY CHAWLA", "status": "EXPIRED", "source": "SARATHI_REVOKED", "reason": "REPORTED LOST: Lost driving licence notice at checkpoint transit."},
    {"type": "DRIVING_LICENCE", "number": "UP-1620200088334", "name": "TARUN MISHRA", "status": "BLACKLISTED", "source": "SARATHI_REVOKED", "reason": "WATCHLIST: Forged heavy vehicle licence seized during check."},
    {"type": "DRIVING_LICENCE", "number": "HR-2620150077221", "name": "VIJAY MALIK", "status": "SUSPICIOUS", "source": "SYNTHETIC_BENCHMARK", "reason": "SYNTHETIC TEST CASE: Parivahan Sarathi cross-validation test record."},
    {"type": "DRIVING_LICENCE", "number": "BR-0120170066119", "name": "DINESH PRASAD", "status": "BLACKLISTED", "source": "SARATHI_REVOKED", "reason": "STOLEN: Stolen credentials alert issued by state transport authority."}
]

from sqlalchemy import inspect, text

def _migrate_existing_tables():
    """Safely adds newly defined columns and fixes legacy foreign keys in existing tables."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    with engine.begin() as conn:
        # Check officers columns
        if "officers" in table_names:
            cols = {c["name"] for c in inspector.get_columns("officers")}
            if "checkpoint_id" not in cols:
                conn.execute(text("ALTER TABLE officers ADD COLUMN checkpoint_id VARCHAR(36)"))
            if "status" not in cols:
                conn.execute(text("ALTER TABLE officers ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"))
            if "created_at" not in cols:
                conn.execute(text("ALTER TABLE officers ADD COLUMN created_at DATETIME"))
            if "last_login" not in cols:
                conn.execute(text("ALTER TABLE officers ADD COLUMN last_login DATETIME"))

        # Check traveler_biometrics columns
        if "traveler_biometrics" in table_names:
            cols = {c["name"] for c in inspector.get_columns("traveler_biometrics")}
            if "embedding_engine" not in cols:
                conn.execute(text("ALTER TABLE traveler_biometrics ADD COLUMN embedding_engine VARCHAR(50) DEFAULT 'OpenCV-SpatialGradient-512D'"))
            if "embedding_dimension" not in cols:
                conn.execute(text("ALTER TABLE traveler_biometrics ADD COLUMN embedding_dimension INTEGER DEFAULT 512"))
            if "status" not in cols:
                conn.execute(text("ALTER TABLE traveler_biometrics ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"))

        # Check screening_logs columns
        if "screening_logs" in table_names:
            cols = {c["name"] for c in inspector.get_columns("screening_logs")}
            if "checkpoint_id" not in cols:
                conn.execute(text("ALTER TABLE screening_logs ADD COLUMN checkpoint_id VARCHAR(50)"))
            if "processing_time_ms" not in cols:
                conn.execute(text("ALTER TABLE screening_logs ADD COLUMN processing_time_ms FLOAT DEFAULT 0.0"))
            if "ocr_time_ms" not in cols:
                conn.execute(text("ALTER TABLE screening_logs ADD COLUMN ocr_time_ms FLOAT DEFAULT 0.0"))
            if "forensics_time_ms" not in cols:
                conn.execute(text("ALTER TABLE screening_logs ADD COLUMN forensics_time_ms FLOAT DEFAULT 0.0"))
            if "biometric_time_ms" not in cols:
                conn.execute(text("ALTER TABLE screening_logs ADD COLUMN biometric_time_ms FLOAT DEFAULT 0.0"))
            if "pipeline_version" not in cols:
                conn.execute(text("ALTER TABLE screening_logs ADD COLUMN pipeline_version VARCHAR(20) DEFAULT '2.0.0'"))

            # If legacy officer_id or checkpoint_id FK constraint exists in SQLite, recreate screening_logs cleanly
            fk_list = inspector.get_foreign_keys("screening_logs")
            if any(fk.get("referred_table") == "officers" for fk in fk_list):
                conn.execute(text("PRAGMA foreign_keys=OFF;"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS screening_logs_backup AS SELECT * FROM screening_logs;"))
                conn.execute(text("DROP TABLE screening_logs;"))
                Base.metadata.tables["screening_logs"].create(conn)
                conn.execute(text("""
                    INSERT INTO screening_logs (
                        id, timestamp, checkpoint_id, checkpoint_location, officer_id,
                        document_type, document_number, holder_name, raw_document_image_path,
                        raw_live_photo_path, tamper_heatmap_path, extracted_data_json,
                        validation_flags_json, tampering_score, face_match_score,
                        overall_risk_score, risk_level, officer_decision, officer_notes,
                        prev_log_hash, record_hash, processing_time_ms, ocr_time_ms,
                        forensics_time_ms, biometric_time_ms, pipeline_version
                    )
                    SELECT 
                        id, timestamp, checkpoint_id, checkpoint_location, officer_id,
                        document_type, document_number, holder_name, raw_document_image_path,
                        raw_live_photo_path, tamper_heatmap_path, extracted_data_json,
                        validation_flags_json, tampering_score, face_match_score,
                        overall_risk_score, risk_level, officer_decision, officer_notes,
                        prev_log_hash, record_hash, processing_time_ms, ocr_time_ms,
                        forensics_time_ms, biometric_time_ms, pipeline_version
                    FROM screening_logs_backup;
                """))
                conn.execute(text("DROP TABLE screening_logs_backup;"))
                conn.execute(text("PRAGMA foreign_keys=ON;"))


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_existing_tables()
    db = SessionLocal()
    
    try:
        # 1. Seed Checkpoints
        existing_codes = {cp.checkpoint_code: cp for cp in db.query(Checkpoint).all()}
        cp_map = {}
        for cp_data in SYNTHETIC_CHECKPOINTS:
            if cp_data["code"] not in existing_codes:
                new_cp = Checkpoint(
                    checkpoint_code=cp_data["code"],
                    name=cp_data["name"],
                    location=cp_data["location"],
                    state=cp_data["state"],
                    district=cp_data["district"],
                    status=cp_data["status"]
                )
                db.add(new_cp)
                db.flush()
                cp_map[cp_data["code"]] = new_cp
            else:
                cp_map[cp_data["code"]] = existing_codes[cp_data["code"]]
        db.commit()

        # 2. Seed Document Types
        existing_doc_types = {dt.code for dt in db.query(DocumentType).all()}
        for dt_data in SYNTHETIC_DOCUMENT_TYPES:
            if dt_data["code"] not in existing_doc_types:
                db.add(DocumentType(
                    code=dt_data["code"],
                    name=dt_data["name"],
                    enabled=dt_data["enabled"],
                    parser_version=dt_data["parser_version"]
                ))
        db.commit()

        # 3. Seed Officers with Checkpoint Links
        existing_officers = {o.badge_id: o for o in db.query(Officer).all()}
        raxaul_cp = cp_map.get("CP-RAXAUL-01")
        raniganj_cp = cp_map.get("CP-RANIGANJ-01")
        panitanki_cp = cp_map.get("CP-PANITANKI-01")

        officers_to_seed = [
            {
                "badge_id": "SSB-7741",
                "full_name": "Inspector R. K. Sharma",
                "role": "OFFICER",
                "checkpoint": raxaul_cp,
                "password": "officer123"
            },
            {
                "badge_id": "SSB-1002",
                "full_name": "Asst. Commandant A. Verma",
                "role": "SUPERVISOR",
                "checkpoint": raniganj_cp,
                "password": "super123"
            },
            {
                "badge_id": "SSB-5099",
                "full_name": "Senior Analyst P. Singh",
                "role": "ANALYST",
                "checkpoint": panitanki_cp,
                "password": "analyst123"
            },
            {
                "badge_id": "SSB-0001",
                "full_name": "Commandant M. S. Rawat",
                "role": "ADMIN",
                "checkpoint": raxaul_cp,
                "password": "admin123"
            }
        ]

        for off_data in officers_to_seed:
            badge = off_data["badge_id"]
            if badge not in existing_officers:
                cp = off_data["checkpoint"]
                db.add(Officer(
                    badge_id=badge,
                    full_name=off_data["full_name"],
                    role=off_data["role"],
                    checkpoint_id=cp.id if cp else None,
                    checkpoint_location=cp.name if cp else "SSB Checkpoint Unit",
                    password_hash=get_password_hash(off_data["password"]),
                    status="ACTIVE"
                ))
            else:
                # Update checkpoint link if missing
                off = existing_officers[badge]
                cp = off_data["checkpoint"]
                if not off.checkpoint_id and cp:
                    off.checkpoint_id = cp.id
                    off.checkpoint_location = cp.name
        db.commit()

        # 4. Seed Reference Documents & Blacklisted Documents
        existing_ref_nums = {r.document_number for r in db.query(ReferenceDocument.document_number).all()}
        existing_black_nums = {b.document_number for b in db.query(BlacklistedDocument.document_number).all()}

        new_ref_records = []
        new_black_records = []

        for rec in SYNTHETIC_BLACKLIST_RECORDS:
            clean_num = rec["number"].replace(" ", "").replace("-", "")
            if clean_num not in existing_ref_nums and rec["number"] not in existing_ref_nums:
                new_ref_records.append(
                    ReferenceDocument(
                        document_type=rec["type"],
                        document_number=clean_num,
                        holder_name=rec["name"],
                        status=rec.get("status", "BLACKLISTED"),
                        source_type=rec.get("source", "SYNTHETIC_BENCHMARK"),
                        reason=rec["reason"]
                    )
                )

            if clean_num not in existing_black_nums and rec["number"] not in existing_black_nums:
                new_black_records.append(
                    BlacklistedDocument(
                        document_type=rec["type"],
                        document_number=clean_num,
                        holder_name=rec["name"],
                        reason=rec["reason"]
                    )
                )

        if new_ref_records:
            db.add_all(new_ref_records)
        if new_black_records:
            db.add_all(new_black_records)
        db.commit()

        # 5. Ensure Screening Log Cryptographic Provenance
        logs = db.query(ScreeningLog).order_by(ScreeningLog.timestamp.asc()).all()
        if logs:
            prev_hash = GENESIS_HASH
            for log in logs:
                log.prev_log_hash = prev_hash
                log.record_hash = compute_record_hash(
                    record_id=log.id,
                    timestamp_str=log.timestamp,
                    checkpoint_location=log.checkpoint_location,
                    officer_id=log.officer_id,
                    document_type=log.document_type,
                    document_number=log.document_number,
                    overall_risk_score=log.overall_risk_score,
                    risk_level=log.risk_level,
                    officer_decision=log.officer_decision,
                    prev_log_hash=prev_hash
                )
                prev_hash = log.record_hash
            db.commit()

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialization and multi-checkpoint seeding completed successfully.")
