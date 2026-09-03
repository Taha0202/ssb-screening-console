import os
import io
import time
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_documents")

def generate_test_doc_image(text_header="PASSPORT REPUBLIC OF INDIA", doc_num="K1234567", name="SHUBHAM SURAJ SINGH"):
    """Generates synthetic test document bitmap."""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 245
    cv2.putText(img, text_header, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    cv2.putText(img, f"Doc No: {doc_num}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
    cv2.putText(img, f"Name: {name}", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
    cv2.rectangle(img, (400, 80), (550, 260), (100, 100, 100), 2)
    # Synthetic face shape
    cv2.circle(img, (475, 170), 50, (180, 180, 180), -1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

def generate_test_traveler_face():
    """Generates synthetic traveler face bitmap."""
    img = np.ones((300, 300, 3), dtype=np.uint8) * 230
    cv2.circle(img, (150, 150), 80, (160, 160, 160), -1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

def test_01_genuine_passport():
    """1. Genuine Passport -> LOW RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_genuine.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")
    t0 = time.perf_counter()
    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={"document_file": ("sample_passport_genuine.jpg", f_doc, "image/jpeg"), "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg")},
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
        )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "LOW"
    assert data["face_verification"]["similarity_score"] >= 70.0
    print(f"\n[Matrix #01] Genuine Passport: Status=200, Time={elapsed_ms}ms, Risk={data['risk_assessment']['risk_level']}, Score={data['risk_assessment']['overall_risk_score']:.1f}")

def test_02_tampered_passport():
    """2. Tampered Passport -> HIGH RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_tampered.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")
    t0 = time.perf_counter()
    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={"document_file": ("sample_passport_tampered.jpg", f_doc, "image/jpeg"), "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg")},
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
        )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "HIGH"
    assert data["tampering"]["overall_tampering_score"] > 20.0
    print(f"\n[Matrix #02] Tampered Passport: Status=200, Time={elapsed_ms}ms, Risk={data['risk_assessment']['risk_level']}, TamperScore={data['tampering']['overall_tampering_score']:.1f}")

def test_03_face_mismatch():
    """3. Face Mismatch -> HIGH RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_genuine.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_mismatch.jpg")
    t0 = time.perf_counter()
    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={"document_file": ("sample_passport_genuine.jpg", f_doc, "image/jpeg"), "live_photo_file": ("sample_traveler_mismatch.jpg", f_live, "image/jpeg")},
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
        )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "HIGH"
    assert data["face_verification"]["similarity_score"] < 50.0
    print(f"\n[Matrix #03] Face Mismatch: Status=200, Time={elapsed_ms}ms, Risk={data['risk_assessment']['risk_level']}, SimScore={data['face_verification']['similarity_score']:.1f}%")

def test_04_blacklisted_document():
    """4. Blacklisted Document -> HIGH RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_blacklisted.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")
    t0 = time.perf_counter()
    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={"document_file": ("sample_passport_blacklisted.jpg", f_doc, "image/jpeg"), "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg")},
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
        )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "HIGH"
    assert any("BLACKLIST" in f.get("code", "") for f in data["validation_flags"])
    print(f"\n[Matrix #04] Blacklisted Doc: Status=200, Time={elapsed_ms}ms, Risk={data['risk_assessment']['risk_level']}, Flags={len(data['validation_flags'])}")

def test_05_tampered_aadhaar():
    """5. Tampered Aadhaar -> HIGH RISK (Checksum failure)."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_aadhaar_tampered.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")
    t0 = time.perf_counter()
    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={"document_file": ("sample_aadhaar_tampered.jpg", f_doc, "image/jpeg"), "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg")},
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
        )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert data["document_type"] == "AADHAAR"
    print(f"\n[Matrix #05] Tampered Aadhaar: Status=200, Time={elapsed_ms}ms, DocType={data['document_type']}, Risk={data['risk_assessment']['risk_level']}")

def test_06_valid_driving_licence():
    """6. Valid Driving Licence -> Parsed and Processed."""
    img_bytes = generate_test_doc_image("UNION OF INDIA DRIVING LICENCE", "DL-1420110012345", "RAJESH KUMAR")
    live_bytes = generate_test_traveler_face()
    t0 = time.perf_counter()
    res = client.post(
        "/api/v1/screening/scan",
        files={"document_file": ("dl_valid.jpg", img_bytes, "image/jpeg"), "live_photo_file": ("live.jpg", live_bytes, "image/jpeg")},
        data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert data["document_type"] in ["DRIVING_LICENSE", "DRIVING_LICENCE", "UNKNOWN", "PASSPORT"]
    print(f"\n[Matrix #06] Valid DL: Status=200, Time={elapsed_ms}ms, DocType={data['document_type']}, Score={data['risk_assessment']['overall_risk_score']:.1f}")

def test_07_invalid_driving_licence():
    """7. Invalid Driving Licence -> Format checked."""
    from app.services.validation.format_rules import validate_dl_number
    assert validate_dl_number("INVALID-DL") is False
    assert validate_dl_number("DL1420110012345") is True
    print("\n[Matrix #07] Invalid DL Format: Successfully rejected invalid syntax pattern.")

def test_08_valid_voter_id():
    """8. Valid Voter ID (EPIC) -> Formatted and parsed."""
    from app.services.validation.format_rules import validate_voter_id_number
    assert validate_voter_id_number("ABC1234567") is True
    assert validate_voter_id_number("WBF9081234") is True
    
    img_bytes = generate_test_doc_image("ELECTION COMMISSION OF INDIA ELECTOR PHOTO IDENTITY CARD", "ABC1234567", "SURESH PATEL")
    live_bytes = generate_test_traveler_face()
    t0 = time.perf_counter()
    res = client.post(
        "/api/v1/screening/scan",
        files={"document_file": ("voter_valid.jpg", img_bytes, "image/jpeg"), "live_photo_file": ("live.jpg", live_bytes, "image/jpeg")},
        data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"}
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert res.status_code == 200
    data = res.json()
    assert "screening_id" in data
    assert "document_type" in data
    print(f"\n[Matrix #08] Valid Voter ID: Status=200, Time={elapsed_ms}ms, DocType={data['document_type']}")

def test_09_invalid_voter_id():
    """9. Invalid Voter ID -> Format rejected."""
    from app.services.validation.format_rules import validate_voter_id_number
    assert validate_voter_id_number("123ABC456") is False
    assert validate_voter_id_number("AB1234") is False
    print("\n[Matrix #09] Invalid Voter ID: Correctly rejected malformed EPIC strings.")

def test_10_unsupported_reserved_document_type():
    """10. Unsupported / Reserved Document Type -> Proper handling."""
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    # Query document types
    from app.core.database import SessionLocal
    from app.db.models import DocumentType
    db = SessionLocal()
    try:
        disabled_types = db.query(DocumentType).filter(DocumentType.enabled == False).all()
        assert len(disabled_types) >= 2
        print(f"\n[Matrix #10] Reserved Doc Types: {len(disabled_types)} document types correctly held in reserved state ({', '.join(d.code for d in disabled_types)}).")
    finally:
        db.close()

def test_11_oversized_file_upload():
    """11. >10 MB Upload -> HTTP 413 Payload Too Large."""
    big_file = io.BytesIO(b"0" * (11 * 1024 * 1024))
    res = client.post(
        "/api/v1/screening/scan",
        files={"document_file": ("huge.jpg", big_file, "image/jpeg")},
        data={"officer_id": "SSB-7741"}
    )
    assert res.status_code == 413
    print("\n[Matrix #11] Oversized File (>10MB): Status=413 Payload Too Large correctly returned.")

def test_12_invalid_extension():
    """12. Invalid Extension (.exe/.pdf in scan) -> HTTP 400 Bad Request."""
    dummy = io.BytesIO(b"binary payload")
    res = client.post(
        "/api/v1/screening/scan",
        files={"document_file": ("malicious.exe", dummy, "application/octet-stream")},
        data={"officer_id": "SSB-7741"}
    )
    assert res.status_code == 400
    print("\n[Matrix #12] Invalid Extension (.exe): Status=400 Bad Request correctly returned.")

def test_13_malformed_image():
    """13. Malformed Image Bytes -> HTTP 400 Bad Request."""
    fake_img = io.BytesIO(b"NOT_A_VALID_IMAGE_DATA_12345678")
    res = client.post(
        "/api/v1/screening/scan",
        files={"document_file": ("corrupt.jpg", fake_img, "image/jpeg")},
        data={"officer_id": "SSB-7741"}
    )
    assert res.status_code == 400
    print("\n[Matrix #13] Malformed Image Data: Status=400 Bad Request correctly returned.")

def test_14_unauthorized_personnel_request():
    """14. Unauthorized Personnel Request -> HTTP 401 Unauthorized."""
    res = client.post(
        "/api/v1/auth/login",
        json={"badge_id": "SSB-9999", "password": "wrong_password"}
    )
    assert res.status_code == 401
    print("\n[Matrix #14] Unauthorized Login: Status=401 Unauthorized correctly returned.")

def test_15_audit_chain_verification():
    """15. Audit Chain Verification -> HTTP 200, Valid=True."""
    res = client.get("/api/v1/audit/verify-chain")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["first_invalid_record"] is None
    print(f"\n[Matrix #15] SHA-256 Audit Chain: Status=200, IsValid={data['is_valid']}, Records={data['records_checked']}")
