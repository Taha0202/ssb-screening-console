import re
from typing import Dict, Any, List
import numpy as np
from app.services.ocr.base_parser import BaseDocumentParser
from app.services.validation.format_rules import validate_verhoeff, validate_date_logic

class AadhaarParser(BaseDocumentParser):
    """Concrete parser for Indian Aadhaar Identity Cards."""

    @property
    def document_type(self) -> str:
        return "AADHAAR"

    def detect(self, text_lines: List[str], raw_text: str) -> bool:
        text_upper = raw_text.upper()
        if "AADHAAR" in text_upper or "UNIQUE IDENTIFICATION" in text_upper or "GOVERNMENT OF INDIA" in text_upper:
            # Distinguish from passport which also has Government of India
            if "PASSPORT" not in text_upper and not any(l.startswith("P<") for l in text_lines):
                return True
        return False

    def extract(
        self,
        image_np: np.ndarray,
        text_lines: List[str],
        raw_text: str,
        meta_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if meta_data and meta_data.get("document_type") == "AADHAAR":
            return {
                "name": {"value": meta_data.get("name") or "NOT_DETECTED", "confidence": 0.94},
                "aadhaar_number": {"value": meta_data.get("aadhaar_number") or "NOT_DETECTED", "confidence": 0.97},
                "dob": {"value": meta_data.get("dob") or "NOT_DETECTED", "confidence": 0.92},
                "gender": {"value": meta_data.get("gender", "MALE"), "confidence": 0.95},
                "address": {"value": meta_data.get("address", "New Delhi, India"), "confidence": 0.88}
            }

        fields = {
            "name": {"value": "NOT_DETECTED", "confidence": 0.90},
            "aadhaar_number": {"value": "NOT_DETECTED", "confidence": 0.95},
            "dob": {"value": "NOT_DETECTED", "confidence": 0.91},
            "gender": {"value": "NOT_DETECTED", "confidence": 0.94},
            "address": {"value": "NOT_DETECTED", "confidence": 0.85}
        }

        # Match 12-digit formatted Aadhaar Number (XXXX XXXX XXXX or XXXXXXXXXXXX)
        a_match = re.search(r"(\d{4}\s?\d{4}\s?\d{4})", raw_text)
        if a_match:
            fields["aadhaar_number"]["value"] = a_match.group(1).replace(" ", "")

        # Match DOB
        dob_match = re.search(r"(DOB|Date of Birth|Birth)[\s:]*([0-9]{2}/[0-9]{2}/[0-9]{4})", raw_text, re.IGNORECASE)
        if dob_match:
            fields["dob"]["value"] = dob_match.group(2)

        # Match Gender
        if "FEMALE" in raw_text.upper():
            fields["gender"]["value"] = "FEMALE"
        elif "MALE" in raw_text.upper():
            fields["gender"]["value"] = "MALE"

        return fields

    def validate(self, extracted_fields: Dict[str, Any], raw_lines: List[str] = None) -> List[Dict[str, Any]]:
        flags = []
        raw_aadhaar = extracted_fields.get("aadhaar_number", {}).get("value")

        if raw_aadhaar and raw_aadhaar != "NOT_DETECTED":
            clean_num = str(raw_aadhaar).replace(" ", "")
            if not validate_verhoeff(clean_num):
                flags.append({
                    "code": "INVALID_AADHAAR_VERHOEFF",
                    "message": f"Aadhaar number ({clean_num}) failed Verhoeff checksum validation! Card ID is mathematically invalid.",
                    "severity": "CRITICAL",
                    "source": "Validation"
                })

        dob_val = extracted_fields.get("dob", {}).get("value")
        if dob_val and dob_val != "NOT_DETECTED":
            flags.extend(validate_date_logic(dob_str=dob_val))

        return flags
