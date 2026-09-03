import pytest  # type: ignore
import io
import numpy as np
import cv2  # type: ignore
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def sample_image_bytes():
    """Generates a dummy 300x200 JPEG image in-memory."""
    img = np.ones((200, 300, 3), dtype=np.uint8) * 240
    cv2.putText(img, "TEST DOC", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

def test_system_status():
    """GET /api/v1/system/status returns operational readiness."""
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert data["offline_mode"] is True
    assert "ocr_engine" in data["subsystems"]
    assert "face_model" in data["subsystems"]
    assert "liveness" in data["subsystems"]
    assert "database" in data["subsystems"]

def test_auth_login():
    """POST /api/v1/auth/login allows officer and supervisor login."""
    res = client.post("/api/v1/auth/login", json={"badge_id": "SSB-7741", "password": "officer123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["badge_id"] == "SSB-7741"


def test_upload_document(sample_image_bytes):
    """POST /api/v1/screening/upload-document ingests doc and returns classification and fields."""
    files = {"document_file": ("sample_passport.jpg", sample_image_bytes, "image/jpeg")}
    res = client.post("/api/v1/screening/upload-document", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "document_path" in data
    assert "document_type" in data
    assert "extracted_fields" in data
    assert "ocr_status" in data

def test_analyze_forensics(sample_image_bytes):
    """POST /api/v1/screening/analyze-forensics analyzes tampering signals."""
    files = {"document_file": ("test_doc.jpg", sample_image_bytes, "image/jpeg")}
    res = client.post("/api/v1/screening/analyze-forensics", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "ela_score" in data
    assert "exif_score" in data
    assert "boundary_score" in data
    assert "overall_tampering_score" in data

def test_verify_face(sample_image_bytes):
    """POST /api/v1/screening/verify-face compares document face with live traveler."""
    files = {"live_photo": ("live_test.jpg", sample_image_bytes, "image/jpeg")}
    res = client.post("/api/v1/screening/verify-face", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "similarity_score" in data
    assert "match_status" in data
    assert "liveness_passed" in data

def test_evaluate_risk():
    """POST /api/v1/screening/evaluate-risk evaluates subscores and standardized flags."""
    payload = {
        "validation_flags": [
            {"code": "MRZ_VALID", "title": "MRZ Valid", "message": "MRZ OK", "severity": "LOW", "source": "MRZ"}
        ],
        "tampering_score": 10.0,
        "face_match_score": 88.0,
        "liveness_passed": True,
        "duplicate_flag": False
    }
    res = client.post("/api/v1/screening/evaluate-risk", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "overall_risk_score" in data
    assert data["risk_level"] == "LOW"
    assert "components" in data
    assert data["components"]["validation"]["max"] == 25
    assert data["components"]["forensics"]["max"] == 40
    assert data["components"]["face"]["max"] == 35

def test_audit_logs_and_verify_chain():
    """GET /api/v1/audit/logs and GET /api/v1/audit/verify-chain."""
    res_logs = client.get("/api/v1/audit/logs")
    assert res_logs.status_code == 200
    logs = res_logs.json()
    assert isinstance(logs, list)
    if logs:
        # Verify masked_document_number is present
        assert "masked_document_number" in logs[0]

    res_chain = client.get("/api/v1/audit/verify-chain")
    assert res_chain.status_code == 200
    chain = res_chain.json()
    assert "is_valid" in chain
    assert "records_checked" in chain
    assert "verification_timestamp" in chain
    assert chain["valid"] is True

def test_audit_export_csv():
    """GET /api/v1/audit/export returns valid CSV stream with download headers."""
    res = client.get("/api/v1/audit/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    
    content = res.text
    lines = content.strip().splitlines()
    assert len(lines) >= 1
    # Check header row
    assert "timestamp,checkpoint,officer,document_type,masked_document_number,risk_score,risk_level,decision,major_flags" in lines[0]

def test_upload_security_invalid_extension():
    """POST /api/v1/screening/upload-document rejects unauthorized file extensions."""
    files = {"document_file": ("malicious_script.exe", b"MZ\x90\x00executable", "application/x-msdownload")}
    res = client.post("/api/v1/screening/upload-document", files=files)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json().get("detail", "")

def test_upload_security_oversized_file():
    """POST /api/v1/screening/upload-document rejects files exceeding 10MB."""
    oversized = b"0" * (11 * 1024 * 1024) # 11MB
    files = {"document_file": ("oversized.jpg", oversized, "image/jpeg")}
    res = client.post("/api/v1/screening/upload-document", files=files)
    assert res.status_code == 413
    assert "exceeds maximum allowable limit" in res.json().get("detail", "")

def test_verify_face_reports_engine(sample_image_bytes):
    """POST /api/v1/screening/verify-face transparently reports the active biometric engine."""
    files = {"live_photo": ("live_test.jpg", sample_image_bytes, "image/jpeg")}
    res = client.post("/api/v1/screening/verify-face", files=files)
    assert res.status_code == 200
    data = res.json()
    assert "engine" in data
    assert "512-D" in data["engine"] or "ArcFace" in data["engine"]
    assert "liveness_steps" in data

def test_reference_blacklist():
    """GET and POST /api/v1/reference/blacklist."""
    res_get = client.get("/api/v1/reference/blacklist")
    assert res_get.status_code == 200
    items = res_get.json()
    assert isinstance(items, list)

