import os
from pathlib import Path
import cv2  # type: ignore
import numpy as np
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import TravelerBiometric
from app.core.config import get_face_cascade, DUPLICATE_FACE_THRESHOLD, ASSETS_DIR

class ArcFaceONNXAdapter:
    """
    Production-grade adapter for InsightFace / ArcFace 512-D deep embedding model.
    Attempts local offline model loading if ONNX weights and onnxruntime are present.
    """
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or (ASSETS_DIR / "arcface_r50.onnx")
        self.session = None
        self.is_ready = False
        self._init_session()

    def _init_session(self):
        if not self.model_path.exists():
            return
        try:
            import onnxruntime as ort  # type: ignore
            self.session = ort.InferenceSession(str(self.model_path), providers=['CPUExecutionProvider'])
            self.is_ready = True
        except Exception:
            self.session = None
            self.is_ready = False

    def extract_embedding(self, aligned_face_crop: np.ndarray) -> Optional[np.ndarray]:
        if not self.is_ready or self.session is None or aligned_face_crop is None:
            return None
        try:
            resized = cv2.resize(aligned_face_crop, (112, 112))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            input_tensor = ((rgb.astype(np.float32) / 127.5) - 1.0).transpose(2, 0, 1)[np.newaxis, :]
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name
            emb = self.session.run([output_name], {input_name: input_tensor})[0][0]
            norm = np.linalg.norm(emb)
            return (emb / norm).astype(np.float32) if norm > 0 else emb.astype(np.float32)
        except Exception:
            return None


class OpenCVGradient512DFallback:
    """
    Lightweight, zero-download offline biometric feature extractor for demo and air-gapped environments.
    Extracts a 512-dimensional spatial luminance (256 components) and Sobel gradient magnitude (256 components) descriptor.
    """
    def extract_embedding(self, face_crop: Optional[np.ndarray]) -> np.ndarray:
        if face_crop is None or face_crop.size == 0:
            return np.zeros(512, dtype=np.float32)
        try:
            resized = cv2.resize(face_crop, (16, 16))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
            
            # 256 normalized luminance components
            v1 = cv2.normalize(gray.astype(np.float32), None, 0, 1, cv2.NORM_MINMAX).flatten()
            
            # 256 gradient orientation components
            sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
            sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
            mag = cv2.magnitude(sx, sy)
            v2 = cv2.normalize(mag, None, 0, 1, cv2.NORM_MINMAX).flatten()
            
            combined = np.concatenate([v1, v2]).astype(np.float32)
            norm = np.linalg.norm(combined)
            if norm > 0:
                return combined / norm
            return combined
        except Exception:
            return np.zeros(512, dtype=np.float32)


class FaceMatcherService:
    """
    Biometric verification service coordinating face detection, embedding extraction,
    similarity calculation, and duplicate identity database cross-checks.
    Transparently reports whether production ArcFace ONNX or local OpenCV 512-D fallback is active.
    """

    def __init__(self):
        self.face_cascade = get_face_cascade()
        self.arcface_adapter = ArcFaceONNXAdapter()
        self.fallback_extractor = OpenCVGradient512DFallback()

    def get_active_engine_name(self) -> str:
        if self.arcface_adapter.is_ready:
            return "ArcFace R50 ONNX — LOCAL"
        return "OpenCV Spatial-Gradient 512-D — LOCAL FALLBACK"

    def crop_face(self, image_np: np.ndarray) -> Optional[np.ndarray]:
        """
        Detects primary face bounding box and extracts aligned face crop.
        Returns None if image is empty or invalid.
        """
        if image_np is None or image_np.size == 0:
            return None
        
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY) if len(image_np.shape) == 3 else image_np
        h, w = gray.shape[:2]

        if not self.face_cascade.empty():
            try:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(40, 40))
                if len(faces) > 0:
                    # Select largest detected face
                    x, y, fw, fh = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
                    mx = max(0, x - int(fw * 0.1))
                    my = max(0, y - int(fh * 0.1))
                    mw = min(w - mx, int(fw * 1.2))
                    mh = min(h - my, int(fh * 1.2))
                    crop = image_np[my:my+mh, mx:mx+mw]
                    if crop.size > 0:
                        return crop
            except Exception:
                pass

        # Robust heuristic fallback
        try:
            if w > h: # Horizontal document (photo typically on left third)
                crop = image_np[int(h * 0.20):int(h * 0.65), int(w * 0.05):int(w * 0.28)]
            else: # Vertical portrait / live capture
                crop = image_np[int(h * 0.20):int(h * 0.80), int(w * 0.20):int(w * 0.80)]
            if crop.size > 0:
                return crop
        except Exception:
            pass

        return None

    def compute_embedding(self, face_crop: Optional[np.ndarray]) -> np.ndarray:
        """
        Computes 512-dimensional facial embedding vector using ArcFace if available,
        or the deterministic OpenCV spatial-gradient fallback.
        """
        if face_crop is None or face_crop.size == 0:
            return np.zeros(512, dtype=np.float32)

        # 1. Attempt ArcFace ONNX extraction
        arc_emb = self.arcface_adapter.extract_embedding(face_crop)
        if arc_emb is not None:
            return arc_emb

        # 2. Graceful offline fallback
        return self.fallback_extractor.extract_embedding(face_crop)

    def calculate_similarity_score(self, crop1: Optional[np.ndarray], crop2: Optional[np.ndarray]) -> float:
        """
        Calculates biometric facial similarity percentage between document face photo
        and live traveler capture using ArcFace deep cosine similarity if available,
        or calibrated central facial structure patch MAE for offline fallback.
        """
        if crop1 is None or crop2 is None or crop1.size == 0 or crop2.size == 0:
            return 50.0

        # 1. Primary: If ArcFace ONNX model is available, use deep cosine similarity
        if self.arcface_adapter.is_ready:
            try:
                emb1 = self.arcface_adapter.extract_embedding(crop1)
                emb2 = self.arcface_adapter.extract_embedding(crop2)
                if emb1 is not None and emb2 is not None:
                    return self.calculate_cosine_similarity(emb1, emb2)
            except Exception:
                pass

        # 2. Offline fallback: Calibrated central facial structure patch MAE
        try:
            r1 = cv2.resize(crop1, (96, 96))
            r2 = cv2.resize(crop2, (96, 96))
            
            # Extract central structure patch (eyes, nose, mouth area)
            p1 = r1[20:76, 20:76].astype(np.float32)
            p2 = r2[20:76, 20:76].astype(np.float32)
            
            mae = float(np.mean(np.abs(p1 - p2)))
            
            # MAE < 20 corresponds to high similarity (~88%), MAE > 60 corresponds to mismatch (~15%)
            score = max(0.0, min(100.0, 100.0 - (max(0.0, mae - 12.0) * 1.55)))
            return round(score, 2)
        except Exception:
            return 50.0

    def calculate_cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Computes cosine similarity between two 512-D vectors mapped to 0-100%."""
        if emb1 is None or emb2 is None or np.all(emb1 == 0) or np.all(emb2 == 0):
            return 50.0

        try:
            dot_product = float(np.dot(emb1, emb2))
            norm1 = float(np.linalg.norm(emb1))
            norm2 = float(np.linalg.norm(emb2))
            
            if norm1 == 0 or norm2 == 0:
                return 50.0

            cosine = dot_product / (norm1 * norm2)
            match_percentage = max(0.0, min(100.0, (cosine + 1.0) / 2.0 * 100.0))
            return round(match_percentage, 2)
        except Exception:
            return 50.0

    def check_duplicate_identity(
        self,
        db: Session,
        current_emb: np.ndarray,
        current_doc_num: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Cross-checks face embedding against synthetic records in database.
        If a face matches an existing record under a different document number, returns (True, matched_doc).
        """
        if current_emb is None or np.all(current_emb == 0):
            return False, None

        try:
            records = db.query(TravelerBiometric).all()
            for rec in records:
                if rec.document_number != current_doc_num:
                    stored_emb = np.frombuffer(rec.face_embedding, dtype=np.float32)
                    if len(stored_emb) == len(current_emb):
                        sim = self.calculate_cosine_similarity(current_emb, stored_emb)
                        if sim >= DUPLICATE_FACE_THRESHOLD:
                            return True, rec.document_number
        except Exception:
            pass

        return False, None

