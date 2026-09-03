import pytest  # type: ignore
import numpy as np
from app.services.ocr.ocr_engine import OCREngine
from app.services.ocr.passport_parser import PassportParser
from app.services.ocr.aadhaar_parser import AadhaarParser
from app.services.ocr.dl_parser import DrivingLicenceParser

def test_passport_parser_detect():
    parser = PassportParser()
    assert parser.detect(["P<INDSINGH<<ARJUN<<<<<<<<<<<<<<<<<<<<<<"], "PASSPORT REPUBLIC OF INDIA") is True
    assert parser.detect([], "DRIVING LICENCE UNION OF INDIA") is False

def test_aadhaar_parser_detect():
    parser = AadhaarParser()
    assert parser.detect([], "GOVERNMENT OF INDIA UNIQUE IDENTIFICATION AADHAAR") is True
    assert parser.detect([], "PASSPORT REPUBLIC OF INDIA") is False

def test_dl_parser_detect():
    parser = DrivingLicenceParser()
    assert parser.detect(["DL-1420110098231"], "DRIVING LICENCE UNION OF INDIA") is True
    assert parser.detect([], "AADHAAR CARD") is False

def test_ocr_not_detected_fallback():
    dummy_img = np.full((100, 100, 3), 255, dtype=np.uint8)
    parser = PassportParser()
    extracted = parser.extract(dummy_img, [], "")
    # Fields that cannot be detected must return 'NOT_DETECTED'
    assert extracted["passport_number"]["value"] == "NOT_DETECTED"
    assert extracted["dob"]["value"] == "NOT_DETECTED"

def test_ocr_engine_pipeline():
    engine = OCREngine()
    dummy_img = np.full((200, 400, 3), 240, dtype=np.uint8)
    res = engine.extract_document_data(dummy_img)
    assert "document_type" in res
    assert "extracted_fields" in res
    assert "validation_flags" in res
