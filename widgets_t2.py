#!/usr/bin/env python3
"""
widgets_t2.py

Image Processor Tab - Handles image loading, paragraph extraction, and OCR processing.
Primary interface for processing chapter images extracted from Tab 1.
"""

import tkinter as tk
from tkinter import ttk, Frame, Canvas, messagebox, filedialog
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageTk
from loguru import logger

@dataclass
class ImageTabConfig:
    """Configuration for image processing tab."""
    canvas_width: int = 800
    canvas_height: int = 600
    paragraph_list_width: int = 40
    supported_formats: tuple = ('.png', '.jpg', '.jpeg', '.tif', '.tiff')
    min_confidence: float = 0.75

class ParagraphViewer(tk.Toplevel):
    """Popup window for viewing extracted paragraphs."""

    def __init__(self, parent, paragraph_data: Dict[str, Any]):
        super().__init__(parent)
        self.title(f"Paragraph Viewer")
        self.geometry("800x600")

        self.paragraph_data = paragraph_data
        self._create_widgets()

    def _create_widgets(self):
        """Create widgets for paragraph viewing."""
        # Image display
        img_frame = Frame(self)
        img_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = Canvas(
            img_frame,
            bg="white",
            width=700,
            height=400
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Display image
        if 'image' in self.paragraph_data:
            img = self.paragraph_data['image']
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.create_image(
                0, 0,
                anchor="nw",
                image=self.tk_image
            )

        # Metadata display
        meta_frame = Frame(self)
        meta_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(meta_frame, text="Metadata:").pack(anchor="w")

        self.meta_text = tk.Text(meta_frame, height=10)
        self.meta_text.pack(fill=tk.X)

        # Format and display metadata
        meta_str = (
            f"Confidence: {self.paragraph_data.get('confidence', 'N/A')}\n"
            f"Text: {self.paragraph_data.get('text', '')}\n"
            f"Bbox: {self.paragraph_data.get('bbox', '')}\n"
        )
        self.meta_text.insert("1.0", meta_str)
        self.meta_text.config(state="disabled")

class ImageProcessorTab:
    """Manages the image processing tab interface and functionality."""

    def __init__(self, app, parent: Union[tk.Frame, ttk.Frame], config: Optional[ImageTabConfig] = None):
        self.app = app
        self.parent = parent
        self.config = config or ImageTabConfig()

        # State variables
        self.image_list: List[Path] = []
        self.current_index: int = 0
        self.current_image: Optional[Image.Image] = None
        self.paragraphs: List[Dict[str, Any]] = []

        self._create_widgets()

    def _create_widgets(self):
        """Create all widgets for the image processing tab."""
        self._create_toolbar()
        self._create_main_area()
        self._create_paragraph_list()

    def _create_toolbar(self):
        """Create the toolbar with control buttons."""
        toolbar = Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        buttons = [
            ("Load Image", self._load_single_image),
            ("Load Folder", self._load_image_folder),
            ("Previous", self._prev_image),
            ("Next", self._next_image),
            ("Extract Paragraphs", self._extract_paragraphs)
        ]

        for text, command in buttons:
            ttk.Button(
                toolbar,
                text=text,
                command=command
            ).pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(toolbar, text="No image loaded")
        self.status_label.pack(side=tk.RIGHT, padx=5)

    def _create_main_area(self):
        """Create the main image display area."""
        self.canvas = Canvas(
            self.parent,
            bg="gray",
            width=self.config.canvas_width,
            height=self.config.canvas_height
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add scrollbars
        self.v_scroll = ttk.Scrollbar(
            self.parent,
            orient="vertical",
            command=self.canvas.yview
        )
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.h_scroll = ttk.Scrollbar(
            self.parent,
            orient="horizontal",
            command=self.canvas.xview
        )
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set
        )

    def _create_paragraph_list(self):
        """Create the paragraph list sidebar."""
        list_frame = ttk.LabelFrame(self.parent, text="Extracted Paragraphs")
        list_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        self.para_listbox = tk.Listbox(
            list_frame,
            width=self.config.paragraph_list_width
        )
        self.para_listbox.pack(fill=tk.BOTH, expand=True)

        # Bind double-click to view paragraph
        self.para_listbox.bind('<Double-Button-1>', self._view_paragraph)

    def _load_single_image(self):
        """Load a single image file."""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("Image files", "*" + ";*".join(self.config.supported_formats)),
                    ("All files", "*.*")
                ]
            )

            if not file_path:
                return

            self.load_image(Path(file_path))

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            self._show_error("Image Loading Error", str(e))

    def _load_image_folder(self):
        """Load a folder of images."""
        try:
            folder_path = filedialog.askdirectory()
            if not folder_path:
                return

            folder = Path(folder_path)
            self.image_list = [
                f for f in folder.iterdir()
                if f.suffix.lower() in self.config.supported_formats
            ]

            if not self.image_list:
                raise ValueError("No supported images found in folder")

            self.current_index = 0
            self.load_image(self.image_list[0])

        except Exception as e:
            logger.error(f"Failed to load image folder: {e}")
            self._show_error("Folder Loading Error", str(e))

    def load_image(self, path: Path):
        """Load and display an image."""
        try:
            self.current_image = Image.open(path).convert("RGB")
            self._display_current_image()
            self.status_label.config(text=f"Loaded: {path.name}")
            logger.info(f"Loaded image: {path}")

        except Exception as e:
            logger.error(f"Failed to load image {path}: {e}")
            self._show_error("Image Loading Error", str(e))

    def _display_current_image(self):
        """Display the current image on the canvas."""
        if not self.current_image:
            return

        # Calculate scaling
        scale = min(
            self.config.canvas_width / self.current_image.width,
            self.config.canvas_height / self.current_image.height
        )

        new_size = (
            int(self.current_image.width * scale),
            int(self.current_image.height * scale)
        )

        # Resize and display using Resampling.LANCZOS
        display_image = self.current_image.resize(new_size, Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _extract_paragraphs(self):
        """Extract paragraphs from current image."""
        try:
            if not self.current_image:
                raise ValueError("No image loaded")

            # Clear previous results
            self.paragraphs = []
            self.para_listbox.delete(0, tk.END)

            # Extract paragraphs using OCR processor
            if hasattr(self.app, 'img_processor'):
                self.paragraphs = self.app.img_processor.detect_paragraphs_with_metadata(
                    self.current_image,
                    chapter=1,
                    output_dir="paragraphs"
                )

                # Update listbox
                for idx, para in enumerate(self.paragraphs, 1):
                    confidence = para.get('confidence', 0)
                    text = para.get('text', '')[:30] + '...'
                    self.para_listbox.insert(
                        tk.END,
                        f"Para {idx} ({confidence:.2f}): {text}"
                    )

                self.status_label.config(
                    text=f"Extracted {len(self.paragraphs)} paragraphs"
                )

            else:
                raise AttributeError("Image processor not initialized")

        except Exception as e:
            logger.error(f"Paragraph extraction failed: {e}")
            self._show_error("Extraction Error", str(e))

    def _view_paragraph(self, event):
        """Handle paragraph selection for viewing."""
        selection = self.para_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx < len(self.paragraphs):
            ParagraphViewer(self.parent, self.paragraphs[idx])

    def _prev_image(self):
        """Show previous image in folder."""
        if self.image_list and self.current_index > 0:
            self.current_index -= 1
            self.load_image(self.image_list[self.current_index])

    def _next_image(self):
        """Show next image in folder."""
        if self.image_list and self.current_index < len(self.image_list) - 1:
            self.current_index += 1
            self.load_image(self.image_list[self.current_index])

    def _show_error(self, title: str, message: str):
        """Show error message."""
        messagebox.showerror(title, message)

def create_image_widgets(app, parent: Frame) -> ImageProcessorTab:
    """Create and return an ImageProcessorTab instance."""
    return ImageProcessorTab(app, parent)