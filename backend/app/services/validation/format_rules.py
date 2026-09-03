import re
from datetime import datetime

# Standard Verhoeff algorithm multiplication table based on dihedral group D5
_verhoeff_d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Permutation table
_verhoeff_p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

# Inverse table
_verhoeff_inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def compute_verhoeff_check_digit(base_number_str: str) -> str:
    """Computes the 12th Verhoeff checksum digit for an 11-digit base number."""
    clean_num = re.sub(r"\D", "", base_number_str)
    c = 0
    for i, item in enumerate(reversed(clean_num)):
        c = _verhoeff_d[c][_verhoeff_p[(i + 1) % 8][int(item)]]
    return str(_verhoeff_inv[c])

def validate_verhoeff(number_str: str) -> bool:
    """Validates 12-digit Aadhaar number using the mathematical Verhoeff algorithm."""
    clean_num = re.sub(r"\D", "", number_str)
    if len(clean_num) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(clean_num)):
        c = _verhoeff_d[c][_verhoeff_p[i % 8][int(item)]]
    return c == 0

def validate_passport_number(passport_num: str) -> bool:
    """Validates Indian Passport number (1 letter followed by 7 digits)."""
    if not passport_num:
        return False
    clean_p = passport_num.strip().upper()
    return bool(re.match(r"^[A-Z][0-9]{7}$", clean_p))

def validate_dl_number(dl_num: str) -> bool:
    """Validates Indian Driving Licence number format."""
    if not dl_num:
        return False
    clean_dl = re.sub(r"[\s\-]", "", dl_num.strip().upper())
    return bool(re.match(r"^[A-Z]{2}[0-9]{13}$", clean_dl)) or len(clean_dl) >= 12

def validate_voter_id_number(voter_id_num: str) -> bool:
    """Validates Indian Voter ID (EPIC) format (3 letters followed by 7 digits)."""
    if not voter_id_num:
        return False
    clean_voter = re.sub(r"[\s\-]", "", voter_id_num.strip().upper())
    return bool(re.match(r"^[A-Z]{3}[0-9]{7}$", clean_voter))

def parse_date(date_str: str) -> datetime | None:
    """Attempts to parse common date formats (YYYY-MM-DD, DD/MM/YYYY, YYMMDD)."""
    if not date_str or date_str == "NOT_DETECTED":
        return None
    clean_str = str(date_str).strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%y%m%d", "%d %b %Y", "%d%b%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            continue
    return None

def validate_date_logic(dob_str: str = None, issue_str: str = None, expiry_str: str = None) -> list:
    """Runs logical sanity checks on dates (expiry > issue, DOB implies plausible age)."""
    flags = []
    dob = parse_date(dob_str)
    issue = parse_date(issue_str)
    expiry = parse_date(expiry_str)

    if dob:
        today = datetime.now()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 0 or age > 120:
            flags.append({
                "code": "INVALID_AGE",
                "message": f"Extracted Date of Birth ({dob_str}) implies an implausible age ({age} years).",
                "severity": "HIGH",
                "source": "Validation"
            })

    if issue and expiry:
        if expiry <= issue:
            flags.append({
                "code": "EXPIRY_BEFORE_ISSUE",
                "message": f"Document Date of Expiry ({expiry_str}) is earlier than or equal to Date of Issue ({issue_str}).",
                "severity": "HIGH",
                "source": "Validation"
            })

    if expiry:
        if expiry < datetime.now():
            flags.append({
                "code": "DOCUMENT_EXPIRED",
                "message": f"Document expired on {expiry.strftime('%d-%b-%Y')}.",
                "severity": "MEDIUM",
                "source": "Validation"
            })

    return flags
