import os
import cv2  # type: ignore
import numpy as np
import pytest  # type: ignore
from app.services.tampering.ela_analyzer import ELAAnalyzer
from app.services.tampering.exif_analyzer import EXIFAnalyzer
from app.services.tampering.boundary_analyzer import PhotoBoundaryAnalyzer
from app.services.tampering.jpeg_analyzer import JPEGArtifactAnalyzer
from app.services.tampering.tampering_aggregator import TamperingAggregator
from app.core.config import HEATMAP_DIR

def test_ela_analysis():
    test_img = np.full((300, 400, 3), 220, dtype=np.uint8)
    cv2.putText(test_img, "TEST SIGNATURE", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    
    analyzer = ELAAnalyzer()
    score, heatmap, conf, flags, meta = analyzer.analyze(test_img)
    assert 0.0 <= score <= 100.0
    assert heatmap.shape == (300, 400, 3)
    assert conf > 0.5

def test_jpeg_artifact_analyzer():
    analyzer = JPEGArtifactAnalyzer()
    test_img = np.full((300, 400, 3), 200, dtype=np.uint8)
    result = analyzer.analyze(test_img)
    assert "jpeg_score" in result
    assert "confidence" in result
    assert "flags" in result

def test_photo_boundary_analyzer():
    analyzer = PhotoBoundaryAnalyzer()
    test_img = np.full((400, 600, 3), 230, dtype=np.uint8)
    # Draw photo box
    cv2.rectangle(test_img, (50, 100), (200, 300), (100, 100, 100), 2)
    
    score, bbox, conf, flags, meta = analyzer.analyze(test_img)
    assert 0.0 <= score <= 100.0
    assert len(bbox) == 4

def test_tampering_aggregator(tmp_path):
    # Save a temporary test image
    test_img_path = str(tmp_path / "test_doc.jpg")
    img = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.rectangle(img, (40, 100), (220, 320), (0, 0, 255), 3) # Spliced red boundary
    cv2.imwrite(test_img_path, img)

    aggregator = TamperingAggregator()
    res = aggregator.analyze_document_tampering(test_img_path)

    assert "overall_tampering_score" in res
    assert "heatmap_url" in res
    assert "signals" in res
    assert res["overall_tampering_score"] >= 0.0
