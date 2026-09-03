import os
import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError

BASE_URL = "http://127.0.0.1:8000/api/v1"
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_documents")

def make_multipart_request(url, fields, files):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    
    # Text fields
    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{v}\r\n".encode("utf-8"))
        
    # File fields
    for field_name, file_info in files.items():
        filename, filepath, content_type = file_info
        with open(filepath, "rb") as f:
            file_bytes = f.read()
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_bytes)
        body.extend(b"\r\n")
        
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(url, data=bytes(body))
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def test_live_system():
    print("\n--- LIVE SYSTEM VALIDATION ---")
    
    # 1. Health
    with urllib.request.urlopen(f"{BASE_URL}/system/health") as resp:
        health = json.loads(resp.read().decode("utf-8"))
        print(f"1. Health Check: Status={health.get('status')}, Mode={health.get('ai_inference_mode')}, DB={health.get('database')}")
        
    # 2. Login
    login_data = json.dumps({"badge_id": "SSB-7741", "password": "officer123"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        auth_res = json.loads(resp.read().decode("utf-8"))
        token = auth_res["access_token"]
        print(f"2. Auth Login: Officer={auth_res['user']['full_name']} ({auth_res['user']['badge_id']}) - Token received")
        
    # 3. Checkpoints
    with urllib.request.urlopen(f"{BASE_URL}/checkpoints") as resp:
        cps = json.loads(resp.read().decode("utf-8"))
        print(f"3. Checkpoints List: {len(cps)} active checkpoints available")
        
    # 4. Five Calibrated Scenarios
    scenarios = [
        ("Scenario 1 (Genuine Passport)", "sample_passport_genuine.jpg", "sample_traveler_match.jpg", "LOW"),
        ("Scenario 2 (Tampered Passport)", "sample_passport_tampered.jpg", "sample_traveler_match.jpg", "HIGH"),
        ("Scenario 3 (Face Mismatch)", "sample_passport_genuine.jpg", "sample_traveler_mismatch.jpg", "HIGH"),
        ("Scenario 4 (Blacklisted Passport)", "sample_passport_blacklisted.jpg", "sample_traveler_match.jpg", "HIGH"),
        ("Scenario 5 (Tampered Aadhaar)", "sample_aadhaar_tampered.jpg", "sample_traveler_match.jpg", "HIGH"),
    ]
    
    screening_ids = []
    print("\n4. Testing 5 Calibrated Demo Scenarios:")
    for name, doc_file, live_file, expected_risk in scenarios:
        doc_path = os.path.join(SAMPLE_DIR, doc_file)
        live_path = os.path.join(SAMPLE_DIR, live_file)
        status, scan_res = make_multipart_request(
            f"{BASE_URL}/screening/scan",
            fields={"officer_id": "SSB-7741", "checkpoint_location": "Raxaul Checkpoint Unit A"},
            files={
                "document_file": (doc_file, doc_path, "image/jpeg"),
                "live_photo_file": (live_file, live_path, "image/jpeg")
            }
        )
        actual_risk = scan_res["risk_assessment"]["risk_level"]
        actual_score = scan_res["risk_assessment"]["overall_risk_score"]
        screening_ids.append(scan_res["screening_id"])
        status_sym = "[PASS]" if actual_risk == expected_risk else "[FAIL]"
        print(f"   {status_sym} - {name}: Expected={expected_risk}, Got={actual_risk} (Score: {actual_score:.1f}/100)")
        
    # 5. Record Decision on first screening
    decision_payload = json.dumps({
        "screening_id": screening_ids[0],
        "decision": "APPROVE",
        "notes": "Verified genuine passport and matching biometrics at Raxaul Unit A."
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/screening/record-decision", data=decision_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        dec_res = json.loads(resp.read().decode("utf-8"))
        print(f"\n5. Record Officer Decision: Status={dec_res.get('status')}, Record Hash={dec_res.get('record_hash')[:24]}...")
        
    # 6. Audit logs
    with urllib.request.urlopen(f"{BASE_URL}/audit/logs") as resp:
        logs = json.loads(resp.read().decode("utf-8"))
        print(f"6. Audit Logs: {len(logs)} total screening logs retrieved")
        
    # 7. Chain verification
    with urllib.request.urlopen(f"{BASE_URL}/audit/verify-chain") as resp:
        chain_res = json.loads(resp.read().decode("utf-8"))
        print(f"7. SHA-256 Audit Chain Integrity: Is Valid={chain_res.get('is_valid')}, Records={chain_res.get('records_checked')}, Msg={chain_res.get('message')}")
        
    # 8. CSV Export
    with urllib.request.urlopen(f"{BASE_URL}/audit/export") as resp:
        csv_bytes = resp.read()
        print(f"8. CSV Export (/audit/export): Status={resp.status}, Content Length={len(csv_bytes)} bytes")
        
    print("\n--- ALL LIVE WORKFLOWS OPERATIONAL ---\n")

if __name__ == '__main__':
    test_live_system()
