from PIL import Image, ExifTags  # type: ignore
from typing import Tuple, List, Dict, Any

class EXIFAnalyzer:
    """
    Parses EXIF image metadata to check for software manipulation traces and camera provenance.
    Missing EXIF is treated as a weak signal rather than definitive proof of tampering.
    """

    SUSPICIOUS_SOFTWARE = ["photoshop", "gimp", "canva", "pixlr", "paint.net", "adobe", "editor", "snapseed", "lightroom"]

    def analyze(self, image_path: str) -> Tuple[float, float, List[str], Dict[str, Any]]:
        """
        Returns: (exif_score, confidence, flags, metadata)
        """
        exif_flags = []
        score = 0.0
        confidence = 0.65
        metadata = {}

        try:
            pil_img = Image.open(image_path)
            exif_data = pil_img._getexif()

            if not exif_data:
                exif_flags.append("Limited metadata available (Normal for scanned documents or direct camera capture).")
                score = 0.0
                confidence = 0.60
                metadata["exif_present"] = False
                return 0.0, confidence, exif_flags, metadata

            exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items() if k in ExifTags.TAGS}
            metadata["exif_present"] = True

            # Check Software Tag
            software = str(exif.get("Software", "")).lower()
            metadata["software_tag"] = exif.get("Software", "None")

            for s in self.SUSPICIOUS_SOFTWARE:
                if s in software:
                    exif_flags.append(f"Potential manipulation indicator: Editing software signature detected in EXIF: '{exif.get('Software')}'.")
                    score += 50.0
                    confidence = 0.90
                    break

            # Check Camera Make / Model
            make = exif.get("Make")
            model = exif.get("Model")
            metadata["camera_make"] = make
            metadata["camera_model"] = model
            if not make and not model:
                metadata["hardware_info"] = "Not specified"


            # Check DateTimeOriginal
            dto = exif.get("DateTimeOriginal")
            metadata["date_time_original"] = dto

        except Exception as e:
            exif_flags.append("EXIF metadata inspection could not be completed.")
            score += 5.0
            confidence = 0.40

        return round(min(100.0, score), 2), confidence, exif_flags, metadata
