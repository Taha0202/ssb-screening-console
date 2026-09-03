import os
import cv2  # type: ignore
import uuid
import numpy as np
from typing import Dict, Any
from app.core.config import HEATMAP_DIR
from app.services.tampering.ela_analyzer import ELAAnalyzer
from app.services.tampering.exif_analyzer import EXIFAnalyzer
from app.services.tampering.boundary_analyzer import PhotoBoundaryAnalyzer
from app.services.tampering.jpeg_analyzer import JPEGArtifactAnalyzer

class TamperingAggregator:
    """
    Multi-signal forensic analysis aggregator combining:
    1. Error Level Analysis (ELA) via Pillow
    2. EXIF Software & Provenance Analysis
    3. Photo Boundary Discontinuity & Splicing Analysis
    4. JPEG 8x8 Block Compression Artifact Analysis

    Returns individual signal scores, overall explainable score, and visual heatmap overlay.
    """

    def __init__(self):
        self.ela_analyzer = ELAAnalyzer()
        self.exif_analyzer = EXIFAnalyzer()
        self.boundary_analyzer = PhotoBoundaryAnalyzer()
        self.jpeg_analyzer = JPEGArtifactAnalyzer()

    def analyze(self, image_np: np.ndarray = None, image_path: str = "") -> Dict[str, Any]:
        if image_path:
            return self.analyze_document_tampering(image_path)
        elif image_np is not None:
            # Save temporary file or run directly
            return self.analyze_document_tampering_np(image_np)
        return self.analyze_document_tampering("")

    def analyze_document_tampering(self, image_path: str) -> Dict[str, Any]:
        image_np = cv2.imread(image_path)
        if image_np is None:
            return {
                "ela_score": 0.0,
                "exif_score": 0.0,
                "boundary_score": 0.0,
                "jpeg_score": 0.0,
                "overall_tampering_score": 0.0,
                "heatmap_url": None,
                "tampering_flags": ["Failed to load image for tampering evaluation."],
                "signals": {}
            }

        # 1. ELA Signal
        ela_score, ela_heatmap, ela_conf, ela_flags, ela_meta = self.ela_analyzer.analyze(image_np)

        # 2. EXIF Signal
        exif_score, exif_conf, exif_flags, exif_meta = self.exif_analyzer.analyze(image_path)

        # 3. Boundary Signal
        boundary_score, bbox, boundary_conf, boundary_flags, boundary_meta = self.boundary_analyzer.analyze(image_np)

        # 4. JPEG Grid Artifact Signal
        jpeg_result = self.jpeg_analyzer.analyze(image_np)
        jpeg_score = jpeg_result["jpeg_score"]
        jpeg_flags = jpeg_result["flags"]

        # Aggregate plain-language flags
        all_flags = []
        all_flags.extend(exif_flags)
        all_flags.extend(boundary_flags)
        all_flags.extend(jpeg_flags)
        all_flags.extend(ela_flags)

        # Weighted Tampering Score:
        # Boundary: 35%, ELA: 35%, JPEG: 15%, EXIF: 15%
        overall_score = round(
            (boundary_score * 0.35) +
            (ela_score * 0.35) +
            (jpeg_score * 0.15) +
            (exif_score * 0.15),
            2
        )
        overall_score = min(100.0, max(0.0, overall_score))

        # Render Visual Heatmap + Bounding Box Overlay
        annotated = cv2.addWeighted(image_np, 0.65, ela_heatmap, 0.35, 0)
        x, y, w, h = bbox
        if w > 0 and h > 0:
            box_color = (0, 0, 255) if overall_score > 35.0 else (0, 220, 100)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), box_color, 2)
            cv2.putText(
                annotated,
                f"Photo Boundary (Score: {boundary_score})",
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                box_color,
                2
            )

        # Save Heatmap file
        heatmap_filename = f"heatmap_{uuid.uuid4().hex[:12]}.jpg"
        heatmap_file_path = os.path.join(HEATMAP_DIR, heatmap_filename)
        cv2.imwrite(heatmap_file_path, annotated)

        return {
            "ela_score": ela_score,
            "exif_score": exif_score,
            "boundary_score": boundary_score,
            "jpeg_score": jpeg_score,
            "overall_tampering_score": overall_score,
            "heatmap_url": f"/static/heatmaps/{heatmap_filename}",
            "tampering_flags": all_flags,
            "signals": {
                "ela": {"score": ela_score, "confidence": ela_conf, "metadata": ela_meta},
                "exif": {"score": exif_score, "confidence": exif_conf, "metadata": exif_meta},
                "boundary": {"score": boundary_score, "confidence": boundary_conf, "metadata": boundary_meta},
                "jpeg": {"score": jpeg_score, "confidence": jpeg_result["confidence"], "metadata": jpeg_result["metadata"]}
            }
        }
