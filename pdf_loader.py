#!/usr/bin/env python3
"""
pdf_loader.py

Handles loading of PDF files and displaying pages in the application.
Provides PDF loading, page navigation, and display functionality.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from loguru import logger
from pdf_processor import PDFProcessor

# Configure logging
logger.add(
    "logs/pdf_loader_{time}.log",
    rotation="1 MB",
    level="DEBUG",
    format="{time} {level} {message}"
)

class PDFLoaderError(Exception):
    """Base exception for PDF loading errors."""
    pass

@dataclass
class PDFDisplayConfig:
    """Configuration for PDF display settings."""
    max_width: int = 675
    max_height: int = 871
    dpi: int = 300
    pages_per_view: int = 2

class PDFLoader:
    """Handles PDF loading and initialization."""
    
    def __init__(self, file_path: str):
        """Initialize with PDF file path."""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise PDFLoaderError(f"PDF file not found: {file_path}")
        
        try:
            self.pdf_proc = PDFProcessor(str(self.file_path))
        except Exception as e:
            logger.error(f"Failed to initialize PDF processor: {e}")
            raise PDFLoaderError(f"Failed to initialize PDF processor: {e}")

    def load(self) -> PDFProcessor:
        """Load and initialize the PDF processor."""
        try:
            self.pdf_proc.open_pdf()
            logger.info(f"Successfully loaded PDF: {self.file_path}")
            return self.pdf_proc
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            raise PDFLoaderError(f"Failed to load PDF: {e}")

class PDFDisplay:
    """Handles PDF display and navigation."""
    
    def __init__(self, app, config: Optional[PDFDisplayConfig] = None):
        """Initialize display manager."""
        self.app = app
        self.config = config or PDFDisplayConfig()
        
    def load_pdf(self) -> bool:
        """Load PDF through file dialog."""
        try:
            selected_path = filedialog.askopenfilename(
                filetypes=[
                    ("PDF Documents", "*.pdf"),
                    ("All Files", "*.*")
                ]
            )
            
            if not selected_path:
                return False
                
            selected_path = Path(selected_path).absolute()
            self.app.pdf_path = str(selected_path)
            
            # Update status
            self._update_status(f"Loading PDF: {selected_path.name}")
            
            # Initialize loader and processor
            loader = PDFLoader(str(selected_path))
            self.app.pdf_proc = loader.load()
            
            # Update page information
            self.app.total_pages = self.app.pdf_proc.get_total_pages()
            self.app.current_page = 0
            
            self._update_status(f"Loaded PDF: {selected_path.name}")
            self.show_pages()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            self._show_error("PDF Loading Error", str(e))
            return False

    def show_pages(self) -> None:
        """Display current pages."""
        if not self.app.pdf_proc:
            self._show_error("Error", "No PDF is loaded. Please load a PDF first.")
            return
            
        try:
            start_page = self.app.current_page
            end_page = min(start_page + self.config.pages_per_view, self.app.total_pages)
            
            # Process each page
            for i in range(self.config.pages_per_view):
                page_index = start_page + i
                
                if page_index < end_page:
                    # Convert and resize page
                    pil_img = self.app.pdf_proc.convert_page_to_image(
                        page_index,
                        dpi=self.config.dpi
                    )
                    pil_img = self._resize_image(pil_img)
                    
                    # Update display
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self.app.page_labels[i].config(image=tk_img)
                    self.app.page_labels[i].image = tk_img
                else:
                    # Clear excess pages
                    self.app.page_labels[i].config(image='')
                    self.app.page_labels[i].image = None
            
            # Update navigation labels
            self._update_navigation_labels(start_page, end_page)
            
            logger.info(
                f"Showing pages {start_page + 1} to {end_page} "
                f"of {self.app.total_pages}"
            )
            
        except Exception as e:
            logger.error(f"Failed to display pages: {e}")
            self._show_error("Display Error", str(e))

    def navigate_pages(self, direction: int) -> None:
        """
        Navigate pages in specified direction.
        
        Args:
            direction: Integer indicating direction (+1 for forward, -1 for backward)
        """
        if not self.app.pdf_proc:
            self._show_error("Error", "No PDF is loaded.")
            return
            
        new_page = self.app.current_page + (direction * self.config.pages_per_view)
        
        if 0 <= new_page < self.app.total_pages:
            self.app.current_page = new_page
            self.show_pages()
        else:
            logger.info(
                "At document boundary: "
                f"{'end' if direction > 0 else 'beginning'}"
            )

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image while preserving aspect ratio."""
        width_ratio = self.config.max_width / image.width
        height_ratio = self.config.max_height / image.height
        ratio = min(width_ratio, height_ratio)
        
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)
        
        return image.resize((new_width, new_height), Image.LANCZOS)

    def _update_navigation_labels(self, start_page: int, end_page: int) -> None:
        """Update navigation label text."""
        if hasattr(self.app, "prev_page_label"):
            self.app.prev_page_label.config(
                text=f"Page {start_page + 1}"
                if start_page < end_page else ""
            )
        
        if hasattr(self.app, "next_page_label"):
            self.app.next_page_label.config(
                text=f"Page {start_page + 2}"
                if (start_page + 1) < end_page else ""
            )

    def _update_status(self, message: str) -> None:
        """Update status label."""
        if hasattr(self.app, "status_label"):
            self.app.status_label.config(text=message)

    def _show_error(self, title: str, message: str) -> None:
        """Show error message dialog."""
        messagebox.showerror(title, message)

# Convenience functions for backward compatibility
def load_pdf(app) -> None:
    """Load PDF file (compatibility function)."""
    display = PDFDisplay(app)
    display.load_pdf()

def show_pages(app) -> None:
    """Display current pages (compatibility function)."""
    display = PDFDisplay(app)
    display.show_pages()

def show_prev_page(app) -> None:
    """Show previous pages (compatibility function)."""
    display = PDFDisplay(app)
    display.navigate_pages(-1)

def show_next_page(app) -> None:
    """Show next pages (compatibility function)."""
    display = PDFDisplay(app)
    display.navigate_pages(1)

# Create display manager
def create_pdf_display(app, config: Optional[PDFDisplayConfig] = None) -> PDFDisplay:
    """Create and return a PDFDisplay instance."""
    return PDFDisplay(app, config)