import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_documents")

def test_scenario_1_genuine_passport():
    """Scenario 1: Genuine Passport + Matching Traveler -> LOW RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_genuine.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")

    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_passport_genuine.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg"),
            },
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["document_type"] == "PASSPORT"
    assert data["risk_assessment"]["risk_level"] == "LOW"
    assert data["face_verification"]["similarity_score"] >= 70.0

def test_scenario_2_tampered_passport():
    """Scenario 2: Tampered Passport + Matching Traveler -> HIGH RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_tampered.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")

    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_passport_tampered.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg"),
            },
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "HIGH"
    assert data["tampering"]["overall_tampering_score"] > 20.0

def test_scenario_3_face_mismatch():
    """Scenario 3: Genuine Passport + Mismatch Traveler -> HIGH RISK."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_genuine.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_mismatch.jpg")

    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_passport_genuine.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_mismatch.jpg", f_live, "image/jpeg"),
            },
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "HIGH"
    assert data["face_verification"]["similarity_score"] < 50.0

def test_scenario_4_blacklisted_document():
    """Scenario 4: Blacklisted Passport -> HIGH RISK with Lookout Flag."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_blacklisted.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")

    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_passport_blacklisted.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg"),
            },
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["risk_assessment"]["risk_level"] == "HIGH"

def test_scenario_5_tampered_aadhaar():
    """Scenario 5: Tampered Aadhaar -> Detected / Checksum Failure."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_aadhaar_tampered.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")

    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_aadhaar_tampered.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg"),
            },
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["document_type"] == "AADHAAR"

def test_end_to_end_screening_workflow():
    """Full Flow: Scan -> Review -> Officer Decision -> Audit Log -> Verify Chain -> Export CSV."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_genuine.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")

    # 1. SCAN
    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        scan_res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_passport_genuine.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg"),
            },
            data={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint"}
        )
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    screening_id = scan_data["screening_id"]

    # 2. OFFICER DECISION
    decision_res = client.post(
        "/api/v1/screening/record-decision",
        json={
            "screening_id": screening_id,
            "decision": "APPROVE",
            "notes": "Verified genuine passport and matching biometrics at Raxaul gate."
        }
    )
    assert decision_res.status_code == 200
    decision_data = decision_res.json()
    assert decision_data["status"] == "SUCCESS"
    assert "record_hash" in decision_data

    # 3. AUDIT LOG RETRIEVAL
    audit_res = client.get("/api/v1/audit/logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    match = next((l for l in logs if l["id"] == screening_id), None)
    assert match is not None
    assert match["officer_decision"] == "APPROVED"
    assert "masked_document_number" in match

    # 4. VERIFY CRYPTOGRAPHIC CHAIN
    verify_res = client.get("/api/v1/audit/verify-chain")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_valid"] is True
    assert verify_data["records_checked"] >= 1

    # 5. EXPORT CSV
    export_res = client.get("/api/v1/audit/export")
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers.get("content-type", "")
    assert "timestamp,checkpoint,officer" in export_res.text
