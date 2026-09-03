from mrz.checker.td3 import TD3CodeChecker  # type: ignore
from mrz.checker.td1 import TD1CodeChecker  # type: ignore
from mrz.checker.td2 import TD2CodeChecker  # type: ignore
from app.services.validation.format_rules import parse_date

def parse_and_validate_mrz(mrz_lines: list[str]) -> dict:
    """
    Parses MRZ lines using python 'mrz' library for ICAO 9303 format (TD3 passports, TD1/TD2 cards).
    Returns dict containing parsed fields, checksum status, and validation flags.
    """
    result = {
        "valid_mrz": False,
        "mrz_type": None,
        "surname": "",
        "given_names": "",
        "passport_number": "",
        "nationality": "",
        "dob": "",
        "expiry_date": "",
        "gender": "",
        "checksum_valid": False,
        "flags": []
    }

    if not mrz_lines or len(mrz_lines) < 2:
        return result

    # Clean lines
    clean_lines = [line.strip().replace(" ", "").upper() for line in mrz_lines if len(line.strip()) > 20]

    # Try TD3 (Passport - 2 lines of 44 chars)
    if len(clean_lines) >= 2:
        l1, l2 = clean_lines[0], clean_lines[1]
        if len(l1) >= 44 and len(l2) >= 44:
            td3_str = f"{l1[:44]}\n{l2[:44]}"
            try:
                checker = TD3CodeChecker(td3_str)
                fields = checker.fields()
                result["valid_mrz"] = True
                result["mrz_type"] = "TD3 (Passport)"
                result["surname"] = fields.surname
                result["given_names"] = fields.name
                result["passport_number"] = fields.document_number
                result["nationality"] = fields.nationality
                result["dob"] = fields.birth_date
                result["expiry_date"] = fields.expiry_date
                result["checksum_valid"] = bool(checker)

                if not result["checksum_valid"]:
                    warning_detail = f": {'; '.join(checker.report.warnings)}" if hasattr(checker, "report") and checker.report.warnings else ""
                    result["flags"].append({
                        "code": "MRZ_CHECKSUM_MISMATCH",
                        "title": "MRZ Checksum Failure",
                        "message": f"MRZ checksum verification failed (ICAO 9303 digit check invalid{warning_detail}). Possible forgery indicator.",
                        "severity": "HIGH",
                        "source": "Validation"
                    })
                return result
            except Exception as e:
                pass

    return result

def cross_check_mrz_vs_printed(mrz_data: dict, printed_fields: dict) -> list[dict]:
    """
    Cross-verifies MRZ extracted text vs printed document OCR text.
    Differences between MRZ and printed text are a strong indicator of photo/text tampering.
    """
    flags = []
    if not mrz_data.get("valid_mrz"):
        return flags

    # Check Passport Number Mismatch
    mrz_pass = mrz_data.get("passport_number", "").replace("<", "").strip()
    printed_pass = str(printed_fields.get("passport_number", "")).replace(" ", "").strip()
    if mrz_pass and printed_pass and mrz_pass != printed_pass:
        flags.append({
            "code": "PASSPORT_NUMBER_MISMATCH",
            "message": f"Passport number in MRZ ({mrz_pass}) does not match printed text ({printed_pass}).",
            "severity": "CRITICAL"
        })

    # Check Surname / Name Mismatch
    mrz_surname = mrz_data.get("surname", "").replace("<", "").strip()
    printed_name = str(printed_fields.get("name", "")).upper()
    if mrz_surname and printed_name and mrz_surname not in printed_name:
        flags.append({
            "code": "NAME_MRZ_MISMATCH",
            "message": f"Surname in MRZ ({mrz_surname}) is missing from printed name ({printed_name}).",
            "severity": "CRITICAL"
        })

    # Check DOB Mismatch
    mrz_dob = mrz_data.get("dob", "")
    printed_dob_raw = printed_fields.get("dob", "")
    if mrz_dob and printed_dob_raw:
        mrz_dob_parsed = parse_date(mrz_dob)
        printed_dob_parsed = parse_date(printed_dob_raw)
        if mrz_dob_parsed and printed_dob_parsed and mrz_dob_parsed.date() != printed_dob_parsed.date():
            flags.append({
                "code": "DOB_MRZ_MISMATCH",
                "message": f"Date of Birth in MRZ ({mrz_dob}) does not match printed DOB ({printed_dob_raw}).",
                "severity": "CRITICAL"
            })

    return flags
