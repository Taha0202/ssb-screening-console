from abc import ABC, abstractmethod
from typing import Dict, Any, List
import numpy as np

class BaseDocumentParser(ABC):
    """
    Abstract interface for document type parsers (Passport, Aadhaar, Driving Licence).
    Screening pipeline relies on this contract rather than hardcoded document branches.
    """

    @property
    @abstractmethod
    def document_type(self) -> str:
        """Returns standard document identifier: PASSPORT, AADHAAR, DRIVING_LICENCE"""
        pass

    @abstractmethod
    def detect(self, text_lines: List[str], raw_text: str) -> bool:
        """Determines if the document text matches this parser's document signature."""
        pass

    @abstractmethod
    def extract(
        self,
        image_np: np.ndarray,
        text_lines: List[str],
        raw_text: str,
        meta_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extracts structured fields from preprocessed image and OCR text.
        If a field cannot be confidently extracted, sets its value to 'NOT_DETECTED'.
        """
        pass

    @abstractmethod
    def validate(self, extracted_fields: Dict[str, Any], raw_lines: List[str] = None) -> List[Dict[str, Any]]:
        """
        Executes document-specific checksum, layout, and logical validation rules.
        Returns list of structured validation flag dictionaries.
        """
        pass
