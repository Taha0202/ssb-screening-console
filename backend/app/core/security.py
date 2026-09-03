import hashlib
import re
from typing import Optional, Any

def get_password_hash(password: str) -> str:
    """Generates SHA-256 salted password hash."""
    salt = "ssb_sih2026_salt_"
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored hash."""
    if plain_password == hashed_password:
        return True
    return get_password_hash(plain_password) == hashed_password

def mask_document_number(document_number: Optional[str], document_type: Optional[str] = None) -> str:
    """
    Deterministically masks sensitive government document identifiers for display and audit export.
    Preserves document type conventions:
    - Passport (e.g. P1234567 -> P*****67)
    - Aadhaar (e.g. 1234 5678 9012 -> XXXX XXXX 9012)
    - Driving Licence (e.g. DL-14-20200012345 -> DL-14****2345)
    - Generic/Fallback: Keep first 2 and last 2 characters, masking middle.
    """
    if not document_number or document_number.strip() in ("", "NOT_DETECTED", "None", "—"):
        return "—"
    
    raw = document_number.strip()
    clean = re.sub(r'[\s\-]', '', raw).upper()
    doc_type = (document_type or "").upper()
    
    # 1. Aadhaar (12 digits)
    if doc_type == "AADHAAR" or (len(clean) == 12 and clean.isdigit()):
        last4 = clean[-4:]
        return f"XXXX XXXX {last4}"
    
    # 2. Driving Licence (e.g., DL1420200012345 or DL-14-...)
    if doc_type in ("DRIVING_LICENCE", "DL") or raw.startswith("DL") or (len(clean) >= 10 and clean[:2].isalpha()):
        state_code = clean[:2]
        if len(clean) >= 6:
            rto_code = clean[2:4] if clean[2:4].isdigit() else ""
            last4 = clean[-4:]
            if rto_code:
                return f"{state_code}-{rto_code}****{last4}"
            return f"{state_code}****{last4}"
        return f"{clean[:2]}****{clean[-2:]}"
    
    # 3. Passport (1 letter + 7 digits, e.g. P1234567 -> P*****67)
    if doc_type == "PASSPORT" or (len(clean) == 8 and clean[0].isalpha() and clean[1:].isdigit()):
        first_char = clean[0]
        last2 = clean[-2:]
        return f"{first_char}*****{last2}"

    # 4. Voter ID (EPIC: 3 letters + 7 digits, e.g. ABC1234567 -> ABC****567)
    if doc_type in ("VOTER_ID", "EPIC") or (len(clean) == 10 and clean[:3].isalpha() and clean[3:].isdigit()):
        prefix = clean[:3]
        suffix = clean[-3:]
        return f"{prefix}****{suffix}"
    
    # 5. Standard Fallback for other identifiers
    if len(clean) > 4:
        return f"{clean[:2]}****{clean[-2:]}"
    elif len(clean) > 2:
        return f"{clean[0]}**{clean[-1]}"
    return "****"

def mask_name(name: Optional[str]) -> str:
    """Masks traveler full name for privacy-safe presentation (e.g. Rajesh Kumar -> R***** K****)."""
    if not name or name.strip() in ("", "NOT_DETECTED", "None", "—"):
        return "—"
    parts = name.strip().split()
    masked_parts = []
    for p in parts:
        if len(p) <= 2:
            masked_parts.append(p[0] + "*")
        else:
            masked_parts.append(p[0] + "*" * (len(p) - 1))
    return " ".join(masked_parts)

def sanitize_for_log(data: Any) -> str:
    """Sanitizes text strings or dictionaries to prevent accidental leaking of raw PII in console logs."""
    text = str(data)
    # Mask 12 digit Aadhaar pattern
    text = re.sub(r'\b\d{4}\s?\d{4}\s?(\d{4})\b', r'XXXX-XXXX-\1', text)
    # Mask Passport pattern (1 letter + 7 digits)
    text = re.sub(r'\b([A-Z])\d{5}(\d{2})\b', r'\1*****\2', text)
    return text

