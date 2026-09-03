import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.db.models import Checkpoint, Officer, ForensicReport, ScreeningLog

client = TestClient(app)
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_documents")

def test_system_health_endpoint():
    """Verify standard system health and local inference status."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "connected"
    assert data["ai_inference_mode"] == "LOCAL / OFFLINE"
    assert data["version"] == "2.0.0"
    assert data["offline_mode"] is True
    assert data["ocr_engine"] == "available"
    assert data["forensics"] == "available"
    assert data["active_checkpoints_count"] >= 5
    assert data["reference_records_count"] >= 1

def test_list_checkpoints():
    """Verify registered checkpoints can be listed and filtered."""
    res = client.get("/api/v1/checkpoints")
    assert res.status_code == 200
    checkpoints = res.json()
    assert len(checkpoints) >= 5
    codes = [c["checkpoint_code"] for c in checkpoints]
    assert "CP-RAXAUL-01" in codes
    assert "CP-RANIGANJ-01" in codes
    assert "CP-PANITANKI-01" in codes

def test_create_and_get_checkpoint():
    """Verify creating a new border checkpoint and retrieving details."""
    new_code = f"CP-TEST-{os.urandom(2).hex().upper()}"
    create_res = client.post(
        "/api/v1/checkpoints",
        json={
            "checkpoint_code": new_code,
            "name": "Test Frontier Post Alpha",
            "location": "Indo-Nepal Sector 9",
            "state": "Bihar",
            "district": "Sitamarhi",
            "status": "ACTIVE"
        }
    )
    assert create_res.status_code == 201
    created_cp = create_res.json()
    assert created_cp["checkpoint_code"] == new_code

    # Retrieve detail
    get_res = client.get(f"/api/v1/checkpoints/{created_cp['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test Frontier Post Alpha"

def test_officer_management_and_login():
    """Verify creating personnel, assigning checkpoint, and logging in."""
    unique_badge = f"SSB-TEST-{os.urandom(2).hex().upper()}"
    create_res = client.post(
        "/api/v1/officers",
        json={
            "badge_id": unique_badge,
            "full_name": "Assistant Commandant V. Verma",
            "role": "OFFICER",
            "checkpoint_location": "Raxaul Checkpoint",
            "password": "SecurePassword123!",
            "status": "ACTIVE"
        }
    )
    assert create_res.status_code == 201
    officer_data = create_res.json()
    assert officer_data["badge_id"] == unique_badge

    # Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"badge_id": unique_badge, "password": "SecurePassword123!"}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["badge_id"] == unique_badge
    assert login_data["user"]["role"] == "OFFICER"

def test_screening_with_telemetry_and_checkpoint():
    """Verify document scan records millisecond telemetry and links checkpoint and forensic report."""
    doc_path = os.path.join(SAMPLE_DIR, "sample_passport_genuine.jpg")
    live_path = os.path.join(SAMPLE_DIR, "sample_traveler_match.jpg")

    with open(doc_path, "rb") as f_doc, open(live_path, "rb") as f_live:
        res = client.post(
            "/api/v1/screening/scan",
            files={
                "document_file": ("sample_passport_genuine.jpg", f_doc, "image/jpeg"),
                "live_photo_file": ("sample_traveler_match.jpg", f_live, "image/jpeg"),
            },
            data={
                "officer_id": "SSB-7741",
                "checkpoint_location": "Raxaul Checkpoint"
            }
        )

    assert res.status_code == 200
    data = res.json()
    assert "screening_id" in data
    assert "module_timings" in data
    timings = data["module_timings"]
    assert "ocr_time_ms" in timings
    assert "forensics_time_ms" in timings
    assert "biometric_time_ms" in timings
    assert "total_time_ms" in timings
    assert data["pipeline_version"] == "2.0.0"

    # Verify ForensicReport persisted in database
    db = SessionLocal()
    try:
        report = db.query(ForensicReport).filter(ForensicReport.screening_id == data["screening_id"]).first()
        assert report is not None
        assert report.pipeline_version == "2.0.0"
        assert report.overall_tampering_score is not None
    finally:
        db.close()

def test_audit_logs_checkpoint_filter():
    """Verify audit logs can be filtered by checkpoint location."""
    res = client.get("/api/v1/audit/logs?checkpoint_location=Raxaul")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    for log in logs:
        if log.get("checkpoint_location"):
            assert "Raxaul" in log["checkpoint_location"]
