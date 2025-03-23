#!/usr/bin/env python3
"""
chapter_extractor.py

Handles chapter extraction from PDFs and merges pages into single images.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image
import logging

from pdf_processor import PDFProcessor

# Configure logging
logging.basicConfig(
    filename="logs/chapter_extractor.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CHAPTERS_DIR = "chapters"

class ChapterExtractionError(Exception):
    """Base exception for chapter extraction errors."""
    pass

@dataclass
class ChapterConfig:
    """Configuration for chapter extraction."""
    dpi: int = 300
    margin: int = 10
    output_dir: str = CHAPTERS_DIR

class ChapterExtractor:
    """Handles chapter extraction and page merging."""

    def __init__(self, pdf_path: str, config: Optional[ChapterConfig] = None):
        """Initialize with PDF path and optional configuration."""
        self.pdf_path = Path(pdf_path)
        self.config = config or ChapterConfig()

        if not self.pdf_path.exists():
            raise ChapterExtractionError(f"PDF file not found: {pdf_path}")

        try:
            self.pdf_proc = PDFProcessor(str(self.pdf_path))
            self.pdf_proc.open_pdf()
        except Exception as e:
            logger.error(f"Failed to initialize PDF processor: {e}")
            raise ChapterExtractionError(f"Failed to initialize PDF processor: {e}")

    def process_chapters(self) -> List[Dict[str, Any]]:
        """
        Extract chapters from PDF using TOC or detection heuristics.

        Returns:
            List of dictionaries containing chapter information:
            {
                'title': str,
                'page_range': range,
                'confidence': float
            }
        """
        try:
            chapters = []

            # First try to extract from TOC
            toc_chapters = self.pdf_proc.extract_toc()
            if toc_chapters:
                for ch in toc_chapters:
                    chapters.append({
                        'title': ch['title'],
                        'page_range': range(ch['start_page'], ch['end_page'] + 1),
                        'confidence': 1.0  # High confidence for TOC-based extraction
                    })
                logger.info(f"Extracted {len(chapters)} chapters from TOC")
                return chapters

            # If no TOC, use heuristic detection
            detected_chapters = self._detect_chapters_heuristically()
            if detected_chapters:
                chapters.extend(detected_chapters)
                logger.info(f"Detected {len(chapters)} chapters heuristically")

            return chapters

        except Exception as e:
            logger.error(f"Chapter processing failed: {e}")
            raise ChapterExtractionError(f"Failed to process chapters: {e}")

    def _detect_chapters_heuristically(self) -> List[Dict[str, Any]]:
        """
        Detect chapters using text analysis and layout heuristics.

        Returns:
            List of detected chapter information
        """
        chapters = []
        try:
            total_pages = self.pdf_proc.get_total_pages()
            current_chapter = None

            for page_num in range(total_pages):
                # Get page text and analyze for chapter indicators
                page_text = self.pdf_proc.get_page_text(page_num)

                # Simple heuristic: Look for "Chapter" followed by number
                if "Chapter" in page_text:
                    # If we were tracking a chapter, close it
                    if current_chapter:
                        current_chapter['page_range'] = range(
                            current_chapter['start_page'],
                            page_num
                        )
                        chapters.append(current_chapter)

                    # Start new chapter
                    current_chapter = {
                        'title': f"Chapter {len(chapters) + 1}",
                        'start_page': page_num,
                        'confidence': 0.85  # Lower confidence for heuristic detection
                    }

            # Handle last chapter
            if current_chapter:
                current_chapter['page_range'] = range(
                    current_chapter['start_page'],
                    total_pages
                )
                chapters.append(current_chapter)

            return chapters

        except Exception as e:
            logger.error(f"Heuristic chapter detection failed: {e}")
            return []

    def extract(self, selected_range: range, chapter_index: int) -> str:
        """
        Extract chapter pages and merge into single image.

        Args:
            selected_range: Page range for the chapter
            chapter_index: Chapter number for output filename

        Returns:
            Path to the output image file
        """
        try:
            # Create output directory
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Convert pages to images
            page_images = []
            for page_num in selected_range:
                image = self.pdf_proc.convert_page_to_image(
                    page_num,
                    dpi=self.config.dpi
                )
                page_images.append(image)

            # Merge images
            if not page_images:
                raise ChapterExtractionError("No pages to merge")

            merged_image = merge_pages_into_single_image(page_images)

            # Save result
            output_path = output_dir / f"chapter_{chapter_index}.png"
            merged_image.save(str(output_path))

            logger.info(f"Saved chapter {chapter_index} to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Chapter extraction failed: {e}")
            raise ChapterExtractionError(f"Failed to extract chapter: {e}")

def merge_pages_into_single_image(images: List[Image.Image]) -> Image.Image:
    """
    Merge multiple page images into a single vertical image.

    Args:
        images: List of page images to merge

    Returns:
        Merged image
    """
    try:
        if not images:
            raise ChapterExtractionError("No images to merge")

        # Calculate dimensions
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)

        # Create new image
        merged = Image.new(
            "RGB",
            (total_width, total_height),
            color=(255, 255, 255)
        )

        # Paste images
        current_y = 0
        for img in images:
            merged.paste(img, (0, current_y))
            current_y += img.height

        return merged

    except Exception as e:
        logger.error(f"Image merging failed: {e}")
        raise ChapterExtractionError(f"Failed to merge images: {e}")

# Utility functions
def create_extractor(
    pdf_path: str,
    config: Optional[ChapterConfig] = None
) -> ChapterExtractor:
    """Create and return a ChapterExtractor instance."""
    return ChapterExtractor(pdf_path, config)