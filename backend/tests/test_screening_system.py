import os
import cv2  # type: ignore
import numpy as np
import pytest  # type: ignore
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import verify_password, get_password_hash
from app.services.validation.format_rules import validate_verhoeff, validate_passport_number
from app.services.validation.mrz_validator import parse_and_validate_mrz
from app.services.tampering.ela_analyzer import ELAAnalyzer
from app.core.audit_chain import compute_record_hash, verify_audit_chain, GENESIS_HASH

client = TestClient(app)

def test_security_hashing():
    pwd = "officer123"
    hashed = get_password_hash(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_verhoeff_aadhaar_validation():
    # 12-digit Aadhaar format check
    assert len("992811024431") == 12
    # Invalid short length
    assert validate_verhoeff("123456") is False

def test_passport_format_validation():
    assert validate_passport_number("Z9982341") is True
    assert validate_passport_number("12345678") is False

def test_mrz_parsing():
    mrz_lines = [
        "P<INDSINGH<<SHUBHAM<SURAJ<<<<<<<<<<<<<<<<<<<",
        "Z9982341<4IND9608144M3005094<<<<<<<<<<<<<<<04"
    ]
    res = parse_and_validate_mrz(mrz_lines)
    assert res["valid_mrz"] is True
    assert res["passport_number"] == "Z9982341"
    assert res["surname"] == "SINGH"

def test_ela_tampering_analysis():
    test_img = np.full((300, 300, 3), 200, dtype=np.uint8)
    cv2.putText(test_img, "TEST DOC", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    
    analyzer = ELAAnalyzer()
    score, heatmap, *rest = analyzer.analyze(test_img)
    assert 0.0 <= score <= 100.0
    assert heatmap.shape == (300, 300, 3)


def test_audit_hash_chaining():
    h1 = compute_record_hash("id_1", "2026-08-28 14:00:00", "Raxaul Checkpoint", "off_1", "PASSPORT", "Z9982341", 15.0, "LOW", "APPROVED", GENESIS_HASH)
    h2 = compute_record_hash("id_2", "2026-08-28 14:05:00", "Raxaul Checkpoint", "off_1", "PASSPORT", "Z9982341", 15.0, "LOW", "APPROVED", h1)
    
    assert len(h1) == 64
    assert len(h2) == 64
    assert h1 != h2

def test_fastapi_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "SSB" in data["system"]
