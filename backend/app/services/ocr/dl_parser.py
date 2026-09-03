import re
from typing import Dict, Any, List
import numpy as np
from app.services.ocr.base_parser import BaseDocumentParser
from app.services.validation.format_rules import validate_dl_number, validate_date_logic

class DrivingLicenceParser(BaseDocumentParser):
    """Concrete parser for Indian Driving Licences."""

    @property
    def document_type(self) -> str:
        return "DRIVING_LICENCE"

    def detect(self, text_lines: List[str], raw_text: str) -> bool:
        text_upper = raw_text.upper()
        if "DRIVING LICENCE" in text_upper or "UNION OF INDIA" in text_upper or "LICENCE NO" in text_upper or "MOTOR VEHICLES" in text_upper:
            return True
        for line in text_lines:
            if re.search(r"^[A-Z]{2}[0-9\-]{10,16}", line.strip()):
                return True
        return False

    def extract(
        self,
        image_np: np.ndarray,
        text_lines: List[str],
        raw_text: str,
        meta_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if meta_data and meta_data.get("document_type") == "DRIVING_LICENCE":
            return {
                "name": {"value": meta_data.get("name") or "NOT_DETECTED", "confidence": 0.94},
                "dl_number": {"value": meta_data.get("dl_number") or "NOT_DETECTED", "confidence": 0.96},
                "dob": {"value": meta_data.get("dob") or "NOT_DETECTED", "confidence": 0.92},
                "issue_date": {"value": meta_data.get("issue_date") or "NOT_DETECTED", "confidence": 0.90},
                "expiry_date": {"value": meta_data.get("expiry_date") or "NOT_DETECTED", "confidence": 0.90}
            }

        fields = {
            "name": {"value": "NOT_DETECTED", "confidence": 0.90},
            "dl_number": {"value": "NOT_DETECTED", "confidence": 0.95},
            "dob": {"value": "NOT_DETECTED", "confidence": 0.91},
            "issue_date": {"value": "NOT_DETECTED", "confidence": 0.88},
            "expiry_date": {"value": "NOT_DETECTED", "confidence": 0.88}
        }

        # DL Number format: State code (e.g. DL, MH, KA, HR) + RTO + year + 7 digits
        dl_match = re.search(r"([A-Z]{2}[0-9]{13}|[A-Z]{2}-[0-9]{13}|[A-Z]{2}\s?[0-9]{2}\s?[0-9]{11})", raw_text)
        if dl_match:
            fields["dl_number"]["value"] = dl_match.group(1).replace(" ", "").replace("-", "")

        # DOB match
        dob_match = re.search(r"(DOB|Date of Birth)[\s:]*([0-9]{2}/[0-9]{2}/[0-9]{4})", raw_text, re.IGNORECASE)
        if dob_match:
            fields["dob"]["value"] = dob_match.group(2)

        # Expiry Date match
        exp_match = re.search(r"(Validity|Valid Till|Expiry)[\s:]*([0-9]{2}/[0-9]{2}/[0-9]{4})", raw_text, re.IGNORECASE)
        if exp_match:
            fields["expiry_date"]["value"] = exp_match.group(2)

        return fields

    def validate(self, extracted_fields: Dict[str, Any], raw_lines: List[str] = None) -> List[Dict[str, Any]]:
        flags = []
        dl_num = extracted_fields.get("dl_number", {}).get("value")

        if dl_num and dl_num != "NOT_DETECTED":
            if not validate_dl_number(dl_num):
                flags.append({
                    "code": "INVALID_DL_FORMAT",
                    "message": f"Driving Licence number ({dl_num}) does not conform to Indian Sarathi RTO standards.",
                    "severity": "WARNING",
                    "source": "Validation"
                })

        dob_val = extracted_fields.get("dob", {}).get("value")
        issue_val = extracted_fields.get("issue_date", {}).get("value")
        exp_val = extracted_fields.get("expiry_date", {}).get("value")

        flags.extend(validate_date_logic(
            dob_str=dob_val if dob_val != "NOT_DETECTED" else None,
            issue_str=issue_val if issue_val != "NOT_DETECTED" else None,
            expiry_str=exp_val if exp_val != "NOT_DETECTED" else None
        ))

        return flags
