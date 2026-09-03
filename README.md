# SSB Border Document Screening Console (SIH26188)
### Operational Identity Document Screening & Biometric Verification Workstation for Sashastra Seema Bal (SSB) Checkpoints

> [!IMPORTANT]
> **Prototype Notice:**  
> **This prototype is designed for offline/local demonstration and decision support. It is not an operational border-security deployment.**  
> All citizen names, identity numbers, facial images, and watchlist entries included in this repository are **100% synthetic demonstration reference data**.

---

## 1. Executive Summary

The **SSB Border Document Screening Console** is an automated, offline-capable, explainable identity screening workstation engineered specifically for **Sashastra Seema Bal (SSB)** personnel deployed along sensitive land border crossings (such as Raxaul, Raniganj, Panitanki, and eastern land transit posts).

The workstation ingests scanned or camera-captured identity documents (Passport, Aadhaar Card, Driving Licence) alongside a live traveler photograph, executes multi-signal forensic and biometric analysis in **under 10 seconds** (typically **0.15–0.40 seconds** on standard hardware), and presents an explainable risk assessment (**LOW**, **MEDIUM**, **HIGH**) accompanied by itemized plain-language reason codes.

### Core Architecture Principle: Human-in-the-Loop Authority
> **Operational Rule:** The system is an operational decision-support tool. It **NEVER autonomously approves, rejects, or detains a traveler**. The statutory authority remains solely with the on-duty SSB officer, who must review the explainable signals and commit an explicit **APPROVE**, **ESCALATE**, or **REJECT** determination into an immutable, SHA-256 hash-chained audit ledger.

---

## 2. Dual Deployment Modes & Quick Start

### MODE A — Standalone Offline Workstation (Default Demo Mode)
- **Database**: Embedded SQLite with WAL mode (`backend/data/sih_screening.db`)
- **AI Inference**: 100% Local / Offline (`OpenCV-SpatialGradient-512D` or local `ArcFaceONNXAdapter`)
- **Internet Requirement**: **ZERO** (completely air-gapped)
- **Startup**:
  - **macOS / Linux**:
    ```bash
    chmod +x start-dev.sh stop-dev.sh
    ./start-dev.sh
    ```
    To terminate cleanly: `./stop-dev.sh`.
  - **Windows**:
    ```bat
    start-dev.bat
    ```
    To terminate cleanly: `stop-dev.bat`.

  This launches FastAPI (`http://localhost:8000`) and React Vite (`http://localhost:5173`).

---

### MODE B — Enterprise Multi-Checkpoint Deployment (Docker Compose)
- **Database**: PostgreSQL with connection pooling (`DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/sih_screening`)
- **Architecture**: Multi-container stack orchestrated via Docker Compose:
  - `web`: Nginx reverse proxy serving the production React SPA bundle and proxying `/api/` & `/static/` to the backend.
  - `api`: Production FastAPI application with Alembic auto-migrations.
  - `db`: PostgreSQL 16 database with health checks and persistent volume storage.
- **Startup**:
  ```bash
  docker compose up --build -d
  ```
- **Access**:
  - Web Console: `http://localhost:3000` (or `http://localhost:80` if mapped to port 80)
  - Backend API: `http://localhost:8000`
  - Health Probe: `http://localhost:8000/api/v1/system/health`

---

## 3. Seed Accounts & Personas

| Role | Badge ID | Access Key | Checkpoint Location |
|---|---|---|---|
| **Border Officer** | `SSB-7741` | `officer123` | Raxaul Checkpoint Unit A (Indo-Nepal) |
| **Supervisor** | `SSB-1002` | `super123` | Raniganj Integrated Checkpost (Indo-Bangladesh) |
| **Senior Analyst** | `SSB-5099` | `analyst123` | Panitanki Land Port Unit |
| **Commandant (Admin)** | `SSB-0001` | `admin123` | SSB HQ Command Center |

*(Quick demo persona buttons are available on the Login screen for 1-click credential filling).*

---

## 4. Five Calibrated Demonstration Benchmarks

The workstation includes 1-click calibrated scenario loaders under the collapsible **DEMO / TEST SCENARIOS** drawer on `/scan`:

| Scenario | Document File | Traveler Photo | Expected Risk | Core Analytical Explanation |
|---|---|---|---|---|
| **1. Genuine Passport** | `sample_passport_genuine.jpg` | `sample_traveler_match.jpg` | **LOW RISK** (< 30) | ICAO 9303 MRZ valid; 88%+ face similarity; clean watchlist check. |
| **2. Tampered Photo / MRZ** | `sample_passport_tampered.jpg` | `sample_traveler_match.jpg` | **HIGH RISK** (> 70) | Photo boundary discontinuity, ELA compression variance, MRZ check digit failure. |
| **3. Identity Face Mismatch** | `sample_passport_genuine.jpg` | `sample_traveler_mismatch.jpg` | **HIGH RISK** (> 70) | Biometric facial similarity < 20%; triggers `FACE_MISMATCH` flag. |
| **4. Blacklisted Document** | `sample_passport_blacklisted.jpg` | `sample_traveler_match.jpg` | **HIGH RISK** (88) | Document `Z9982341` flagged in local reference lookout circular DB. |
| **5. Tampered Aadhaar** | `sample_aadhaar_tampered.jpg` | `sample_traveler_match.jpg` | **CHECKSUM ERROR** | Mathematical Dihedral D5 Verhoeff checksum algorithm failure. |

---

## 5. System Architecture & Diagnostics

```
                    ┌──────────────────────────────────────────────────────────┐
                    │       SSB Border Workstation (React 18 + Vite)           │
                    │   01 SCAN  →  02 ANALYZE  →  03 REVIEW  →  04 DECIDE     │
                    │   AI INFERENCE MODE: LOCAL / OFFLINE (Zero Cloud Cost)   │
                    └────────────────────────────┬─────────────────────────────┘
                                                 │ Multipart Form-Data
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend Service (Python 3.10+)                           │
│                                                                                            │
│  1. OCR & Structured Parsing Engine (Tesseract / PaddleOCR / Local Regex Parsers)          │
│     ├─ PassportParser: ICAO 9303 TD3 MRZ Parsing & Composite Checksums                    │
│     ├─ AadhaarParser: 12-Digit Extraction & Mathematical Verhoeff D5 Checksum              │
│     └─ DrivingLicenceParser: State Code & Sarathi Format Logic                             │
│                                                                                            │
│  2. Multi-Signal Forensic Tampering Analysis                                               │
│     ├─ Error Level Analysis (ELA at 90% recompression baseline)                            │
│     ├─ Photo Boundary Edge Discontinuity (Canny Gradient Analysis)                         │
│     ├─ JPEG Artifact Analysis (8x8 Block DCT Quantization Grid Discontinuities)            │
│     ├─ EXIF Metadata Anomaly Detection (Editing signatures, timestamp anomalies)           │
│     └─ Generated Heatmap Image Overlay (/static/heatmaps/...)                              │
│                                                                                            │
│  3. Biometric Verification & Liveness Challenge Engine                                     │
│     ├─ Primary: ArcFaceONNXAdapter (InsightFace 512-D Cosine Similarity)                   │
│     ├─ Fallback: OpenCVGradient512DFallback (Offline Luminance + Sobel 512-D)              │
│     ├─ Engine Transparency: Explicitly reports active engine in API & UI                   │
│     └─ 4-Step Operator Liveness Flow (Look at Camera -> Turn -> Center -> Blink)           │
│                                                                                            │
│  4. Explainable Multi-Signal Risk Assessment                                               │
│     ├─ Component Breakdown: Validation (25%) | Forensics (40%) | Biometrics (35%)          │
│     ├─ Security Floor Overrides (Lookout circular matches, severe mismatches)              │
│     └─ Plain-Language Flag Catalog with Human-Readable Explanations                        │
│                                                                                            │
│  5. Security, PII Masking & Immutable SHA-256 Ledger                                       │
│     ├─ Server-side PII Masking: Passports (P*****67), Aadhaar (XXXX XXXX 9012)             │
│     ├─ CSV Audit Export: GET /api/v1/audit/export with Content-Disposition header          │
│     └─ Cryptographic Audit Chaining: SHA-256 record_hash and prev_log_hash linkage         │
└──────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ SQLAlchemy Engine Abstraction
                                               ▼
                         ┌────────────────────────────────────────────┐
                         │ Dual DB: SQLite (WAL) or PostgreSQL 16+    │
                         │ - checkpoints (Arbitrary border units)     │
                         │ - officers (Personnel & Checkpoint links)  │
                         │ - reference_documents (Watchlists)         │
                         │ - traveler_biometrics (512-D Embeddings)   │
                         │ - forensic_reports (Signal sub-telemetry)  │
                         │ - screening_logs (SHA-256 Hash Chain)      │
                         └────────────────────────────────────────────┘
```

---

## 6. Biometric Grounding & Fallback Architecture

The biometric subsystem enforces strict architectural honesty:
1. **`ArcFaceONNXAdapter`**: Loaded if `backend/app/core/assets/arcface_r50.onnx` and `onnxruntime` are available. Reports: `"ArcFace-InsightFace-512D (Production Mode)"`.
2. **`OpenCVGradient512DFallback`**: Zero-dependency local fallback utilizing 256 luminance + 256 Sobel spatial gradient magnitude features. Reports: `"OpenCV-SpatialGradient-512D (Offline Fallback)"`.
3. **Liveness Verification**: Supports 4-step operator prompt flow (`LOOK AT CAMERA`, `TURN HEAD`, `RETURN CENTER`, `BLINK`). When cameras are unavailable or denied in the browser, fallback photo upload is supported without interrupting the screening workflow.

---

## 7. Security, PII Masking & Audit Trail Integrity

### Server-Side PII Protection
In compliance with data privacy standards for border workstations:
- `GET /api/v1/audit/logs` returns `@computed_field def masked_document_number`.
  - Passport: `P1234567` → `P*****67`
  - Aadhaar: `1234 5678 9012` → `XXXX XXXX 9012`
  - Driving Licence: `DL-14-20200012345` → `DL-14****2345`
- Original unmasked values remain stored in the SQLite ledger to ensure deterministic SHA-256 record hash verification.
- Terminal stdout / logging sanitizes sensitive identification fields.

### Cryptographic Audit Verification
- **Endpoint**: `GET /api/v1/audit/verify-chain`
- **Output**: Returns `valid`, `is_valid`, `records_checked`, `total_records`, `verification_timestamp`, and `first_invalid_record`.
- Validates both individual `record_hash` integrity and sequential `prev_log_hash` parent linkage.

### CSV Audit Export
- **Endpoint**: `GET /api/v1/audit/export`
- **Headers**: `Content-Disposition: attachment; filename="ssb_audit_logs_<timestamp>.csv"`
- **Columns**: `timestamp`, `checkpoint`, `officer`, `document_type`, `masked_document_number`, `risk_score`, `risk_level`, `decision`, `major_flags`.

---

## 8. Automated Test Suite (54/54 Passing)

Execute the full backend test suite:
```powershell
cd backend
..\venv\Scripts\python -m pytest -v
```

### Verified Test Categories:
- `tests/test_checkpoints_and_officers.py`:
  - Multi-checkpoint creation, retrieval, and status filtering
  - Officer RBAC, authentication, and checkpoint assignment
  - System health endpoint diagnostic probing
  - Screening sub-telemetry latency verification
- `tests/test_audit_chain.py`:
  - Genesis block anchor verification
  - Multi-record unbroken hash chain verification
  - Tampered record content detection
  - Broken previous hash link detection
  - Deterministic hash consistency across multiple recalculations
  - Server-side PII masking helper functions
- `tests/test_api.py`:
  - CSV audit export headers, content, and masking
  - Upload file size (>10MB) and extension validation
  - Biometric engine reporting and liveness challenge pass-through
  - Screening upload, analyze, verify, evaluate, and record-decision workflows
- `tests/test_ocr.py`: Document classification, MRZ extraction, and fallback parsing.
- `tests/test_validation.py`: ICAO 9303 checksums, Aadhaar Verhoeff D5 mathematical checks, watchlist lookups.
- `tests/test_tampering.py`: Error Level Analysis (ELA), JPEG 8x8 DCT grid, boundary Canny gradients, heatmap generation.
- `tests/test_risk_engine.py`: Weighted 25/40/35 risk model, floor escalations, and plain-language flag catalogs.
- `tests/test_screening_system.py`: End-to-end integration pipeline tests (all 5 calibrated scenarios).

---

## 9. Frontend Production Build

Validate the frontend bundle:
```powershell
cd frontend
npm run build
```
Build output completes in **< 1 second** with zero compilation errors.

---

## 10. Operational Guidelines & Institutional Standards

1. **Human-in-the-Loop**: All automated scores are advisory. The interface highlights `SYSTEM ASSESSMENT` and explicitly prompts for `OFFICER DECISION REQUIRED`.
2. **Explainable Terminology**: The console uses non-prejudicial terminology:
   - *"Potential manipulation indicator"* instead of *"Forgery detected"*
   - *"Reference database match"* instead of *"Criminal detected"*
   - *"Face similarity below threshold"* instead of *"Fake person"*
   - *"Limited metadata available"* for scanned documents rather than declaring tampering.
3. **100% Offline Capability**: All OCR, forensic signal calculations, biometric comparisons, and audit chain operations run locally without external cloud network requests.

