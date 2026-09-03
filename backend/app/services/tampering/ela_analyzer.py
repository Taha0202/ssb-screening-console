import io
import cv2  # type: ignore
import numpy as np
from PIL import Image, ImageChops, ImageEnhance  # type: ignore
from typing import Dict, Any, Tuple

class ELAAnalyzer:
    """
    Performs Error Level Analysis (ELA) using Pillow to detect JPEG re-compression
    and digital manipulation anomalies.
    """

    def analyze(self, image_np: np.ndarray, jpeg_quality: int = 90) -> Tuple[float, np.ndarray, float, list[str], Dict[str, Any]]:
        """
        1. Resaves input image in memory at specified JPEG quality (90%).
        2. Computes absolute difference between original and recompressed image.
        3. Amplifies pixel differences.
        4. Calculates mean ELA anomaly score (0-100) and returns colorized ELA heatmap.
        Returns: (ela_score, heatmap_colored, confidence, flags, metadata)
        """
        flags = []
        metadata = {}

        if image_np is None or image_np.size == 0:
            return 0.0, np.zeros((100, 100, 3), dtype=np.uint8), 0.5, ["No image data for ELA"], metadata

        # Convert OpenCV BGR to PIL RGB
        orig_pil = Image.fromarray(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))

        # Re-compress in memory
        buffer = io.BytesIO()
        orig_pil.save(buffer, "JPEG", quality=jpeg_quality)
        buffer.seek(0)
        recompressed_pil = Image.open(buffer)

        # Calculate absolute difference
        ela_pil = ImageChops.difference(orig_pil, recompressed_pil)

        # Extrema scaling & enhancement
        extrema = ela_pil.getextrema()
        max_diff = max([ex[1] for ex in extrema]) if extrema else 1
        scale = 255.0 / max(max_diff, 1)

        ela_enhanced = ImageEnhance.Brightness(ela_pil).enhance(scale * 0.7)
        ela_np = np.array(ela_enhanced)

        # Calculate mean ELA score
        gray_ela = cv2.cvtColor(ela_np, cv2.COLOR_RGB2GRAY)
        mean_diff = float(np.mean(gray_ela))
        std_diff = float(np.std(gray_ela))
        
        # Normalize score (0-100)
        ela_score = round(min(100.0, (mean_diff * 2.5) + (std_diff * 1.2)), 2)
        confidence = 0.75

        # Generate JET colorized heatmap
        heatmap_colored = cv2.applyColorMap(gray_ela, cv2.COLORMAP_JET)

        if ela_score > 35.0:
            flags.append(
                f"Potential manipulation indicator: Elevated ELA re-compression noise ({ela_score}/100) detected."
            )

        metadata = {
            "mean_pixel_difference": round(mean_diff, 2),
            "pixel_std_dev": round(std_diff, 2),
            "jpeg_recompression_quality": jpeg_quality,
            "max_difference_detected": max_diff
        }

        return ela_score, heatmap_colored, confidence, flags, metadata
