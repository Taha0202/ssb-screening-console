import os
import sys
import json
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_documents")

def test_endpoint(name, method, url, **kwargs):
    try:
        res = requests.request(method, url, **kwargs)
        status = "PASSED" if res.status_code in [200, 201] else "FAILED"
        print(f"[{status}] {name} ({res.status_code}) -> {url}")
        return res
    except Exception as e:
        print(f"[FAILED] {name} -> Error: {e}")
        return None

def main():
    print("==================================================")
    print("SIH26188 LIVE ENDPOINT & INFERENCE VERIFICATION")
    print("==================================================")

    # 1. System Health
    res = test_endpoint("System Health", "GET", f"{BASE_URL}/system/health")
    if res and res.status_code == 200:
        d = res.json()
        print(f"   -> AI Inference Mode: {d.get('ai_inference_mode')}")
        print(f"   -> Database: {d.get('database')} ({d.get('database_type')})")
        print(f"   -> Active Checkpoints: {d.get('active_checkpoints_count')}")
        print(f"   -> Reference Watchlist Count: {d.get('reference_records_count')}")
        print(f"   -> Face Biometric Engine: {d.get('face_engine_name')}")

    # 2. System Status (Modular probe)
    test_endpoint("System Status Probe", "GET", f"{BASE_URL}/system/status")

    # 3. Authentication (All 4 Personnel Roles)
    roles_creds = [
        ("Officer (Inspector)", "SSB-7741", "officer123", "OFFICER"),
        ("Supervisor (Asst. Cmdt)", "SSB-1002", "super123", "SUPERVISOR"),
        ("Senior Analyst", "SSB-5099", "analyst123", "ANALYST"),
        ("Commandant (Admin)", "SSB-0001", "admin123", "ADMIN")
    ]
    for r_label, b_id, pwd, exp_role in roles_creds:
        login_res = test_endpoint(f"Login {r_label}", "POST", f"{BASE_URL}/auth/login", json={
            "badge_id": b_id,
            "password": pwd
        })
        if login_res and login_res.status_code == 200:
            u = login_res.json().get("user", {})
            print(f"   -> {u.get('full_name')} ({u.get('role')}) assigned to {u.get('checkpoint_location')}")

    # 4. Checkpoints Listing
    test_endpoint("List Checkpoints", "GET", f"{BASE_URL}/checkpoints")

    # 5. Officers Listing
    test_endpoint("List Officers", "GET", f"{BASE_URL}/officers")

    # 6. Test Calibrated Demo Scenarios
    scenarios = [
        ("Scenario 1: Genuine Passport", "sample_passport_genuine.jpg", "sample_traveler_match.jpg", "LOW"),
        ("Scenario 2: Tampered Photo", "sample_passport_tampered.jpg", "sample_traveler_match.jpg", "HIGH"),
        ("Scenario 3: Face Mismatch", "sample_passport_genuine.jpg", "sample_traveler_mismatch.jpg", "HIGH"),
        ("Scenario 4: Blacklisted Document", "sample_passport_blacklisted.jpg", "sample_traveler_match.jpg", "HIGH"),
        ("Scenario 5: Tampered Aadhaar", "sample_aadhaar_tampered.jpg", "sample_traveler_match.jpg", "HIGH")
    ]

    last_screening_id = None
    for s_name, doc_file, live_file, expected_risk in scenarios:
        doc_p = os.path.join(SAMPLE_DIR, doc_file)
        live_p = os.path.join(SAMPLE_DIR, live_file)
        with open(doc_p, "rb") as fd, open(live_p, "rb") as fl:
            scan_res = requests.post(
                f"{BASE_URL}/screening/scan",
                files={
                    "document_file": (doc_file, fd, "image/jpeg"),
                    "live_photo_file": (live_file, fl, "image/jpeg")
                },
                data={
                    "officer_id": "SSB-7741",
                    "checkpoint_location": "Raxaul Checkpoint Unit A"
                }
            )
            if scan_res.status_code == 200:
                s_data = scan_res.json()
                act_risk = s_data.get("risk_assessment", {}).get("risk_level")
                last_screening_id = s_data.get("screening_id")
                timings = s_data.get("module_timings", {})
                status_str = "MATCH" if act_risk == expected_risk else "MISMATCH"
                print(f"[PASSED] {s_name} -> Risk Level: {act_risk} (Expected: {expected_risk} [{status_str}]) | Total Latency: {timings.get('total_time_ms', 0)}ms (OCR: {timings.get('ocr_time_ms', 0)}ms, Forensics: {timings.get('forensics_time_ms', 0)}ms, Bio: {timings.get('biometric_time_ms', 0)}ms)")
            else:
                print(f"[FAILED] {s_name} -> HTTP {scan_res.status_code}: {scan_res.text}")

    # 7. Record Decision
    if last_screening_id:
        test_endpoint("Record Decision", "POST", f"{BASE_URL}/screening/record-decision", json={
            "screening_id": last_screening_id,
            "officer_decision": "APPROVE",
            "officer_notes": "Automated verification passed."
        })

    # 8. Audit Logs
    test_endpoint("Audit Logs", "GET", f"{BASE_URL}/audit/logs?limit=10")

    # 9. Audit Export CSV
    test_endpoint("Audit Export CSV", "GET", f"{BASE_URL}/audit/export")

    # 10. Audit Chain Verification
    chain_res = test_endpoint("Verify SHA-256 Audit Chain", "GET", f"{BASE_URL}/audit/verify-chain")
    if chain_res and chain_res.status_code == 200:
        c_data = chain_res.json()
        print(f"   -> Valid: {c_data.get('is_valid')} | Records Checked: {c_data.get('total_records')} | Message: {c_data.get('message')}")

    # 11. Error Handling & Edge Cases (Phase 8)
    print("\n--- Testing Error Handling & Security Constraints ---")
    
    # Invalid Login
    res_err_login = requests.post(f"{BASE_URL}/auth/login", json={"badge_id": "INVALID", "password": "wrong"})
    print(f"[{'PASSED' if res_err_login.status_code == 401 else 'FAILED'}] Invalid Credentials Rejection ({res_err_login.status_code}) -> Expected 401")

    # Unsupported Extension
    res_err_ext = requests.post(
        f"{BASE_URL}/screening/scan",
        files={"document_file": ("malicious.exe", b"MZDummyPayload", "application/octet-stream")},
        data={"officer_id": "SSB-7741"}
    )
    print(f"[{'PASSED' if res_err_ext.status_code == 400 else 'FAILED'}] Unsupported File Extension Rejection ({res_err_ext.status_code}) -> Expected 400")

    # Oversized File (>10MB)
    large_payload = b"0" * (11 * 1024 * 1024)
    res_err_size = requests.post(
        f"{BASE_URL}/screening/scan",
        files={"document_file": ("huge_image.jpg", large_payload, "image/jpeg")},
        data={"officer_id": "SSB-7741"}
    )
    print(f"[{'PASSED' if res_err_size.status_code == 413 else 'FAILED'}] Oversized File Rejection ({res_err_size.status_code}) -> Expected 413")

    # Corrupted / Un-decodable Image
    res_err_corrupt = requests.post(
        f"{BASE_URL}/screening/scan",
        files={"document_file": ("corrupt.jpg", b"NOT_A_VALID_IMAGE_BYTES_STREAM", "image/jpeg")},
        data={"officer_id": "SSB-7741"}
    )
    print(f"[{'PASSED' if res_err_corrupt.status_code == 400 else 'FAILED'}] Corrupted Image Decoding Rejection ({res_err_corrupt.status_code}) -> Expected 400")

    # Non-existent Audit Log
    res_err_log = requests.get(f"{BASE_URL}/audit/logs/non-existent-uuid-0000")
    print(f"[{'PASSED' if res_err_log.status_code == 404 else 'FAILED'}] Non-Existent Audit Record Handling ({res_err_log.status_code}) -> Expected 404")

    # Non-existent Checkpoint
    res_err_cp = requests.get(f"{BASE_URL}/checkpoints/CP-DOES-NOT-EXIST")
    print(f"[{'PASSED' if res_err_cp.status_code == 404 else 'FAILED'}] Non-Existent Checkpoint Handling ({res_err_cp.status_code}) -> Expected 404")

    # 12. Frontend Localhost
    test_endpoint("Frontend Vite Server", "GET", "http://localhost:5173")

    print("==================================================")
    print("LIVE VERIFICATION COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    main()

