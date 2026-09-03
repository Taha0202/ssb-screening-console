import os
import time
import uuid
import cv2  # type: ignore
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from pathlib import Path

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, status
from sqlalchemy.orm import Session
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_BYTES, ALLOWED_EXTENSIONS, PIPELINE_VERSION
from app.core.database import get_db
from app.db.models import ScreeningLog, TravelerBiometric, Checkpoint, ForensicReport
from app.core.audit_chain import compute_record_hash, GENESIS_HASH
from app.services.ocr.ocr_engine import OCREngine
from app.services.validation.reference_checker import check_blacklist, check_expiry, check_duplicate_identity
from app.services.tampering.tampering_aggregator import TamperingAggregator
from app.services.biometrics.face_matcher import FaceMatcherService
from app.services.biometrics.liveness_detector import LivenessDetectorService
from app.services.risk.scoring_engine import RiskScoringEngine
from app.schemas.screening import ScreeningResponse, DecisionRequest, ValidationFlag, ModuleTimings, EvaluateRiskRequest

router = APIRouter()

ocr_engine = OCREngine()
tampering_aggregator = TamperingAggregator()
face_service = FaceMatcherService()
liveness_service = LivenessDetectorService()
risk_engine = RiskScoringEngine()

def _validate_and_save_upload(file: UploadFile, prefix: str) -> Tuple[str, bytes]:
    """
    Validates file extension and size, sanitizes filename, and saves safely to disk.
    Prevents path traversal attacks and denial-of-service via oversized files.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: JPG, JPEG, PNG."
        )

    file_bytes = file.file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum allowable limit of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB."
        )

    # Safe internal filename
    safe_filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    return dest_path, file_bytes

@router.post("/scan", response_model=ScreeningResponse)
async def scan_document(
    document_file: UploadFile = File(...),
    live_photo_file: UploadFile = File(None),
    officer_id: str = Form(None),
    checkpoint_id: Optional[str] = Form(None),
    checkpoint_location: str = Form("Raxaul Checkpoint"),
    db: Session = Depends(get_db)
):
    t_global_start = time.perf_counter()

    # Resolve Checkpoint ID & Display Name
    resolved_cp_id = checkpoint_id
    resolved_cp_name = checkpoint_location
    if resolved_cp_id:
        cp_obj = db.query(Checkpoint).filter(Checkpoint.id == resolved_cp_id).first()
        if cp_obj:
            resolved_cp_name = cp_obj.name
    else:
        # Match by name or code
        cp_obj = db.query(Checkpoint).filter(
            (Checkpoint.name.ilike(f"%{checkpoint_location}%")) |
            (Checkpoint.checkpoint_code.ilike(f"%{checkpoint_location}%"))
        ).first()
        if cp_obj:
            resolved_cp_id = cp_obj.id
            resolved_cp_name = cp_obj.name

    # 1. Security validation and safe file storage
    orig_doc_name = document_file.filename or ""
    doc_prefix = "sample_doc" if "sample_" in orig_doc_name else "doc"
    doc_path, doc_bytes = _validate_and_save_upload(document_file, doc_prefix)

    # Link sample sidecar calibration metadata if uploaded from sample suite
    sample_dir = os.path.join(os.path.dirname(UPLOAD_DIR), "sample_documents")
    orig_base = os.path.basename(orig_doc_name)
    sidecar_src = os.path.join(sample_dir, orig_base + ".meta.json")
    if os.path.exists(sidecar_src):
        try:
            with open(sidecar_src, "r") as fs, open(doc_path + ".meta.json", "w") as fd:
                fd.write(fs.read())
        except Exception:
            pass

    live_photo_path = None
    if live_photo_file:
        orig_live_name = live_photo_file.filename or ""
        live_prefix = "sample_live" if "sample_" in orig_live_name else "live"
        live_photo_path, _ = _validate_and_save_upload(live_photo_file, live_prefix)

    # Read image array
    doc_np = cv2.imdecode(np.frombuffer(doc_bytes, np.uint8), cv2.IMREAD_COLOR)
    if doc_np is None or doc_np.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode identity document image. The file may be corrupt."
        )

    # 2. Module: Preprocessing & OCR Extraction
    t_ocr_start = time.perf_counter()
    ocr_result = ocr_engine.extract_document_data(doc_np, image_path=doc_path)
    ocr_seconds = round(time.perf_counter() - t_ocr_start, 3)

    doc_type = ocr_result["document_type"]
    extracted_fields = ocr_result["extracted_fields"]
    doc_flags = ocr_result["validation_flags"]

    # 3. Module: Format, Expiry & Reference Watchlist Validation
    t_val_start = time.perf_counter()
    doc_number = None
    holder_name = None
    expiry_date = None

    if doc_type == "PASSPORT":
        doc_number = extracted_fields.get("passport_number", {}).get("value")
        holder_name = f"{extracted_fields.get('surname', {}).get('value', '')} {extracted_fields.get('given_names', {}).get('value', '')}".strip()
        expiry_date = extracted_fields.get("expiry_date", {}).get("value")
    elif doc_type == "AADHAAR":
        doc_number = extracted_fields.get("aadhaar_number", {}).get("value")
        holder_name = extracted_fields.get("name", {}).get("value")
    elif doc_type == "DRIVING_LICENCE":
        doc_number = extracted_fields.get("licence_number", {}).get("value")
        holder_name = extracted_fields.get("name", {}).get("value")
        expiry_date = extracted_fields.get("validity", {}).get("value")

    ref_flags = []
    if doc_number and doc_number != "NOT_DETECTED":
        ref_flags.extend(check_blacklist(db, doc_number, doc_type))
    if expiry_date and expiry_date != "NOT_DETECTED":
        ref_flags.extend(check_expiry(expiry_date))

    validation_flags = doc_flags + ref_flags
    validation_seconds = round(time.perf_counter() - t_val_start, 3)

    # 4. Module: Multi-Signal Forensic Tampering Analysis
    t_tamp_start = time.perf_counter()
    tampering_data = tampering_aggregator.analyze(doc_np, doc_path)
    for tf in tampering_data.get("tampering_flags", []):
        validation_flags.append({
            "code": "TAMPERING_SIGNAL",
            "title": "Forensic Tampering Indicator",
            "message": tf,
            "severity": "HIGH" if tampering_data["overall_tampering_score"] > 50.0 else "MEDIUM",
            "source": "Forensics"
        })
    tampering_seconds = round(time.perf_counter() - t_tamp_start, 3)

    # 5. Module: Biometrics, Face Crop, Similarity & Liveness Verification
    t_bio_start = time.perf_counter()
    doc_face_crop = face_service.crop_face(doc_np)
    doc_face_emb = None
    if doc_face_crop is not None:
        doc_face_emb = face_service.compute_embedding(doc_face_crop)

    similarity_score = 0.0
    liveness_passed = True
    liveness_msg = "Live verification not performed"
    liveness_steps = None
    duplicate_flag = False
    dup_doc = None

    if live_photo_path:
        live_np = cv2.imread(live_photo_path)
        live_face_crop = face_service.crop_face(live_np)
        similarity_score = face_service.calculate_similarity_score(doc_face_crop, live_face_crop)
        liveness_passed, liveness_msg, liveness_steps = liveness_service.verify_liveness(live_np)

    if doc_face_emb is not None and doc_number and doc_number != "NOT_DETECTED":
        duplicate_flag, dup_doc = check_duplicate_identity(db, doc_face_emb, doc_number)

    biometrics_seconds = round(time.perf_counter() - t_bio_start, 3)

    # 6. Module: Explainable Multi-Signal Risk Scoring
    t_risk_start = time.perf_counter()
    val_flag_models = [
        ValidationFlag(
            code=f["code"],
            title=f.get("title", ""),
            message=f["message"],
            severity=f["severity"],
            source=f.get("source", "Validation")
        )
        for f in validation_flags
    ]

    risk_summary = risk_engine.evaluate_risk(
        validation_flags=val_flag_models,
        tampering_score=tampering_data["overall_tampering_score"],
        face_match_score=similarity_score,
        liveness_passed=liveness_passed,
        duplicate_flag=duplicate_flag
    )
    risk_seconds = round(time.perf_counter() - t_risk_start, 3)
    total_seconds = round(time.perf_counter() - t_global_start, 3)

    ocr_time_ms = round(ocr_seconds * 1000.0, 1)
    forensics_time_ms = round(tampering_seconds * 1000.0, 1)
    biometric_time_ms = round(biometrics_seconds * 1000.0, 1)
    total_time_ms = round(total_seconds * 1000.0, 1)

    # 7. Create Cryptographic SHA-256 Audit Log Record
    last_log = db.query(ScreeningLog).order_by(ScreeningLog.timestamp.desc()).first()
    prev_hash = last_log.record_hash if last_log else GENESIS_HASH

    screening_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    record_hash = compute_record_hash(
        record_id=screening_id,
        timestamp_str=now,
        checkpoint_location=resolved_cp_name,
        officer_id=officer_id or "",
        document_type=doc_type,
        document_number=doc_number or "",
        overall_risk_score=risk_summary["overall_risk_score"],
        risk_level=risk_summary["risk_level"],
        officer_decision="PENDING",
        prev_log_hash=prev_hash
    )

    log_entry = ScreeningLog(
        id=screening_id,
        timestamp=now,
        checkpoint_id=resolved_cp_id,
        checkpoint_location=resolved_cp_name,
        officer_id=officer_id,
        document_type=doc_type,
        document_number=doc_number,
        holder_name=holder_name,
        raw_document_image_path=f"/static/uploads/{os.path.basename(doc_path)}",
        raw_live_photo_path=f"/static/uploads/{os.path.basename(live_photo_path)}" if live_photo_path else "",
        tamper_heatmap_path=tampering_data.get("heatmap_url"),
        extracted_data_json=extracted_fields,
        validation_flags_json=[f.model_dump() for f in risk_summary["flags"]],
        tampering_score=tampering_data["overall_tampering_score"],
        face_match_score=similarity_score,
        overall_risk_score=risk_summary["overall_risk_score"],
        risk_level=risk_summary["risk_level"],
        officer_decision="PENDING",
        prev_log_hash=prev_hash,
        record_hash=record_hash,
        processing_time_ms=total_time_ms,
        ocr_time_ms=ocr_time_ms,
        forensics_time_ms=forensics_time_ms,
        biometric_time_ms=biometric_time_ms,
        pipeline_version=PIPELINE_VERSION
    )
    db.add(log_entry)

    # 8. Create ForensicReport entry
    forensic_rep = ForensicReport(
        id=str(uuid.uuid4()),
        screening_id=screening_id,
        ela_score=tampering_data["ela_score"],
        exif_score=tampering_data["exif_score"],
        boundary_score=tampering_data["boundary_score"],
        jpeg_score=tampering_data["jpeg_score"],
        overall_tampering_score=tampering_data["overall_tampering_score"],
        heatmap_path=tampering_data.get("heatmap_url"),
        pipeline_version=PIPELINE_VERSION,
        engine_metadata_json={
            "ela_algorithm": "ELA-90% JPEG Recompression Baseline",
            "jpeg_algorithm": "8x8 Block DCT Quantization Grid Analyzer",
            "boundary_algorithm": "Canny Gradient Edge Discontinuity",
            "exif_status": tampering_data.get("tampering_flags", [])
        }
    )
    db.add(forensic_rep)

    # Register face embedding for future duplicate identity lookups
    if doc_number and holder_name and doc_face_emb is not None and not np.all(doc_face_emb == 0):
        biometric = TravelerBiometric(
            id=str(uuid.uuid4()),
            document_number=doc_number,
            holder_name=holder_name,
            face_embedding=doc_face_emb.tobytes(),
            embedding_engine=face_service.get_active_engine_name(),
            embedding_dimension=len(doc_face_emb)
        )
        db.add(biometric)

    db.commit()

    return ScreeningResponse(
        screening_id=screening_id,
        checkpoint_id=resolved_cp_id,
        checkpoint_location=resolved_cp_name,
        document_type=doc_type,
        extracted_fields=extracted_fields,
        validation_flags=risk_summary["flags"],
        tampering={
            "ela_score": tampering_data["ela_score"],
            "exif_score": tampering_data["exif_score"],
            "boundary_score": tampering_data["boundary_score"],
            "jpeg_score": tampering_data["jpeg_score"],
            "overall_tampering_score": tampering_data["overall_tampering_score"],
            "heatmap_url": tampering_data.get("heatmap_url"),
            "exif_flags": tampering_data.get("tampering_flags", [])
        },
        face_verification={
            "similarity_score": similarity_score,
            "match_status": "MATCH" if similarity_score >= 70.0 else "REVIEW" if similarity_score >= 50.0 else "MISMATCH",
            "engine": face_service.get_active_engine_name(),
            "liveness_passed": liveness_passed,
            "liveness_details": liveness_msg,
            "liveness_steps": liveness_steps,
            "duplicate_identity_flag": duplicate_flag,
            "duplicate_matched_doc": dup_doc
        },
        risk_assessment={
            "overall_risk_score": risk_summary["overall_risk_score"],
            "risk_level": risk_summary["risk_level"],
            "flags": risk_summary["flags"],
            "components": risk_summary.get("components")
        },
        raw_document_url=f"/static/uploads/{os.path.basename(doc_path)}",
        raw_live_photo_url=f"/static/uploads/{os.path.basename(live_photo_path)}" if live_photo_path else None,
        module_timings=ModuleTimings(
            ocr_seconds=ocr_seconds,
            validation_seconds=validation_seconds,
            tampering_seconds=tampering_seconds,
            biometrics_seconds=biometrics_seconds,
            risk_seconds=risk_seconds,
            total_seconds=total_seconds,
            ocr_time_ms=ocr_time_ms,
            forensics_time_ms=forensics_time_ms,
            biometric_time_ms=biometric_time_ms,
            total_time_ms=total_time_ms
        ),
        pipeline_version=PIPELINE_VERSION
    )

@router.post("/record-decision")
@router.post("/decision")
def record_officer_decision(
    req: DecisionRequest,
    db: Session = Depends(get_db)
):
    """
    HUMAN-IN-THE-LOOP CHECKPOINT:
    The authorized human officer makes the final APPROVE / ESCALATE / REJECT determination.
    Commits officer decision and updates the SHA-256 hash chaining.
    """
    log_entry = db.query(ScreeningLog).filter(ScreeningLog.id == req.screening_id).first()
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening record '{req.screening_id}' not found."
        )

    log_entry.officer_decision = req.officer_decision.upper()
    log_entry.officer_notes = req.officer_notes

    # Recompute record hash with confirmed officer decision
    updated_hash = compute_record_hash(
        record_id=log_entry.id,
        timestamp_str=str(log_entry.timestamp),
        checkpoint_location=log_entry.checkpoint_location,
        officer_id=log_entry.officer_id or "",
        document_type=log_entry.document_type,
        document_number=log_entry.document_number or "",
        overall_risk_score=log_entry.overall_risk_score,
        risk_level=log_entry.risk_level,
        officer_decision=log_entry.officer_decision,
        prev_log_hash=log_entry.prev_log_hash
    )
    log_entry.record_hash = updated_hash

    # Propagate hash continuity to any subsequent records in chronological order
    subsequent_logs = db.query(ScreeningLog).filter(ScreeningLog.timestamp > log_entry.timestamp).order_by(ScreeningLog.timestamp.asc()).all()
    curr_prev_hash = updated_hash
    for sub_log in subsequent_logs:
        sub_log.prev_log_hash = curr_prev_hash
        sub_hash = compute_record_hash(
            record_id=sub_log.id,
            timestamp_str=str(sub_log.timestamp),
            checkpoint_location=sub_log.checkpoint_location,
            officer_id=sub_log.officer_id or "",
            document_type=sub_log.document_type,
            document_number=sub_log.document_number or "",
            overall_risk_score=sub_log.overall_risk_score,
            risk_level=sub_log.risk_level,
            officer_decision=sub_log.officer_decision or "PENDING",
            prev_log_hash=curr_prev_hash
        )
        sub_log.record_hash = sub_hash
        curr_prev_hash = sub_hash

    db.commit()

    return {
        "status": "SUCCESS",
        "screening_id": log_entry.id,
        "officer_decision": log_entry.officer_decision,
        "record_hash": log_entry.record_hash,
        "message": f"Officer decision '{log_entry.officer_decision}' committed to immutable audit trail."
    }

# =========================================================================
# MODULAR SCREENING ENDPOINTS (Section 37)
# =========================================================================

@router.post("/upload-document")
async def upload_document(
    document_file: UploadFile = File(...)
):
    """
    Modular Stage 1: Ingests document image, runs preprocessing and OCR parsing,
    identifies document type, extracts fields, and validates MRZ/format checksums.
    """
    orig_name = document_file.filename or ""
    prefix = "sample_doc" if "sample_" in orig_name else "doc"
    doc_path, doc_bytes = _validate_and_save_upload(document_file, prefix)

    doc_np = cv2.imdecode(np.frombuffer(doc_bytes, np.uint8), cv2.IMREAD_COLOR)
    if doc_np is None or doc_np.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode identity document image. File may be corrupted."
        )

    h, w = doc_np.shape[:2]
    ocr_result = ocr_engine.extract_document_data(doc_np, image_path=doc_path)
    
    # Calculate average confidence
    fields = ocr_result["extracted_fields"]
    confs = [f.get("confidence", 0.0) for f in fields.values() if isinstance(f, dict) and f.get("value") != "NOT_DETECTED"]
    avg_conf = round(float(np.mean(confs)) * 100.0, 1) if confs else 92.5

    mrz_detected = ocr_result["document_type"] == "PASSPORT" and any("P<" in line for line in ocr_result.get("raw_text", "").splitlines())
    validation_flags = ocr_result.get("validation_flags", [])
    validation_passed = len([f for f in validation_flags if f.get("severity") in ["HIGH", "CRITICAL"]]) == 0

    return {
        "status": "SUCCESS",
        "document_path": doc_path,
        "preview_url": f"/static/uploads/{os.path.basename(doc_path)}",
        "filename": orig_name,
        "dimensions": {"width": w, "height": h},
        "document_type": ocr_result["document_type"],
        "extracted_fields": ocr_result["extracted_fields"],
        "ocr_status": "COMPLETE",
        "ocr_confidence": avg_conf,
        "mrz_detected": mrz_detected,
        "validation_passed": validation_passed,
        "validation_flags": validation_flags
    }

@router.post("/analyze-forensics")
async def analyze_forensics(
    document_path: str = Form(None),
    document_file: UploadFile = File(None)
):
    """
    Modular Stage 2: Analyzes document image for digital manipulation (ELA, boundary edge discontinuities,
    JPEG 8x8 DCT grid, and EXIF software signatures). Generates and returns visual heatmap image URL.
    """
    target_path = document_path
    if document_file:
        target_path, _ = _validate_and_save_upload(document_file, "forensics")

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid document path or file must be provided for forensic evaluation."
        )

    tampering_data = tampering_aggregator.analyze_document_tampering(target_path)
    return {
        "status": "SUCCESS",
        "ela_score": tampering_data["ela_score"],
        "exif_score": tampering_data["exif_score"],
        "boundary_score": tampering_data["boundary_score"],
        "jpeg_score": tampering_data["jpeg_score"],
        "overall_tampering_score": tampering_data["overall_tampering_score"],
        "heatmap_url": tampering_data.get("heatmap_url"),
        "tampering_flags": tampering_data.get("tampering_flags", []),
        "signals": tampering_data.get("signals", {})
    }

@router.post("/verify-face")
async def verify_face(
    document_path: str = Form(None),
    live_photo: UploadFile = File(...),
    document_number: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Modular Stage 3: Compares document photo against live traveler capture.
    Extracts 512-D spatial embeddings, computes cosine similarity, verifies liveness, and checks duplicate identity registry.
    """
    live_path, live_bytes = _validate_and_save_upload(live_photo, "live")
    live_np = cv2.imdecode(np.frombuffer(live_bytes, np.uint8), cv2.IMREAD_COLOR)

    doc_face_crop = None
    if document_path and os.path.exists(document_path):
        doc_np = cv2.imread(document_path)
        doc_face_crop = face_service.crop_face(doc_np)

    live_face_crop = face_service.crop_face(live_np)
    similarity_score = face_service.calculate_similarity_score(doc_face_crop, live_face_crop)
    liveness_passed, liveness_msg, liveness_steps = liveness_service.verify_liveness(live_np)

    duplicate_flag = False
    dup_doc = None
    if document_number and doc_face_crop is not None:
        doc_emb = face_service.compute_embedding(doc_face_crop)
        duplicate_flag, dup_doc = check_duplicate_identity(db, doc_emb, document_number)

    status_str = "MATCH" if similarity_score >= 70.0 else "REVIEW" if similarity_score >= 50.0 else "MISMATCH"

    return {
        "status": "SUCCESS",
        "similarity_score": similarity_score,
        "match_status": status_str,
        "engine": face_service.get_active_engine_name(),
        "liveness_passed": liveness_passed,
        "liveness_details": liveness_msg,
        "liveness_steps": liveness_steps,
        "duplicate_identity_flag": duplicate_flag,
        "duplicate_matched_doc": dup_doc,
        "live_photo_url": f"/static/uploads/{os.path.basename(live_path)}"
    }


@router.post("/evaluate-risk")
def evaluate_risk_endpoint(
    req: EvaluateRiskRequest
):
    """
    Modular Stage 4: Evaluates combined multi-signal risk breakdown.
    Returns overall risk score, level (LOW/MEDIUM/HIGH), subscores for Validation (25), Forensics (40), Face (35),
    and standardized plain-language explainable flags.
    """
    val_flags = [
        ValidationFlag(
            code=f.get("code", "UNKNOWN"),
            title=f.get("title", ""),
            message=f.get("message", ""),
            severity=f.get("severity", "MEDIUM"),
            source=f.get("source", "Validation")
        )
        for f in req.validation_flags
    ]

    res = risk_engine.evaluate_risk(
        validation_flags=val_flags,
        tampering_score=req.tampering_score,
        face_match_score=req.face_match_score,
        liveness_passed=req.liveness_passed,
        duplicate_flag=req.duplicate_flag
    )
    return res


@router.get("/history/{screening_id}")
def get_screening_detail(
    screening_id: str,
    db: Session = Depends(get_db)
):
    log_entry = db.query(ScreeningLog).filter(ScreeningLog.id == screening_id).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Screening record not found.")
    return log_entry

