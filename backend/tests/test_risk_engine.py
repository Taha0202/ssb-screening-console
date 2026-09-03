import pytest  # type: ignore
from app.services.risk.scoring_engine import RiskScoringEngine
from app.schemas.screening import ValidationFlag

def test_risk_low_clean_document():
    engine = RiskScoringEngine()
    flags = []
    res = engine.evaluate_risk(
        validation_flags=flags,
        tampering_score=12.0,
        face_match_score=88.5,
        liveness_passed=True,
        duplicate_flag=False
    )
    assert res["risk_level"] == "LOW"
    assert res["overall_risk_score"] < 30.0

def test_risk_high_blacklisted_document():
    engine = RiskScoringEngine()
    flags = [
        ValidationFlag(
            code="BLACKLIST_MATCH",
            title="Watchlist Match",
            message="Document flagged in watchlist.",
            severity="CRITICAL",
            source="Reference"
        )
    ]
    res = engine.evaluate_risk(
        validation_flags=flags,
        tampering_score=15.0,
        face_match_score=85.0,
        liveness_passed=True,
        duplicate_flag=False
    )
    assert res["risk_level"] == "HIGH"
    assert res["overall_risk_score"] >= 88.0 # Critical security floor

def test_risk_high_severe_face_mismatch():
    engine = RiskScoringEngine()
    flags = []
    res = engine.evaluate_risk(
        validation_flags=flags,
        tampering_score=10.0,
        face_match_score=18.0, # Severe biometric mismatch
        liveness_passed=True,
        duplicate_flag=False
    )
    assert res["risk_level"] == "HIGH"
    assert res["overall_risk_score"] >= 75.0

def test_risk_medium_cautionary():
    engine = RiskScoringEngine()
    flags = [
        ValidationFlag(
            code="DOCUMENT_EXPIRED",
            title="Document Expired",
            message="Document expired.",
            severity="MEDIUM",
            source="Validation"
        )
    ]
    res = engine.evaluate_risk(
        validation_flags=flags,
        tampering_score=25.0,
        face_match_score=75.0,
        liveness_passed=True,
        duplicate_flag=False
    )
    assert res["risk_level"] in ["LOW", "MEDIUM"]
