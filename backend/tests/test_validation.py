import pytest  # type: ignore
from app.services.validation.format_rules import (
    validate_verhoeff, compute_verhoeff_check_digit,
    validate_passport_number, validate_dl_number
)
from app.services.validation.mrz_validator import parse_and_validate_mrz, cross_check_mrz_vs_printed
from app.services.validation.reference_checker import check_blacklist, check_expiry
from app.core.database import SessionLocal
from app.db.init_db import init_db

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_valid_and_invalid_mrz():
    # Valid ICAO 9303 TD3 MRZ lines
    valid_lines = [
        "P<INDSINGH<<SHUBHAM<SURAJ<<<<<<<<<<<<<<<<<<<",
        "Z9982341<7IND9608144M3005095<<<<<<<<<<<<<<04"
    ]
    res_valid = parse_and_validate_mrz(valid_lines)
    assert res_valid["valid_mrz"] is True
    assert res_valid["passport_number"] == "Z9982341"
    assert res_valid["checksum_valid"] is True
    assert len([f for f in res_valid["flags"] if f["code"] == "MRZ_CHECKSUM_MISMATCH"]) == 0


    # Tampered MRZ with corrupted check digit
    tampered_lines = [
        "P<INDSINGH<<SHUBHAM<SURAJ<<<<<<<<<<<<<<<<<<<",
        "Z9982341<9IND9608144M3005094<<<<<<<<<<<<<<<04"
    ]
    res_tampered = parse_and_validate_mrz(tampered_lines)
    assert res_tampered["checksum_valid"] is False
    assert any(f["code"] == "MRZ_CHECKSUM_MISMATCH" for f in res_tampered["flags"])

def test_aadhaar_verhoeff_checksum():
    # Valid Aadhaar numbers generated via Verhoeff
    base = "23456789012"
    chk = compute_verhoeff_check_digit(base)
    valid_aadhaar = base + chk
    assert validate_verhoeff(valid_aadhaar) is True

    # Invalid Aadhaar numbers
    invalid_aadhaar = base + ("0" if chk != "0" else "1")
    assert validate_verhoeff(invalid_aadhaar) is False
    assert validate_verhoeff("123456") is False
    assert validate_verhoeff("short_bad_no") is False

def test_cross_field_validation():
    mrz_data = {
        "valid_mrz": True,
        "passport_number": "Z9982341",
        "surname": "SINGH",
        "dob": "960814",
        "expiry_date": "300509"
    }

    # Case 1: Matching printed text
    printed_matching = {
        "passport_number": "Z9982341",
        "name": "SHUBHAM SURAJ SINGH",
        "dob": "14/08/1996"
    }
    flags_match = cross_check_mrz_vs_printed(mrz_data, printed_matching)
    assert len(flags_match) == 0

    # Case 2: Mismatched DOB (Altered printed text)
    printed_mismatched = {
        "passport_number": "Z9982341",
        "name": "SHUBHAM SURAJ SINGH",
        "dob": "01/01/1985"
    }
    flags_mismatch = cross_check_mrz_vs_printed(mrz_data, printed_mismatched)
    assert any(f["code"] == "DOB_MRZ_MISMATCH" for f in flags_mismatch)

def test_reference_blacklist_match(db_session):
    # Z9982341 is seeded in synthetic watchlist
    flags = check_blacklist(db_session, "Z9982341", "PASSPORT")
    assert len(flags) > 0
    assert flags[0]["code"] == "BLACKLIST_MATCH"

    # Clean non-blacklisted number
    clean_flags = check_blacklist(db_session, "K1234567", "PASSPORT")
    assert len(clean_flags) == 0

def test_document_expiry():
    expired_flags = check_expiry("01/01/2020")
    assert len(expired_flags) > 0
    assert expired_flags[0]["code"] == "DOCUMENT_EXPIRED"

    future_flags = check_expiry("01/01/2035")
    assert len(future_flags) == 0
