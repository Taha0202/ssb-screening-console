import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, JSON, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Checkpoint(Base):
    """
    Physical border checkpoint or transit control unit.
    Supports multi-checkpoint deployments along border frontiers.
    """
    __tablename__ = "checkpoints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    checkpoint_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    state = Column(String(50), nullable=False)
    district = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")  # 'ACTIVE', 'INACTIVE', 'MAINTENANCE'
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    officers = relationship("Officer", back_populates="checkpoint", foreign_keys="Officer.checkpoint_id")

class Officer(Base):
    """
    Authorized border security personnel (Officer, Supervisor, Analyst, Admin).
    """
    __tablename__ = "officers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    badge_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="OFFICER")  # 'OFFICER', 'SUPERVISOR', 'ANALYST', 'ADMIN'
    checkpoint_id = Column(String(36), ForeignKey("checkpoints.id"), nullable=True)
    checkpoint_location = Column(String(100), nullable=True)  # Preserved display string
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")  # 'ACTIVE', 'SUSPENDED', 'DECOMMISSIONED'
    created_at = Column(DateTime, default=utc_now)
    last_login = Column(DateTime, nullable=True)

    checkpoint = relationship("Checkpoint", back_populates="officers", foreign_keys=[checkpoint_id])

class DocumentType(Base):
    """
    Supported identity document classifications and parser versions.
    """
    __tablename__ = "document_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(30), unique=True, nullable=False, index=True)  # 'PASSPORT', 'AADHAAR', 'DRIVING_LICENSE', etc.
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    parser_version = Column(String(20), nullable=False, default="1.0.0")
    created_at = Column(DateTime, default=utc_now)

class ReferenceDocument(Base):
    """
    Scalable synthetic reference database for watchlists, lookout circulars,
    expired documents, and verified benchmark identities.
    """
    __tablename__ = "reference_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_type = Column(String(30), nullable=False, index=True)
    document_number = Column(String(50), nullable=False, index=True)
    holder_name = Column(String(100), nullable=True)
    date_of_birth = Column(String(30), nullable=True)
    issue_date = Column(String(30), nullable=True)
    expiry_date = Column(String(30), nullable=True)
    status = Column(String(30), nullable=False, default="BLACKLISTED", index=True)  # 'VALID', 'EXPIRED', 'BLACKLISTED', 'SUSPICIOUS', 'REVOKED'
    reason = Column(String(255), nullable=True)
    source_type = Column(String(50), nullable=False, default="SYNTHETIC_BENCHMARK")
    created_at = Column(DateTime, default=utc_now)

class BlacklistedDocument(Base):
    """
    Direct lookout watchlist entries (maintained for backward compatibility).
    """
    __tablename__ = "blacklisted_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_type = Column(String(30), nullable=False)
    document_number = Column(String(50), unique=True, nullable=False, index=True)
    holder_name = Column(String(100), nullable=True)
    reason = Column(String(255), nullable=False)
    flagged_at = Column(DateTime, default=utc_now)

class TravelerBiometric(Base):
    """
    Enrolled facial biometric embeddings for deduplication and impostor detection.
    """
    __tablename__ = "traveler_biometrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_number = Column(String(50), nullable=False, index=True)
    holder_name = Column(String(100), nullable=False)
    face_embedding = Column(LargeBinary, nullable=False)  # 512-dim float vector
    embedding_engine = Column(String(50), nullable=False, default="OpenCV-SpatialGradient-512D")
    embedding_dimension = Column(Integer, nullable=False, default=512)
    status = Column(String(20), nullable=False, default="ACTIVE")
    registered_at = Column(DateTime, default=utc_now)

class ScreeningLog(Base):
    """
    Append-only screening audit trail with cryptographic SHA-256 block hash chaining.
    """
    __tablename__ = "screening_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=utc_now, index=True)
    checkpoint_id = Column(String(50), nullable=True)
    checkpoint_location = Column(String(100), nullable=False)
    officer_id = Column(String(50), nullable=True)
    document_type = Column(String(30), nullable=False)
    document_number = Column(String(50), nullable=True, index=True)
    holder_name = Column(String(100), nullable=True)
    raw_document_image_path = Column(String(255), nullable=False)
    raw_live_photo_path = Column(String(255), nullable=False)
    tamper_heatmap_path = Column(String(255), nullable=True)
    extracted_data_json = Column(JSON, nullable=False)
    validation_flags_json = Column(JSON, nullable=False)
    tampering_score = Column(Float, nullable=False, default=0.0)
    face_match_score = Column(Float, nullable=False, default=0.0)
    overall_risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(10), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH'
    officer_decision = Column(String(20), nullable=True)  # 'APPROVE', 'REJECT', 'ESCALATE', 'PENDING'
    officer_notes = Column(Text, nullable=True)
    prev_log_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), nullable=False)

    # Telemetry and pipeline metadata
    processing_time_ms = Column(Float, nullable=True, default=0.0)
    ocr_time_ms = Column(Float, nullable=True, default=0.0)
    forensics_time_ms = Column(Float, nullable=True, default=0.0)
    biometric_time_ms = Column(Float, nullable=True, default=0.0)
    pipeline_version = Column(String(20), nullable=False, default="2.0.0")

    forensic_report = relationship("ForensicReport", back_populates="screening_log", uselist=False)

class ForensicReport(Base):
    """
    Detailed multi-signal forensic breakdown and metadata.
    """
    __tablename__ = "forensic_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    screening_id = Column(String(36), ForeignKey("screening_logs.id"), nullable=True, index=True)
    ela_score = Column(Float, nullable=False, default=0.0)
    exif_score = Column(Float, nullable=False, default=0.0)
    boundary_score = Column(Float, nullable=False, default=0.0)
    jpeg_score = Column(Float, nullable=False, default=0.0)
    overall_tampering_score = Column(Float, nullable=False, default=0.0)
    heatmap_path = Column(String(255), nullable=True)
    pipeline_version = Column(String(20), nullable=False, default="2.0.0")
    engine_metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    screening_log = relationship("ScreeningLog", back_populates="forensic_report", foreign_keys=[screening_id])
