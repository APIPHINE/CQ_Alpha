#!/usr/bin/env python3
"""
widgets_t3.py

Citation Manager Tab - Handles loading, display, and annotation of extracted citations.
Manages metadata and annotations for paragraphs processed in Tab 2.
"""

import json
import tkinter as tk
from tkinter import ttk, Frame, Canvas, messagebox, filedialog
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageTk
import logging

# Configure logging
logging.basicConfig(
    filename="logs/widgets_t3.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CitationTabConfig:
    """Configuration for citation manager tab."""
    canvas_width: int = 800
    canvas_height: int = 600
    metadata_width: int = 40
    supported_formats: tuple = ('.png', '.jpg', '.jpeg', '.tif', '.tiff')
    metadata_autosave: bool = True


@dataclass
class Citation:
    """Structure for citation data."""
    image_path: Path
    text: str
    context: str
    confidence: float
    annotations: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to dictionary format."""
        return {
            "image_path": str(self.image_path),
            "text": self.text,
            "context": self.context,
            "confidence": self.confidence,
            "annotations": self.annotations,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Citation':
        """Create Citation instance from dictionary."""
        return cls(image_path=Path(data["image_path"]),
                   text=data["text"],
                   context=data["context"],
                   confidence=data["confidence"],
                   annotations=data["annotations"],
                   metadata=data["metadata"])


class AnnotationDialog(tk.Toplevel):
    """Dialog for editing citation annotations."""

    def __init__(self, parent, citation: Citation, callback):
        super().__init__(parent)
        self.title("Edit Citation Annotations")
        self.geometry("600x400")

        self.citation = citation
        self.callback = callback
        self._create_widgets()

    def _create_widgets(self):
        """Create dialog widgets."""
        # Citation text display
        text_frame = ttk.LabelFrame(self, text="Citation Text")
        text_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(text_frame, text=self.citation.text,
                  wraplength=550).pack(padx=5, pady=5)

        # Annotation editor
        edit_frame = ttk.LabelFrame(self, text="Annotations")
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.editor = tk.Text(edit_frame)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Pre-fill with current annotations
        self.editor.insert("1.0",
                           json.dumps(self.citation.annotations, indent=4))

        # Buttons
        button_frame = Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="Save",
                   command=self._save).pack(side=tk.RIGHT, padx=5)

        ttk.Button(button_frame, text="Cancel",
                   command=self.destroy).pack(side=tk.RIGHT)

    def _save(self):
        """Save annotations and close dialog."""
        try:
            # Parse annotations
            annotations = json.loads(self.editor.get("1.0", tk.END))

            # Update citation
            self.citation.annotations = annotations

            # Callback
            if self.callback:
                self.callback(self.citation)

            self.destroy()

        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON",
                                 f"Please check your annotation format: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save annotations: {e}")


class CitationManagerTab:
    """Manages the citation manager tab interface and functionality."""

    def __init__(self,
                 app,
                 parent: Frame,
                 config: Optional[CitationTabConfig] = None):
        self.app = app
        self.parent = parent
        self.config = config or CitationTabConfig()

        # State variables
        self.citations: List[Citation] = []
        self.current_index: int = 0
        self.current_image: Optional[ImageTk.PhotoImage] = None

        self._create_widgets()

    def _create_widgets(self):
        """Create all widgets for the citation manager tab."""
        self._create_toolbar()
        self._create_main_area()
        self._create_metadata_panel()

    def _create_toolbar(self):
        """Create the toolbar with control buttons."""
        toolbar = Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        buttons = [("Load Citations", self._load_citations),
                   ("Previous", self._prev_citation),
                   ("Next", self._next_citation),
                   ("Annotate", self._annotate_current),
                   ("Export", self._export_citations)]

        for text, command in buttons:
            ttk.Button(toolbar, text=text, command=command).pack(side=tk.LEFT,
                                                                 padx=2)

        self.status_label = ttk.Label(toolbar, text="No citations loaded")
        self.status_label.pack(side=tk.RIGHT, padx=5)

    def _create_main_area(self):
        """Create the main citation display area."""
        self.canvas = Canvas(self.parent,
                             bg="white",
                             width=self.config.canvas_width,
                             height=self.config.canvas_height)
        self.canvas.pack(side=tk.LEFT,
                         fill=tk.BOTH,
                         expand=True,
                         padx=5,
                         pady=5)

    def _create_metadata_panel(self):
        """Create the metadata display panel."""
        meta_frame = ttk.LabelFrame(self.parent, text="Citation Metadata")
        meta_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        self.meta_text = tk.Text(meta_frame,
                                 width=self.config.metadata_width,
                                 wrap=tk.WORD)
        self.meta_text.pack(fill=tk.BOTH, expand=True)

    def _load_citations(self):
        """Load citations from a folder."""
        try:
            folder_path = filedialog.askdirectory(
                title="Select Citations Folder")
            if not folder_path:
                return

            folder = Path(folder_path)

            # Find image files
            image_files = [
                f for f in folder.iterdir()
                if f.suffix.lower() in self.config.supported_formats
            ]

            if not image_files:
                raise ValueError("No citation images found")

            # Load citations
            self.citations = []
            for img_path in image_files:
                json_path = img_path.with_suffix('.json')

                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = {
                        "text": "",
                        "context": "",
                        "confidence": 0.0,
                        "annotations": {},
                        "metadata": {
                            "filename": img_path.name
                        }
                    }

                citation = Citation(image_path=img_path, **data)
                self.citations.append(citation)

            self.current_index = 0
            self._display_current_citation()

            self.status_label.config(
                text=f"Loaded {len(self.citations)} citations")

        except Exception as e:
            logger.error(f"Failed to load citations: {e}")
            messagebox.showerror("Error", f"Failed to load citations: {e}")

    def _display_current_citation(self):
        """Display the current citation."""
        if not self.citations:
            return

        citation = self.citations[self.current_index]

        try:
            # Load and display image
            image = Image.open(citation.image_path)
            self._display_image(image)

            # Update metadata display
            self._update_metadata_display(citation)

            # Update status
            self.status_label.config(
                text=
                f"Citation {self.current_index + 1} of {len(self.citations)}")

        except Exception as e:
            logger.error(f"Failed to display citation: {e}")
            messagebox.showerror("Error", f"Failed to display citation: {e}")

    def _display_image(self, image: Image.Image):
        """Display an image on the canvas."""
        # Calculate scaling
        scale = min(self.config.canvas_width / image.width,
                    self.config.canvas_height / image.height)

        new_size = (int(image.width * scale), int(image.height * scale))

        # Resize and display using Resampling.LANCZOS
        display_image = image.resize(new_size, Image.Resampling.LANCZOS)
        self.current_image = ImageTk.PhotoImage(display_image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.current_image)

    def _update_metadata_display(self, citation: Citation):
        """Update the metadata display."""
        self.meta_text.delete("1.0", tk.END)

        meta_str = (f"Text: {citation.text}\n\n"
                    f"Context: {citation.context}\n\n"
                    f"Confidence: {citation.confidence:.2f}\n\n"
                    f"Annotations:\n"
                    f"{json.dumps(citation.annotations, indent=2)}\n\n"
                    f"Metadata:\n"
                    f"{json.dumps(citation.metadata, indent=2)}")

        self.meta_text.insert("1.0", meta_str)
        self.meta_text.config(state="disabled")

    def _prev_citation(self):
        """Show previous citation."""
        if self.citations and self.current_index > 0:
            self.current_index -= 1
            self._display_current_citation()

    def _next_citation(self):
        """Show next citation."""
        if self.citations and self.current_index < len(self.citations) - 1:
            self.current_index += 1
            self._display_current_citation()

    def _annotate_current(self):
        """Open annotation dialog for current citation."""
        if not self.citations:
            return

        def update_citation(updated: Citation):
            """Handle citation update."""
            self.citations[self.current_index] = updated
            self._save_citation(updated)
            self._display_current_citation()

        AnnotationDialog(self.parent, self.citations[self.current_index],
                         update_citation)

    def _save_citation(self, citation: Citation):
        """Save citation metadata to file."""
        try:
            json_path = citation.image_path.with_suffix('.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(citation.to_dict(), f, indent=4)
            logger.info(f"Saved citation metadata to {json_path}")

        except Exception as e:
            logger.error(f"Failed to save citation: {e}")
            messagebox.showerror("Error", f"Failed to save citation: {e}")

    def _export_citations(self):
        """Export all citations to a single JSON file."""
        try:
            if not self.citations:
                raise ValueError("No citations to export")

            export_path = filedialog.asksaveasfilename(
                defaultextension=".json", filetypes=[("JSON files", "*.json")])

            if not export_path:
                return

            data = {
                "citations": [c.to_dict() for c in self.citations],
                "metadata": {
                    "count": len(self.citations),
                    "version": "1.0"
                }
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            messagebox.showinfo("Success",
                                f"Exported {len(self.citations)} citations")

        except Exception as e:
            logger.error(f"Failed to export citations: {e}")
            messagebox.showerror("Error", f"Failed to export citations: {e}")


def create_tab3_widgets(app, parent: Frame) -> CitationManagerTab:
    """Create and return a CitationManagerTab instance."""
    return CitationManagerTab(app, parent)
