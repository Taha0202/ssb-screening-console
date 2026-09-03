from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, computed_field
from app.core.security import mask_document_number

class ScreeningLogResponse(BaseModel):
    id: str
    timestamp: datetime
    checkpoint_location: str
    officer_id: Optional[str] = None
    document_type: str
    document_number: Optional[str] = None
    holder_name: Optional[str] = None
    raw_document_image_path: str
    raw_live_photo_path: str
    tamper_heatmap_path: Optional[str] = None
    extracted_data_json: Dict[str, Any]
    validation_flags_json: List[Dict[str, Any]]
    tampering_score: float
    face_match_score: float
    overall_risk_score: float
    risk_level: str
    officer_decision: Optional[str] = "PENDING"
    officer_notes: Optional[str] = None
    prev_log_hash: str
    record_hash: str

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def masked_document_number(self) -> str:
        return mask_document_number(self.document_number, self.document_type)


class AuditChainVerificationResponse(BaseModel):
    valid: bool
    is_valid: bool
    records_checked: int
    total_records: int
    verification_timestamp: str
    first_invalid_record: Optional[str] = None
    first_invalid_record_id: Optional[str] = None
    message: str


