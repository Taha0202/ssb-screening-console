from typing import List, Dict, Any
from app.schemas.screening import ValidationFlag
from app.core.config import (
    TAMPERING_WEIGHT, FACE_WEIGHT, VALIDATION_WEIGHT,
    RISK_LOW_THRESHOLD, RISK_HIGH_THRESHOLD
)

FLAG_CATALOG = {
    "MRZ_CHECKSUM_MISMATCH": {
        "title": "MRZ Checksum Failure",
        "severity": "HIGH",
        "default_message": "The machine-readable passport data contains an invalid checksum.",
        "source": "Validation"
    },
    "PASSPORT_NUMBER_MISMATCH": {
        "title": "Passport Number Inconsistency",
        "severity": "HIGH",
        "default_message": "Passport number in MRZ does not match printed visual text.",
        "source": "Validation"
    },
    "DOB_MRZ_MISMATCH": {
        "title": "Date of Birth Mismatch",
        "severity": "HIGH",
        "default_message": "The date of birth extracted from printed document does not match the machine-readable zone.",
        "source": "Validation"
    },
    "NAME_MRZ_MISMATCH": {
        "title": "Holder Name Mismatch",
        "severity": "HIGH",
        "default_message": "Surname or given name in MRZ is inconsistent with printed name.",
        "source": "Validation"
    },
    "INVALID_AADHAAR_VERHOEFF": {
        "title": "Invalid Aadhaar Verhoeff Checksum",
        "severity": "HIGH",
        "default_message": "The 12-digit Aadhaar number failed mathematical Verhoeff checksum validation.",
        "source": "Validation"
    },
    "BLACKLIST_MATCH": {
        "title": "Reference Database Watchlist Match",
        "severity": "HIGH",
        "default_message": "The document number matches a locally configured synthetic watchlist record.",
        "source": "Reference"
    },
    "BLACKLISTED_DOCUMENT": {
        "title": "Reference Database Watchlist Match",
        "severity": "HIGH",
        "default_message": "Document flagged in synthetic border security alert database.",
        "source": "Reference"
    },
    "DOCUMENT_EXPIRED": {
        "title": "Document Expired",
        "severity": "MEDIUM",
        "default_message": "Document date of expiry has passed. Travel credentials are not valid.",
        "source": "Validation"
    },
    "PHOTO_BOUNDARY_ANOMALY": {
        "title": "Photo Boundary Anomaly",
        "severity": "HIGH",
        "default_message": "The document photo region contains unusual edge discontinuities or splicing tells.",
        "source": "Forensics"
    },
    "ELA_ANOMALY": {
        "title": "Potential Image Manipulation (ELA)",
        "severity": "MEDIUM",
        "default_message": "Compression-level error differences were detected in parts of the document image.",
        "source": "Forensics"
    },
    "JPEG_ARTIFACT_ANOMALY": {
        "title": "JPEG Compression Grid Inconsistency",
        "severity": "MEDIUM",
        "default_message": "Misaligned 8x8 block DCT quantization grids indicate possible multi-layer composition.",
        "source": "Forensics"
    },
    "FACE_MISMATCH": {
        "title": "Face Similarity Below Threshold",
        "severity": "HIGH",
        "default_message": "The captured traveler image has low biometric similarity to the document photograph.",
        "source": "Biometrics"
    },
    "LIVENESS_FAILED": {
        "title": "Liveness Verification Failed",
        "severity": "HIGH",
        "default_message": "Traveler failed active liveness challenge. Potential flat print or replay attack.",
        "source": "Biometrics"
    },
    "DUPLICATE_IDENTITY_RECORD": {
        "title": "Potential Duplicate Identity",
        "severity": "HIGH",
        "default_message": "A highly similar facial biometric is associated with another synthetic identity record.",
        "source": "Biometrics"
    }
}

class RiskScoringEngine:
    """
    Dedicated decision-support risk scoring engine.
    Calculates weighted normalized risk score (0-100), categorizes risk level (LOW/MEDIUM/HIGH),
    and standardizes plain-language, explainable findings for human officer review.
    """

    def __init__(self):
        self.tampering_weight = TAMPERING_WEIGHT
        self.face_weight = FACE_WEIGHT
        self.validation_weight = VALIDATION_WEIGHT
        self.low_threshold = RISK_LOW_THRESHOLD
        self.high_threshold = RISK_HIGH_THRESHOLD

    def evaluate_risk(
        self,
        validation_flags: List[ValidationFlag],
        tampering_score: float,
        face_match_score: float,
        liveness_passed: bool,
        duplicate_flag: bool
    ) -> Dict[str, Any]:
        # 1. Validation & Reference Sub-Score (0-100)
        val_score = 0.0
        for flag in validation_flags:
            if flag.severity in ["HIGH", "CRITICAL"]:
                val_score += 45.0
            elif flag.severity == "MEDIUM":
                val_score += 20.0
            elif flag.severity == "LOW":
                val_score += 10.0

        if duplicate_flag:
            val_score += 50.0

        val_score = min(100.0, val_score)

        # 2. Biometric Mismatch Sub-Score (0-100)
        face_mismatch_score = max(0.0, 100.0 - face_match_score)
        if not liveness_passed:
            face_mismatch_score = max(face_mismatch_score, 80.0)

        # 3. Overall Weighted Risk Score
        total_risk = (
            (tampering_score * self.tampering_weight) +
            (face_mismatch_score * self.face_weight) +
            (val_score * self.validation_weight)
        )

        # Security Escalation Floors for Critical Threats
        has_blacklist = any(
            f.code in ["BLACKLIST_MATCH", "BLACKLISTED_DOCUMENT"] for f in validation_flags
        )
        has_severe_face_mismatch = face_match_score < 45.0
        has_severe_tampering = tampering_score >= 45.0
        has_invalid_id = any(
            f.code in ["INVALID_AADHAAR_VERHOEFF", "MRZ_CHECKSUM_MISMATCH"] for f in validation_flags
        )

        if has_blacklist:
            total_risk = max(total_risk, 88.0)
        elif has_severe_face_mismatch:
            total_risk = max(total_risk, 78.0)
        elif has_severe_tampering:
            total_risk = max(total_risk, 74.0)
        elif has_invalid_id:
            total_risk = max(total_risk, 70.0)

        total_risk = round(min(100.0, max(0.0, total_risk)), 2)

        # 4. Categorize Risk Level
        if total_risk < self.low_threshold:
            risk_level = "LOW"
        elif total_risk <= self.high_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # 5. Enrich and standardize explainable flags
        standardized_flags = self._standardize_flags(
            validation_flags, tampering_score, face_match_score, liveness_passed, duplicate_flag
        )

        # Scale sub-scores to exact requested breakdown:
        # Validation: /25, Forensics: /40, Face: /35 -> Total: /100
        val_comp = round((val_score / 100.0) * 25.0, 1)
        tamper_comp = round((tampering_score / 100.0) * 40.0, 1)
        face_comp = round((face_mismatch_score / 100.0) * 35.0, 1)

        # If escalation floor lifted total_risk higher, adjust components proportionally
        raw_sum = val_comp + tamper_comp + face_comp
        if total_risk > raw_sum and raw_sum > 0:
            scale_factor = total_risk / raw_sum
            val_comp = round(min(25.0, val_comp * scale_factor), 1)
            tamper_comp = round(min(40.0, tamper_comp * scale_factor), 1)
            face_comp = round(min(35.0, face_comp * scale_factor), 1)

        return {
            "overall_risk_score": total_risk,
            "risk_level": risk_level,
            "validation_subscore": val_score,
            "tampering_subscore": tampering_score,
            "face_mismatch_subscore": face_mismatch_score,
            "components": {
                "validation": {"score": val_comp, "max": 25, "label": "Validation"},
                "forensics": {"score": tamper_comp, "max": 40, "label": "Document Forensics"},
                "face": {"score": face_comp, "max": 35, "label": "Face Verification"}
            },
            "flags": standardized_flags
        }


    def _standardize_flags(
        self,
        flags: List[ValidationFlag],
        tampering_score: float,
        face_match_score: float,
        liveness_passed: bool,
        duplicate_flag: bool
    ) -> List[ValidationFlag]:
        out_flags: List[ValidationFlag] = []
        seen_codes = set()

        for f in flags:
            code = f.code.upper()
            seen_codes.add(code)
            catalog_entry = FLAG_CATALOG.get(code, {})
            title = f.title or catalog_entry.get("title", code.replace("_", " ").title())
            sev = f.severity or catalog_entry.get("severity", "MEDIUM")
            source = f.source or catalog_entry.get("source", "Validation")
            out_flags.append(ValidationFlag(
                code=code,
                title=title,
                message=f.message or catalog_entry.get("default_message", "Inconsistency detected."),
                severity=sev,
                source=source
            ))

        # Check additional synthesized indicators
        if tampering_score > 35.0 and "PHOTO_BOUNDARY_ANOMALY" not in seen_codes and "ELA_ANOMALY" not in seen_codes:
            out_flags.append(ValidationFlag(
                code="PHOTO_BOUNDARY_ANOMALY",
                title="Photo Boundary Anomaly",
                message=f"Forensic indicators detected potential image manipulation (Tampering Score: {tampering_score}/100).",
                severity="HIGH" if tampering_score > 55.0 else "MEDIUM",
                source="Forensics"
            ))

        if face_match_score < 70.0 and "FACE_MISMATCH" not in seen_codes:
            out_flags.append(ValidationFlag(
                code="FACE_MISMATCH",
                title="Face Similarity Below Threshold",
                message=f"Captured traveler image has low biometric similarity to document photo (Match Score: {face_match_score}%).",
                severity="HIGH" if face_match_score < 50.0 else "MEDIUM",
                source="Biometrics"
            ))

        if not liveness_passed and "LIVENESS_FAILED" not in seen_codes:
            out_flags.append(ValidationFlag(
                code="LIVENESS_FAILED",
                title="Liveness Verification Failed",
                message="Live traveler photo failed basic liveness check (Potential paper print or screen replay attack).",
                severity="HIGH",
                source="Biometrics"
            ))

        if duplicate_flag and "DUPLICATE_IDENTITY_RECORD" not in seen_codes:
            out_flags.append(ValidationFlag(
                code="DUPLICATE_IDENTITY_RECORD",
                title="Potential Duplicate Identity",
                message="SECURITY ALERT: Facial biometric matches an existing record under a different document number/name.",
                severity="HIGH",
                source="Biometrics"
            ))

        return out_flags
