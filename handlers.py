#!/usr/bin/env python3
"""
handlers.py

Handles operations related to PDF processing and chapter/citation extraction.
Provides event handlers and processing logic for the PDF reader application.
"""

import os
import threading
import json
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog
from pdf_processor import PDFProcessor
from chapter_extractor import merge_pages_into_single_image, CHAPTERS_DIR
from ocr_processor import extract_citations_from_paragraph
from loguru import logger

# Configure logging
logger.add(
    "logs/handlers_{time}.log",
    rotation="1 MB",
    level="DEBUG",
    format="{time} {level} {message}"
)

class HandlerError(Exception):
    """Base exception for handler errors."""
    pass

@dataclass
class Chapter:
    """Data class for chapter information."""
    title: str
    page_range: range
    index: int
    extracted_path: Optional[str] = None

    def format_display(self) -> str:
        """Format chapter for display in listbox."""
        return f"{self.title} [Page {self.page_range.start + 1}, Page {self.page_range.stop}]"

class ChapterExtractor:
    """Handles chapter extraction operations."""
    
    def __init__(self, pdf_path: str):
        """Initialize with PDF path."""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise HandlerError(f"PDF file not found: {pdf_path}")
        self.pdf_proc = PDFProcessor(str(self.pdf_path))

    def extract(self, selected_range: range, chapter_index: int) -> str:
        """Extract chapter pages to single image."""
        try:
            self.pdf_proc.open_pdf()
            
            # Ensure output directory exists
            output_dir = Path(CHAPTERS_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            out_filename = output_dir / f"chapter_{chapter_index}.png"
            merge_pages_into_single_image(
                self.pdf_proc,
                selected_range,
                str(out_filename),
                dpi=300
            )
            
            logger.info(f"Extracted chapter {chapter_index} to {out_filename}")
            return str(out_filename)
            
        except Exception as e:
            logger.error(f"Failed to extract chapter {chapter_index}: {e}")
            raise HandlerError(f"Chapter extraction failed: {e}")

class PDFHandler:
    """Handles PDF-related operations."""
    
    def __init__(self, app_instance):
        """Initialize with application instance."""
        self.app = app_instance
        self.chapters: List[Chapter] = []

    def load_pdf(self) -> bool:
        """Load PDF file."""
        try:
            if not self.app.pdf_path:
                raise HandlerError("No PDF path specified")
                
            self.app.pdf_proc = PDFProcessor(self.app.pdf_path)
            self.app.pdf_proc.open_pdf()
            self.app.current_page = 0
            
            self.display_pages()
            return True
            
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            self._show_error("PDF Loading Error", str(e))
            return False

    def load_chapters(self) -> List[Chapter]:
        """Load chapters from PDF."""
        try:
            if not self.app.pdf_path:
                raise HandlerError("Please load a PDF first!")
                
            pdf_proc = PDFProcessor(self.app.pdf_path)
            pdf_proc.open_pdf()
            
            # Try TOC first, then detection
            chapters_raw = pdf_proc.extract_toc() or pdf_proc.detect_chapters()
            if not chapters_raw:
                logger.warning("No chapters detected")
                messagebox.showwarning("Warning", "No chapters detected")
                return []
                
            # Convert to Chapter objects
            self.chapters = []
            self.app.chapter_listbox.delete(0, tk.END)
            
            for idx, (title, page_range) in enumerate(chapters_raw):
                chapter = Chapter(
                    title=title,
                    page_range=page_range,
                    index=idx
                )
                self.chapters.append(chapter)
                self.app.chapter_listbox.insert(
                    tk.END,
                    chapter.format_display()
                )
                
            return self.chapters
            
        except Exception as e:
            logger.error(f"Failed to load chapters: {e}")
            self._show_error("Chapter Loading Error", str(e))
            return []

    def extract_chapter(self, chapter: Chapter) -> None:
        """Extract a single chapter."""
        try:
            def extraction_thread():
                try:
                    extractor = ChapterExtractor(self.app.pdf_path)
                    saved_path = extractor.extract(
                        chapter.page_range,
                        chapter.index + 1
                    )
                    
                    if saved_path:
                        chapter.extracted_path = saved_path
                        self._update_status(
                            f"Saved Chapter {chapter.index + 1} to {saved_path}",
                            "green"
                        )
                        
                except Exception as e:
                    logger.error(f"Extraction thread error: {e}")
                    self._show_error("Extraction Error", str(e))

            thread = threading.Thread(
                target=extraction_thread,
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start extraction: {e}")
            raise HandlerError(f"Extraction failed: {e}")

    def extract_all_chapters(self) -> None:
        """Extract all chapters."""
        for chapter in self.chapters:
            self.extract_chapter(chapter)

    def edit_chapter_range(self, chapter: Chapter) -> bool:
        """Edit chapter page range."""
        try:
            new_start = simpledialog.askinteger(
                "Edit Chapter",
                f"Enter new start page for '{chapter.title}':",
                minvalue=1
            )
            if new_start is None:
                return False
                
            new_end = simpledialog.askinteger(
                "Edit Chapter",
                f"Enter new end page for '{chapter.title}':",
                minvalue=new_start
            )
            if new_end is None:
                return False
                
            # Update chapter
            chapter.page_range = range(new_start - 1, new_end)
            
            # Update display
            idx = self.chapters.index(chapter)
            self.app.chapter_listbox.delete(idx)
            self.app.chapter_listbox.insert(
                idx,
                chapter.format_display()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to edit chapter: {e}")
            self._show_error("Edit Error", str(e))
            return False

    def display_pages(self) -> None:
        """Display current pages."""
        if not self.app.pdf_proc:
            return
            
        try:
            start_page = self.app.current_page
            total_pages = self.app.pdf_proc.get_total_pages()
            end_page = min(start_page + 2, total_pages)
            
            for i in range(2):
                if start_page + i < end_page:
                    page_image = self.app.pdf_proc.convert_page_to_image(
                        start_page + i,
                        dpi=300
                    )
                    self.app.page_labels[i].config(image=page_image)
                    self.app.page_labels[i].image = page_image
                    self.app.page_numbers[i].config(
                        text=f"Page {start_page + i + 1}"
                    )
                else:
                    self.app.page_labels[i].config(image='')
                    self.app.page_numbers[i].config(text='')
                    
        except Exception as e:
            logger.error(f"Failed to display pages: {e}")
            self._show_error("Display Error", str(e))

    def navigate_pages(self, direction: int) -> None:
        """Navigate pages in specified direction."""
        if not self.app.pdf_proc:
            return
            
        new_page = self.app.current_page + (direction * 2)
        total_pages = self.app.pdf_proc.get_total_pages()
        
        if 0 <= new_page < total_pages:
            self.app.current_page = new_page
            self.display_pages()

    def _show_error(self, title: str, message: str) -> None:
        """Show error message dialog."""
        messagebox.showerror(title, message)

    def _update_status(self, message: str, color: str = "black") -> None:
        """Update status label."""
        if hasattr(self.app, 'status_label'):
            self.app.status_label.config(text=message, fg=color)

# Create handler instances
def create_handlers(app_instance) -> Tuple[PDFHandler, ChapterExtractor]:
    """Create and return handler instances."""
    return (
        PDFHandler(app_instance),
        ChapterExtractor(app_instance.pdf_path) if app_instance.pdf_path else None
    )