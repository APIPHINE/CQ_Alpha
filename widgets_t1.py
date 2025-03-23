#!/usr/bin/env python3
"""
widgets_t1.py

PDF Processor Tab - Handles PDF loading, chapter detection, and page display.
"""

import tkinter as tk
from tkinter import ttk, Frame, messagebox, simpledialog, filedialog
from typing import Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageTk
if not hasattr(Image, "LINEAR"):
    Image.LINEAR = Image.BILINEAR
from loguru import logger

@dataclass
class PDFTabConfig:
    """Configuration for PDF tab display."""
    # The displayed PDF will be scaled to 75% (i.e. 25% smaller)
    page_width: int = 675   # Adjusted for 25% reduction
    page_height: int = 872  # Adjusted for 25% reduction
    pages_per_view: int = 2
    chapter_list_width: int = 50

class PDFProcessorTab:
    """Manages the PDF processing tab interface and functionality."""
    
    def __init__(self, app, parent: Frame, config: Optional[PDFTabConfig] = None):
        self.app = app
        self.parent = parent
        self.config = config or PDFTabConfig()
        
        # State variables
        self.current_page: int = 0
        self.total_pages: int = 0
        self.chapters: List[Tuple[str, range]] = []
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create all widgets for the PDF tab."""
        # First, create the chapter sidebar at the top (for chapters)
        self._create_chapter_sidebar()
        # Then, create the toolbar and main content area (with navigation and page display)
        self._create_toolbar()
        self._create_main_content()
        
    def _create_toolbar(self):
        """Create the toolbar with control buttons."""
        toolbar = Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        buttons = [
            ("Load PDF", self._load_pdf),
            ("Detect Chapters", self._detect_chapters),
            ("Extract Selected", self._extract_selected_chapter),
            ("Extract All", self._extract_all_chapters)
        ]
        
        for text, command in buttons:
            ttk.Button(toolbar, text=text, command=command).pack(side=tk.LEFT, padx=2)
            
        self.status_label = ttk.Label(toolbar, text="No PDF loaded")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
    def _create_chapter_sidebar(self):
        """
        Create a chapter sidebar that appears above the main PDF display area.
        This sidebar contains chapter control buttons and a listbox.
        """
        sidebar = ttk.LabelFrame(self.parent, text="Chapters")
        sidebar.pack(fill=tk.X, padx=5, pady=5)
        
        # Chapter control buttons (horizontal layout)
        controls = Frame(sidebar)
        controls.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(controls, text="Add", command=self._add_chapter).pack(side=tk.LEFT)
        ttk.Button(controls, text="Edit", command=self._edit_chapter).pack(side=tk.LEFT)
        ttk.Button(controls, text="Remove", command=self._remove_chapter).pack(side=tk.LEFT)
        
        # Chapter listbox
        self.chapter_listbox = tk.Listbox(sidebar, width=self.config.chapter_list_width, selectmode=tk.SINGLE)
        self.chapter_listbox.pack(fill=tk.X, padx=5, pady=5)
        
    def _create_main_content(self):
        """Create the main content area showing PDF pages with navigation and a scroll bar."""
        # Create a container frame for all content
        content = Frame(self.parent)
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Navigation Controls ---
        nav_frame = Frame(content)
        nav_frame.pack(fill=tk.X)
        ttk.Button(nav_frame, text="← Previous", command=self._prev_pages).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="Next →", command=self._next_pages).pack(side=tk.RIGHT, padx=2)

        # Bind arrow keys for navigation and scrolling
        content.bind("<Left>", lambda e: self._prev_pages())
        content.bind("<Right>", lambda e: self._next_pages())
        content.bind("<Up>", lambda e: self._scroll_canvas(-1))
        content.bind("<Down>", lambda e: self._scroll_canvas(1))
        content.focus_set()

        # --- Scrollable Page Display Area ---
        # Create a container for the scrollable canvas and its scrollbar.
        container = Frame(content)
        container.pack(fill=tk.BOTH, expand=True)

        # Create a canvas inside the container.
        self.canvas = tk.Canvas(container)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create a vertical scrollbar linked to the canvas.
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame inside the canvas that will hold your page display widgets.
        self.page_frame = Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.page_frame, anchor="nw")

        # Update the scroll region whenever the size of the page_frame changes.
        self.page_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Create page_labels and attach them to self.app for external update (e.g., by pdf_loader.show_pages)
        self.app.page_labels = []
        for i in range(self.config.pages_per_view):
            label = ttk.Label(self.page_frame)
            label.pack(side=tk.LEFT, padx=5, pady=5)
            self.app.page_labels.append(label)
        self.page_labels = self.app.page_labels  # Local reference
        
    def _scroll_canvas(self, direction: int):
        """Scroll the content vertically. 'direction' should be -1 for up, 1 for down."""
        # If the main app has a canvas (e.g., pdf_canvas) with scrolling, use it.
        if hasattr(self.app, "pdf_canvas"):
            self.app.pdf_canvas.yview_scroll(direction, "units")
        
    def _load_pdf(self):
        """Handle PDF loading by delegating to the main app."""
        try:
            if hasattr(self.app, 'load_pdf'):
                self.app.load_pdf()
            else:
                raise AttributeError("PDF loading not implemented")
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            self._show_error("PDF Loading Error", str(e))
            
    def _detect_chapters(self):
        """Handle chapter detection."""
        try:
            # Dummy implementation: show informational message.
            messagebox.showinfo("Info", "Chapter detection is not implemented yet.")
            logger.error("Chapter detection not implemented")
        except Exception as e:
            logger.error(f"Failed to detect chapters: {e}")
            self._show_error("Chapter Detection Error", str(e))
            
    def _extract_selected_chapter(self):
        """Handle extraction of the selected chapter."""
        try:
            # Dummy implementation: show informational message.
            messagebox.showinfo("Info", "Chapter extraction is not implemented yet.")
            logger.error("Chapter extraction not implemented")
        except Exception as e:
            logger.error(f"Failed to extract chapter: {e}")
            self._show_error("Extraction Error", str(e))
            
    def _extract_all_chapters(self):
        """Handle extraction of all chapters."""
        try:
            # Dummy implementation: show informational message.
            messagebox.showinfo("Info", "Batch chapter extraction is not implemented yet.")
            logger.error("Batch extraction not implemented")
        except Exception as e:
            logger.error(f"Failed to extract chapters: {e}")
            self._show_error("Batch Extraction Error", str(e))
            
    def _prev_pages(self):
        """Show previous pages (via left arrow key or button)."""
        try:
            if hasattr(self.app, 'show_prev_page'):
                self.app.show_prev_page()
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            
    def _next_pages(self):
        """Show next pages (via right arrow key or button)."""
        try:
            if hasattr(self.app, 'show_next_page'):
                self.app.show_next_page()
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            
    def _add_chapter(self):
        """Add a new chapter manually by delegating to the main app."""
        try:
            if hasattr(self.app, 'add_chapter'):
                self.app.add_chapter()
        except Exception as e:
            logger.error(f"Failed to add chapter: {e}")
            
    def _edit_chapter(self):
        """Edit selected chapter by delegating to the main app."""
        try:
            if hasattr(self.app, 'edit_chapter_range'):
                self.app.edit_chapter_range()
        except Exception as e:
            logger.error(f"Failed to edit chapter: {e}")
            
    def _remove_chapter(self):
        """Remove selected chapter by delegating to the main app."""
        try:
            if hasattr(self.app, 'remove_chapter'):
                self.app.remove_chapter()
        except Exception as e:
            logger.error(f"Failed to remove chapter: {e}")
            
    def _show_error(self, title: str, message: str):
        """Show an error message dialog."""
        tk.messagebox.showerror(title, message)
        
    def update_status(self, message: str):
        """Update the status label."""
        self.status_label.config(text=message)

def create_pdf_widgets(app, parent: Frame) -> PDFProcessorTab:
    """Create and return a PDFProcessorTab instance."""
    return PDFProcessorTab(app, parent)