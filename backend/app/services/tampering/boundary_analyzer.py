import cv2  # type: ignore
import numpy as np
from typing import Tuple, List, Dict, Any
from app.core.config import get_face_cascade

class PhotoBoundaryAnalyzer:
    """
    Analyzes document photo boundary region for edge discontinuities,
    high edge density variances, and color saturation tells indicative of photo replacement or splicing.
    """

    def __init__(self):
        self.face_cascade = get_face_cascade()

    def analyze(self, image_np: np.ndarray) -> Tuple[float, List[int], float, List[str], Dict[str, Any]]:
        """
        Returns: (boundary_score, bbox [x,y,w,h], confidence, flags, metadata)
        """
        flags = []
        boundary_score = 0.0
        confidence = 0.70
        metadata = {}

        if image_np is None or image_np.size == 0:
            return 0.0, [0, 0, 0, 0], 0.5, ["No image data for boundary analysis"], metadata

        h, w = image_np.shape[:2]
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY) if len(image_np.shape) == 3 else image_np

        faces = ()
        if not self.face_cascade.empty():
            try:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(40, 40))
            except Exception:
                faces = ()

        if len(faces) > 0:
            fx, fy, fw, fh = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
            px = max(0, fx - int(fw * 0.25))
            py = max(0, fy - int(fh * 0.25))
            pw = min(w - px, int(fw * 1.5))
            ph = min(h - py, int(fh * 1.5))
            doc_photo_box = [int(px), int(py), int(pw), int(ph)]
            confidence = 0.85
        else:
            # Check for rectangular portrait photograph contours
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            detected_box = None
            for cnt in contours:
                cx, cy, cw, ch = cv2.boundingRect(cnt)
                aspect = ch / float(cw) if cw > 0 else 0
                area = cw * ch
                # Expected passport photo size relative to document
                if 0.03 * (w * h) < area < 0.35 * (w * h) and 1.1 <= aspect <= 1.7:
                    detected_box = [int(cx), int(cy), int(cw), int(ch)]
                    confidence = 0.70
                    break
            
            if detected_box:
                doc_photo_box = detected_box
            else:
                flags.append("Photo region could not be confidently localized")
                metadata["photo_localized"] = False
                return 0.0, [0, 0, 0, 0], 0.40, flags, metadata


        px, py, pw, ph = doc_photo_box
        crop = gray[py:py+ph, px:px+pw]
        
        if crop.size > 0:
            edges = cv2.Canny(crop, 50, 150)
            
            top_edge = float(np.mean(edges[0:5, :])) if edges.shape[0] >= 5 else 0.0
            bottom_edge = float(np.mean(edges[-5:, :])) if edges.shape[0] >= 5 else 0.0
            left_edge = float(np.mean(edges[:, 0:5])) if edges.shape[1] >= 5 else 0.0
            right_edge = float(np.mean(edges[:, -5:])) if edges.shape[1] >= 5 else 0.0
            
            edge_variance = float(np.var([top_edge, bottom_edge, left_edge, right_edge]))
            max_edge = float(np.max([top_edge, bottom_edge, left_edge, right_edge]))

            # Check color saturation anomaly along perimeter (splicing border tell)
            color_crop = image_np[py:py+ph, px:px+pw]
            if len(color_crop.shape) == 3:
                b, g, r = cv2.split(color_crop)
                red_dom = np.mean(r[0:6, :] > (g[0:6, :] + 40)) + np.mean(r[-6:, :] > (g[-6:, :] + 40))
                if red_dom > 0.25:
                    boundary_score += 40.0

            if edge_variance > 500.0 or max_edge > 90.0:
                boundary_score += 55.0
                flags.append(
                    "Potential manipulation indicator: Photo boundary edge discontinuity / sharpness variance detected around photo frame."
                )
            else:
                boundary_score += 8.0

            metadata = {
                "detected_photo_bbox": doc_photo_box,
                "perimeter_edge_variance": round(edge_variance, 2),
                "max_perimeter_edge": round(max_edge, 2)
            }

        return round(min(100.0, boundary_score), 2), doc_photo_box, confidence, flags, metadata
