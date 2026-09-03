import re
from typing import Dict, Any, List
import numpy as np
from app.services.ocr.base_parser import BaseDocumentParser
from app.services.validation.format_rules import validate_voter_id_number, validate_date_logic

class VoterIDParser(BaseDocumentParser):
    """
    Concrete parser for Indian Voter Identity Cards (Electors Photo Identity Card - EPIC).
    EPIC Format: 3 Alphabetic characters followed by 7 numeric digits (e.g. ABC1234567, WBF1092834).
    """

    @property
    def document_type(self) -> str:
        return "VOTER_ID"

    def detect(self, text_lines: List[str], raw_text: str) -> bool:
        text_upper = raw_text.upper()
        if (
            "ELECTION COMMISSION OF INDIA" in text_upper
            or "ELECTOR PHOTO IDENTITY CARD" in text_upper
            or "ELECTOR'S PHOTO IDENTITY CARD" in text_upper
            or "EPIC NO" in text_upper
            or "VOTER ID" in text_upper
            or "BHARAT NIRVACHAN AAYOG" in text_upper
        ):
            return True
        
        # Heuristic: Check for standard 3-alpha + 7-digit EPIC pattern
        if re.search(r"\b[A-Z]{3}[0-9]{7}\b", text_upper):
            if "PASSPORT" not in text_upper and "AADHAAR" not in text_upper and "DRIVING" not in text_upper:
                return True
                
        return False

    def extract(
        self,
        image_np: np.ndarray,
        text_lines: List[str],
        raw_text: str,
        meta_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if meta_data and meta_data.get("document_type") == "VOTER_ID":
            return {
                "name": {"value": meta_data.get("name") or "NOT_DETECTED", "confidence": 0.93},
                "voter_id_number": {"value": meta_data.get("voter_id_number") or meta_data.get("epic_number") or "NOT_DETECTED", "confidence": 0.96},
                "father_husband_name": {"value": meta_data.get("father_name") or "NOT_DETECTED", "confidence": 0.90},
                "dob": {"value": meta_data.get("dob") or "NOT_DETECTED", "confidence": 0.91},
                "gender": {"value": meta_data.get("gender", "MALE"), "confidence": 0.95},
                "assembly_constituency": {"value": meta_data.get("constituency", "NOT_DETECTED"), "confidence": 0.88}
            }

        fields = {
            "name": {"value": "NOT_DETECTED", "confidence": 0.90},
            "voter_id_number": {"value": "NOT_DETECTED", "confidence": 0.95},
            "father_husband_name": {"value": "NOT_DETECTED", "confidence": 0.88},
            "dob": {"value": "NOT_DETECTED", "confidence": 0.90},
            "gender": {"value": "NOT_DETECTED", "confidence": 0.92},
            "assembly_constituency": {"value": "NOT_DETECTED", "confidence": 0.85}
        }

        # 1. Extract EPIC / Voter ID Number (3 Letters + 7 Digits)
        epic_match = re.search(r"\b([A-Z]{3}[0-9]{7})\b", raw_text.upper())
        if not epic_match:
            # Tolerant pattern with space/hyphen e.g. ABC-1234567 or ABC 1234567
            epic_match = re.search(r"\b([A-Z]{3}[\s\-][0-9]{7})\b", raw_text.upper())
            
        if epic_match:
            fields["voter_id_number"]["value"] = re.sub(r"[\s\-]", "", epic_match.group(1))

        # 2. Extract Elector Name
        name_match = re.search(r"(?:Elector's Name|Elector Name|Name)[\s:]*([A-Za-z\s]+)", raw_text, re.IGNORECASE)
        if name_match:
            cand = name_match.group(1).split("\n")[0].strip()
            if len(cand) > 2 and "FATHER" not in cand.upper() and "ELECTION" not in cand.upper():
                fields["name"]["value"] = cand.title()

        # 3. Extract Father's / Husband's Name
        father_match = re.search(r"(?:Father's Name|Husband's Name|Father/Husband Name)[\s:]*([A-Za-z\s]+)", raw_text, re.IGNORECASE)
        if father_match:
            cand_f = father_match.group(1).split("\n")[0].strip()
            if len(cand_f) > 2:
                fields["father_husband_name"]["value"] = cand_f.title()

        # 4. Extract DOB / Age
        dob_match = re.search(r"(?:DOB|Date of Birth|Birth)[\s:]*([0-9]{2}[/\-][0-9]{2}[/\-][0-9]{4})", raw_text, re.IGNORECASE)
        if dob_match:
            fields["dob"]["value"] = dob_match.group(1)

        # 5. Extract Gender
        if "FEMALE" in raw_text.upper():
            fields["gender"]["value"] = "FEMALE"
        elif "MALE" in raw_text.upper():
            fields["gender"]["value"] = "MALE"

        return fields

    def validate(self, extracted_fields: Dict[str, Any], raw_lines: List[str] = None) -> List[Dict[str, Any]]:
        flags = []
        raw_voter = extracted_fields.get("voter_id_number", {}).get("value")

        if raw_voter and raw_voter != "NOT_DETECTED":
            clean_num = str(raw_voter).replace(" ", "").replace("-", "")
            if not validate_voter_id_number(clean_num):
                flags.append({
                    "code": "INVALID_VOTER_ID_FORMAT",
                    "title": "Invalid Voter ID (EPIC) Format",
                    "message": f"Voter ID ({clean_num}) does not conform to standard 3-alpha + 7-numeric EPIC format.",
                    "severity": "CRITICAL",
                    "source": "Validation"
                })

        dob_val = extracted_fields.get("dob", {}).get("value")
        if dob_val and dob_val != "NOT_DETECTED":
            flags.extend(validate_date_logic(dob_str=dob_val))

        return flags
