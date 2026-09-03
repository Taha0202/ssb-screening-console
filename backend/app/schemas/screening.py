from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class OCRField(BaseModel):
    value: Optional[str] = "NOT_DETECTED"
    confidence: float = 0.0

class ValidationFlag(BaseModel):
    code: str
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    title: str = ""
    message: str
    source: str = "Validation"  # 'Validation', 'Reference', 'Forensics', 'Biometrics'

class TamperingSignals(BaseModel):
    ela_score: float = 0.0
    exif_score: float = 0.0
    boundary_score: float = 0.0
    jpeg_score: float = 0.0
    overall_tampering_score: float = 0.0
    heatmap_url: Optional[str] = None
    exif_flags: List[str] = []

class FaceVerificationResult(BaseModel):
    similarity_score: float = 0.0
    match_status: str = "MATCH"  # 'MATCH', 'REVIEW', 'MISMATCH'
    engine: str = "OpenCV-SpatialGradient-512D (Offline Fallback)"
    liveness_passed: bool = True
    liveness_details: str = "Liveness verified"
    liveness_steps: Optional[Dict[str, Any]] = None
    duplicate_identity_flag: bool = False
    duplicate_matched_doc: Optional[str] = None


class RiskEvaluationResult(BaseModel):
    overall_risk_score: float = 0.0
    risk_level: str = "LOW"  # 'LOW', 'MEDIUM', 'HIGH'
    flags: List[ValidationFlag] = []
    components: Optional[Dict[str, Any]] = None

class EvaluateRiskRequest(BaseModel):
    validation_flags: List[Dict[str, Any]] = []
    tampering_score: float = 0.0
    face_match_score: float = 85.0
    liveness_passed: bool = True
    duplicate_flag: bool = False



class ModuleTimings(BaseModel):
    ocr_seconds: float = 0.0
    validation_seconds: float = 0.0
    tampering_seconds: float = 0.0
    biometrics_seconds: float = 0.0
    risk_seconds: float = 0.0
    total_seconds: float = 0.0
    ocr_time_ms: float = 0.0
    forensics_time_ms: float = 0.0
    biometric_time_ms: float = 0.0
    total_time_ms: float = 0.0

class ScreeningResponse(BaseModel):
    screening_id: str
    checkpoint_id: Optional[str] = None
    checkpoint_location: Optional[str] = None
    document_type: str
    extracted_fields: Dict[str, Any]
    validation_flags: List[ValidationFlag]
    tampering: TamperingSignals
    face_verification: FaceVerificationResult
    risk_assessment: RiskEvaluationResult
    raw_document_url: str
    raw_live_photo_url: Optional[str] = None
    module_timings: Optional[ModuleTimings] = None
    pipeline_version: str = "2.0.0"


from pydantic import BaseModel, model_validator

class DecisionRequest(BaseModel):
    screening_id: str
    officer_decision: str = "APPROVED"  # 'APPROVED', 'REJECTED', 'ESCALATED', 'PENDING'
    officer_notes: Optional[str] = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "decision" in data and "officer_decision" not in data:
                data["officer_decision"] = data["decision"]
            if "notes" in data and "officer_notes" not in data:
                data["officer_notes"] = data["notes"]
            
            raw_dec = str(data.get("officer_decision", "APPROVED")).strip().upper()
            mapping = {
                "APPROVE": "APPROVED",
                "APPROVED": "APPROVED",
                "REJECT": "REJECTED",
                "REJECTED": "REJECTED",
                "ESCALATE": "ESCALATED",
                "ESCALATED": "ESCALATED",
                "PENDING": "PENDING"
            }
            data["officer_decision"] = mapping.get(raw_dec, "APPROVED")
        return data
