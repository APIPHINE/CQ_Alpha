#!/usr/bin/env python3
"""
pdf_processor.py

A COMPLETE PDF processing module with:
- TOC extraction (with fallback to heuristic-based chapter detection)
- Text extraction (with OCR support for scanned PDFs)
- Advanced chapter heuristics (including Roman numeral detection, font size, keywords, uppercase ratio, etc.)
- Image processing & merging
- Logging & error handling
- Support for different PDF layouts (decorative, academic, structured)
- Final structured output for integration with other applications
"""

import os
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import pymupdf as fitz  # PyMuPDF
from PIL import Image
import numpy as np
import pytesseract  # OCR for scanned PDFs

# ---- Configuration ----
log_directory = "/Applications/Ptxt/logs"
output_directory = "/Applications/Ptxt/output"
log_file = os.path.join(log_directory, "pdf_processor.log")

# Ensure required directories exist
for directory in [log_directory, output_directory]:
    os.makedirs(directory, exist_ok=True)

# ---- Logging Setup ----
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---- Global Pattern for Roman Numerals ----
ROMAN_NUMERAL_PATTERN = re.compile(
    r"^(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))$",
    re.IGNORECASE
)

# ---- Custom Exceptions ----
class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass

# ---- Configuration DataClass ----
@dataclass
class ProcessingConfig:
    """Configuration for PDF processing."""
    dpi: int = 300
    ocr_enabled: bool = False  # Enable OCR for scanned PDFs
    min_heading_score: float = 1.5
    min_uppercase_ratio: float = 0.7
    min_alpha_length: int = 5
    block_width_threshold: float = 0.6
    chapter_keywords: List[str] = None

    def __post_init__(self):
        if self.chapter_keywords is None:
            self.chapter_keywords = [
                "CHAPTER", "Chapter",
                "SECTION", "Section",
                "BOOK", "Book",
                "PART", "Part",
                "Preface", "Contents",
                "APPENDIX", "Appendix"
            ]

# ---- Chapter DataClass ----
@dataclass
class Chapter:
    """Represents a detected chapter."""
    title: str
    page_range: range
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "title": self.title,
            "start_page": self.page_range.start,
            "end_page": self.page_range.stop - 1,
            "confidence": self.confidence,
            "metadata": self.metadata or {}
        }

# ---- Image Processing ----
def merge_page_images(image_list: List[Image.Image]) -> Optional[Image.Image]:
    """Merge multiple page images vertically."""
    try:
        if not image_list:
            raise PDFProcessingError("No images to merge")

        total_width = max(img.width for img in image_list)
        total_height = sum(img.height for img in image_list)

        merged_image = Image.new("RGB", (total_width, total_height), color=(255, 255, 255))
        current_y = 0
        for img in image_list:
            merged_image.paste(img, (0, current_y))
            current_y += img.height

        return merged_image

    except Exception as e:
        logger.error(f"Image merging failed: {e}")
        raise PDFProcessingError(f"Failed to merge images: {e}")

# ---- PDF Processor ----
class PDFProcessor:
    """Full-featured PDF processor with TOC extraction, heuristic-based chapter detection, and image processing."""

    def __init__(self, pdf_path: Union[str, Path], config: Optional[ProcessingConfig] = None):
        """Initialize with PDF path and optional configuration."""
        self.pdf_path = Path(pdf_path)
        self.config = config or ProcessingConfig()
        self.doc: Optional[fitz.Document] = None

        if not self.pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")

    def open_pdf(self) -> None:
        """Open the PDF document."""
        try:
            self.doc = fitz.open(str(self.pdf_path))
            logger.info(f"Opened PDF: {self.pdf_path}")
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            raise PDFProcessingError(f"Failed to open PDF: {e}")

    def get_total_pages(self) -> int:
        """Get total number of pages."""
        if not self.doc:
            raise PDFProcessingError("Document is not opened")
        return len(self.doc)

    def get_page_text(self, page_num: int) -> str:
        """Get text content from a specific page, using OCR if enabled and text is empty."""
        try:
            if not self.doc:
                raise PDFProcessingError("Document is not opened")
            page = self.doc[page_num]
            text = page.get_text()
            if not text and self.config.ocr_enabled:
                # Fallback to OCR if text extraction is empty
                img = self.convert_page_to_image(page_num)
                text = pytesseract.image_to_string(img)
                logger.info(f"OCR text extracted for page {page_num + 1}")
            return text
        except Exception as e:
            logger.error(f"Failed to get text from page {page_num}: {e}")
            raise PDFProcessingError(f"Failed to get page text: {e}")

    def convert_page_to_image(self, page_number: int, dpi: Optional[int] = None) -> Image.Image:
        """Convert a PDF page to an image."""
        try:
            if not self.doc:
                raise PDFProcessingError("Document is not opened")
            page = self.doc[page_number]
            zoom = (dpi or self.config.dpi) / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            logger.info(f"Converted page {page_number + 1} to image at {dpi or self.config.dpi} DPI")
            return img
        except Exception as e:
            logger.error(f"Page conversion failed: {e}")
            raise PDFProcessingError(f"Failed to convert page {page_number}: {e}")

    def extract_toc(self) -> List[Dict[str, Any]]:
        """Extract table of contents."""
        try:
            if not self.doc:
                raise PDFProcessingError("Document is not opened")
            toc = self.doc.get_toc()
            if not toc:
                logger.warning("No TOC found in PDF")
                return []
            chapters = []
            for i, (level, title, page) in enumerate(toc):
                end_page = (toc[i + 1][2] - 1) if (i + 1) < len(toc) else len(self.doc)
                chapters.append({
                    "title": title,
                    "start_page": page - 1,  # Convert to 0-based indexing
                    "end_page": end_page - 1,
                    "level": level,
                    "confidence": 1.0
                })
            return chapters
        except Exception as e:
            logger.error(f"TOC extraction failed: {e}")
            raise PDFProcessingError(f"Failed to extract TOC: {e}")

    def detect_chapters(self) -> List[Dict[str, Any]]:
        """Detect chapters using heuristics."""
        try:
            if not self.doc:
                raise PDFProcessingError("Document is not opened")
            candidates = self._get_chapter_candidates()
            if not candidates:
                logger.info("No chapter candidates found")
                return []
            chapters = []
            total_pages = len(self.doc)
            for i, candidate in enumerate(candidates):
                # Determine end page for chapter candidate
                if i < len(candidates) - 1:
                    end_page = candidates[i + 1]["page"] - 1
                else:
                    # Look ahead for keywords such as 'appendix' or 'references'
                    for j in range(candidate["page"], total_pages):
                        page_text = self.get_page_text(j).lower()
                        if "appendix" in page_text or "references" in page_text:
                            end_page = j - 1
                            break
                    else:
                        end_page = total_pages - 1
                chapters.append({
                    "title": candidate["text"],
                    "start_page": candidate["page"],
                    "end_page": end_page,
                    "confidence": candidate["score"] / 4.0,
                    "metadata": {
                        "bbox": candidate["bbox"],
                        "score": candidate["score"]
                    }
                })
            return chapters
        except Exception as e:
            logger.error(f"Chapter detection failed: {e}")
            raise PDFProcessingError(f"Failed to detect chapters: {e}")

    def _get_chapter_candidates(self) -> List[Dict[str, Any]]:
        """Get chapter candidates using heuristics based on text blocks."""
        try:
            candidates = []
            for page_num in range(len(self.doc)):
                page = self.doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" not in block:
                        continue
                    text = " ".join(
                        span["text"] for line in block["lines"]
                        for span in line["spans"]
                    ).strip()
                    if self._is_chapter_heading(text, block):
                        candidates.append({
                            "page": page_num,
                            "text": text,
                            "bbox": block["bbox"],
                            "score": self._calculate_heading_score(text, block)
                        })
            return sorted(candidates, key=lambda x: x["page"])
        except Exception as e:
            logger.error(f"Chapter candidate detection failed: {e}")
            return []

    def _is_chapter_heading(self, text: str, block: Dict[str, Any]) -> bool:
        """Check if a text block might be a chapter heading, including Roman numerals."""
        text = text.strip()
        # Check if the text is a Roman numeral
        if ROMAN_NUMERAL_PATTERN.match(text):
            return True
        # Check for chapter keywords
        if any(kw in text for kw in self.config.chapter_keywords):
            return True
        # Check font attributes (if available)
        if "lines" in block and block["lines"]:
            line = block["lines"][0]
            if "spans" in line and line["spans"]:
                span = line["spans"][0]
                if span.get("size", 0) > 12:  # Consider larger font size as potential heading
                    return True
        return False

    def _calculate_heading_score(self, text: str, block: Dict[str, Any]) -> float:
        """Calculate a likelihood score for a chapter heading."""
        score = 0.0
        # Keyword matching
        if any(kw in text for kw in self.config.chapter_keywords):
            score += 2.0
        # Font size
        if "lines" in block and block["lines"]:
            line = block["lines"][0]
            if "spans" in line and line["spans"]:
                span = line["spans"][0]
                if span.get("size", 0) > 14:
                    score += 1.0
        # Capitalization
        if text.isupper():
            score += 0.5
        # Length check (reasonable heading length)
        if 10 <= len(text) <= 100:
            score += 0.5
        # Boost score if the text is a Roman numeral
        if ROMAN_NUMERAL_PATTERN.match(text):
            score += 2.5
        return score

# ---- TOC Extractor ----
class TOCExtractor:
    """Extracts table of contents with fallback to heuristic-based chapter detection."""

    def __init__(self, pdf_path: Union[str, Path]):
        """Initialize with a PDF path."""
        self.processor = PDFProcessor(pdf_path)
        self.processor.open_pdf()

    def extract(self) -> List[Chapter]:
        """Extract chapters from TOC; if unavailable, fall back to chapter detection."""
        try:
            toc_data = self.processor.extract_toc()
            if toc_data:
                # Convert dictionaries to Chapter objects
                chapters = [
                    Chapter(
                        title=entry["title"],
                        page_range=range(entry["start_page"], entry["end_page"] + 1),
                        confidence=entry["confidence"],
                        metadata={"level": entry.get("level", 1)}
                    )
                    for entry in toc_data
                ]
                return chapters
            # Fallback to heuristic-based detection if no TOC found
            detected = self.processor.detect_chapters()
            return [
                Chapter(
                    title=entry["title"],
                    page_range=range(entry["start_page"], entry["end_page"] + 1),
                    confidence=entry["confidence"],
                    metadata=entry.get("metadata", {})
                )
                for entry in detected
            ]
        except Exception as e:
            logger.error(f"Chapter extraction failed: {e}")
            raise PDFProcessingError(f"Failed to extract chapters: {e}")

# ---- Factory Function ----
def create_processor(pdf_path: Union[str, Path], config: Optional[ProcessingConfig] = None) -> PDFProcessor:
    """Create and return a PDFProcessor instance."""
    return PDFProcessor(pdf_path, config)