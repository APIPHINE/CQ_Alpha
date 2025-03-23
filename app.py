#!/usr/bin/env python3
"""
app.py

Main application for PDF and Image Processing with Citation Management.
Integrates three tabs:
1. PDF Processor - For PDF loading and chapter extraction
2. Image Processor - For image loading and paragraph extraction
3. Citation Manager - For managing extracted citations and annotations
"""

import os
import threading
import datetime
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
if not hasattr(Image, "LINEAR"):
    Image.LINEAR = Image.BILINEAR


# Local imports
from loguru import logger
from pdf_loader import PDFLoader
from pdf_processor import PDFProcessor,TOCExtractor, create_processor
from image_processor import ImageProcessor
from ocr_processor import OCRProcessor
from chapter_extractor import ChapterExtractor
from widgets_t1 import create_pdf_widgets
from widgets_t2 import create_image_widgets
from widgets_t3 import create_tab3_widgets, CitationManagerTab
from Flask import app as flask_app

# Configure logging
logger.add("logs/app_{time}.log",
        rotation="1 MB",
        level="DEBUG",
        format="{time} {level} {message}")


@dataclass
class AppConfig:
    """Application configuration settings."""
    window_title: str = "Advanced PDF & Image Processing Tool"
    window_size: tuple = (1200, 800)
    temp_dir: str = "temp"
    output_dir: str = "output"
    flask_port: int = 5000

    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.temp_dir, self.output_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)


class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass


class PDFReaderApp(tk.Tk):
    """
    Main application window integrating PDF processing, image processing,
    and citation management functionality.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize the application."""
        super().__init__()
        self.config = config or AppConfig()
        self.title(self.config.window_title)
        self.geometry(
            f"{self.config.window_size[0]}x{self.config.window_size[1]}")

        # Initialize state variables
        self.pdf_path: Optional[Path] = None
        self.pdf_proc: Optional[PDFProcessor] = None
        self.current_page: int = 0
        self.total_pages: int = 0

        # Initialize processors
        self.img_processor = ImageProcessor()
        self.ocr_processor = OCRProcessor()

        # Create UI
        self._create_notebook()
        self._create_status_bar()

        # Start Flask server
        self._start_flask_server()

        logger.info("Application initialized")

    def _create_notebook(self):
        """Create the tabbed interface."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create frames for each tab
        self.pdf_frame = ttk.Frame(self.notebook)
        self.image_frame = ttk.Frame(self.notebook)
        self.citation_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.pdf_frame, text="PDF Processor")
        self.notebook.add(self.image_frame, text="Image Processor")
        self.notebook.add(self.citation_frame, text="Citation Manager")

        # Initialize tab interfaces from external widget modules
        self.pdf_tab = create_pdf_widgets(self, self.pdf_frame)
        self.image_tab = create_image_widgets(self, self.image_frame)
        self.citation_tab = create_tab3_widgets(self, self.citation_frame)

        # Bind tab change event
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_change)

    def _create_status_bar(self):
        """Create the application status bar."""
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_bar,
                                      text="Ready",
                                      padding=(5, 2))
        self.status_label.pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.status_bar,
                                            length=200,
                                            mode='determinate',
                                            variable=self.progress_var)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)

    def _start_flask_server(self):
        """Start the Flask server in a separate thread."""

        def run_flask():
            try:
                flask_app.run(port=self.config.flask_port,
                              debug=False,
                              use_reloader=False)
            except Exception as e:
                logger.error(f"Flask server error: {e}")

        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        logger.info(f"Flask server started on port {self.config.flask_port}")

    def _on_tab_change(self, event):
        """Handle tab change events."""
        current_tab = self.notebook.select()
        tab_name = self.notebook.tab(current_tab, "text")
        logger.debug(f"Switched to tab: {tab_name}")

    # PDF Processing Methods
    def load_pdf(self) -> None:
        """Load a PDF and display the first two pages."""
        try:
            selected_path = filedialog.askopenfilename(
                filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")])
            if not selected_path:
                return

            # If a PDF is already loaded, ask for confirmation
            if self.pdf_path and self.pdf_proc:
                if not messagebox.askyesno(
                        "Confirm", "Close current PDF and load new one?"):
                    return

            self.pdf_path = Path(selected_path)
            self.status_label.config(text=f"Loading PDF: {self.pdf_path.name}")

            loader = PDFLoader(str(self.pdf_path))
            self.pdf_proc = loader.load()
            self.total_pages = self.pdf_proc.get_total_pages()
            self.current_page = 0

            self.status_label.config(text=f"Loaded PDF: {self.pdf_path.name}")
            self.show_pages()

            logger.info(f"Successfully loaded PDF: {self.pdf_path}")
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            messagebox.showerror("Error", f"Failed to load PDF: {e}")
            self.status_label.config(text="Failed to load PDF")

    def show_pages(self):
        """Display pages using the show_pages function from pdf_loader."""
        try:
            from pdf_loader import show_pages
            show_pages(self)
        except Exception as e:
            logger.error(f"Failed to display pages: {e}")

    def process_chapters(self) -> List[Dict[str, Any]]:
        """Process and extract chapters from the PDF."""
        try:
            if not self.pdf_proc:
                raise ProcessingError("No PDF loaded")

            self._update_status("Processing chapters...")
            self.progress_var.set(0)

            extractor = ChapterExtractor(str(self.pdf_path))
            chapters = extractor.process_chapters()

            self._update_status(f"Processed {len(chapters)} chapters")
            self.progress_var.set(100)
            return chapters
        except Exception as e:
            logger.error(f"Chapter processing failed: {e}")
            self._show_error("Chapter Processing Error", str(e))
            return []

    def extract_chapter_images(self, chapters: List[Dict[str,
                                                         Any]]) -> List[Path]:
        """Extract images from processed chapters."""
        try:
            if not chapters:
                raise ProcessingError("No chapters to process")

            self._update_status("Extracting chapter images...")
            self.progress_var.set(0)

            output_paths = []
            for i, chapter in enumerate(chapters):
                progress = ((i + 1) / len(chapters)) * 100
                self.progress_var.set(progress)
                try:
                    output_path = Path(
                        self.config.output_dir) / f"chapter_{i+1}.png"
                    extractor = ChapterExtractor(str(self.pdf_path))
                    extractor.extract(chapter["page_range"], output_path)
                    output_paths.append(output_path)
                except Exception as e:
                    logger.error(f"Failed to extract chapter {i+1}: {e}")
                    continue

            self._update_status(
                f"Extracted {len(output_paths)} chapter images")
            return output_paths
        except Exception as e:
            logger.error(f"Chapter image extraction failed: {e}")
            self._show_error("Image Extraction Error", str(e))
            return []

    # Image Processing Methods
    def process_image_paragraphs(self,
                                 image_path: Path) -> List[Dict[str, Any]]:
        """Process an image to extract paragraphs."""
        try:
            self._update_status("Processing paragraphs...")
            self.progress_var.set(0)

            image = Image.open(image_path)
            paragraphs = self.img_processor.detect_paragraphs_with_metadata(
                image, chapter=1, output_dir=self.config.output_dir)

            self._update_status(f"Extracted {len(paragraphs)} paragraphs")
            self.progress_var.set(100)
            return paragraphs
        except Exception as e:
            logger.error(f"Paragraph processing failed: {e}")
            self._show_error("Paragraph Processing Error", str(e))
            return []

    # Citation Processing Methods
    def process_citations(self, paragraph_data: Dict[str,
                                                    Any]) -> Dict[str, Any]:
        """Process a paragraph to extract citations."""
        try:
            self._update_status("Processing citations...")
            if 'image' not in paragraph_data:
                raise ProcessingError("No image data in paragraph")

            citations = self.ocr_processor.extract_citations_from_paragraph(
                paragraph_data['image'])
            self._update_status(
                f"Extracted {len(citations.get('quotes', []))} citations")
            return citations
        except Exception as e:
            logger.error(f"Citation processing failed: {e}")
            self._show_error("Citation Processing Error", str(e))
            return {}

    # Utility Methods
    def _update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.update_idletasks()
        logger.info(message)

    def _show_error(self, title: str, message: str):
        """Show error message dialog."""
        messagebox.showerror(title, message)
        self._update_status(f"Error: {message}")

    def on_closing(self):
        """Handle application closing."""
        try:
            self.save_application_state()
            # Clean up temporary files
            temp_dir = Path(self.config.temp_dir)
            if temp_dir.exists():
                for file in temp_dir.glob("*"):
                    try:
                        file.unlink()
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete temp file {file}: {e}")
            logger.info("Application closing")
            self.destroy()
        except Exception as e:
            logger.error(f"Error during application closure: {e}")
            self.destroy()

    def cleanup_temp_files(self):
        """Clean up temporary files created during processing."""
        try:
            temp_dir = Path(self.config.temp_dir)
            if temp_dir.exists():
                for file in temp_dir.glob("*"):
                    try:
                        file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete {file}: {e}")
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def save_application_state(self):
        """Save current application state for recovery."""
        try:
            state = {
                "pdf_path": str(self.pdf_path) if self.pdf_path else None,
                "current_page": self.current_page,
                "current_tab": self.notebook.select(),
                "image_processor_state": {
                    "current_image_index":
                    getattr(self.image_tab, 'current_image_index', 0),
                    "image_list": [
                        str(p)
                        for p in getattr(self.image_tab, 'image_list', [])
                    ]
                },
                "citation_manager_state": {
                    "current_citation_index":
                    getattr(self.citation_tab, 'current_index', 0)
                }
            }
            state_file = Path(self.config.temp_dir) / "app_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=4)
            logger.info("Saved application state")
        except Exception as e:
            logger.error(f"Failed to save application state: {e}")

    def load_application_state(self):
        """Restore previous application state."""
        try:
            state_file = Path(self.config.temp_dir) / "app_state.json"
            if not state_file.exists():
                return
            with open(state_file, 'r') as f:
                state = json.load(f)
            if state.get("pdf_path"):
                self.pdf_path = Path(state["pdf_path"])
                if self.pdf_path.exists():
                    self.load_pdf()
                    self.current_page = state["current_page"]
            if state.get("current_tab"):
                self.notebook.select(state["current_tab"])
            if hasattr(self, 'image_tab'):
                img_state = state.get("image_processor_state", {})
                if img_state.get("image_list"):
                    self.image_tab.image_list = [
                        Path(p) for p in img_state["image_list"]
                    ]
                    self.image_tab.current_index = img_state[
                        "current_image_index"]
                    if self.image_tab.image_list:
                        self.image_tab.load_image(self.image_tab.image_list[
                            self.image_tab.current_image_index])
            if hasattr(self, 'citation_tab'):
                cit_state = state.get("citation_manager_state", {})
                self.citation_tab.current_index = cit_state.get(
                    "current_citation_index", 0)
            logger.info("Restored application state")
        except Exception as e:
            logger.error(f"Failed to restore application state: {e}")

    def export_processing_results(self, output_path: Optional[Path] = None):
        """Export all processing results to a structured format."""
        try:
            if output_path is None:
                output_path = Path(
                    self.config.output_dir) / "processing_results.json"
            results = {
                "pdf_info": {
                    "path": str(self.pdf_path) if self.pdf_path else None,
                    "total_pages": self.total_pages,
                    "processed_date": datetime.datetime.now().isoformat()
                },
                "chapters":
                [ch.to_dict() for ch in getattr(self.pdf_tab, 'chapters', [])],
                "paragraphs": [
                    p.to_dict()
                    for p in getattr(self.image_tab, 'paragraphs', [])
                ],
                "citations": [
                    c.to_dict()
                    for c in getattr(self.citation_tab, 'citations', [])
                ]
            }
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=4)
            logger.info(f"Exported processing results to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            return False

    def generate_processing_report(self, output_path: Optional[Path] = None):
        """Generate a detailed processing report in HTML format."""
        try:
            if output_path is None:
                output_path = Path(
                    self.config.output_dir) / "processing_report.html"
            template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Processing Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .section { margin-bottom: 20px; }
                    .header { background-color: #f0f0f0; padding: 10px; }
                    .content { margin-left: 20px; }
                </style>
            </head>
            <body>
                <h1>Processing Report</h1>
                <div class="section">
                    <div class="header">PDF Information</div>
                    <div class="content">
                        <p>File: {pdf_path}</p>
                        <p>Pages: {total_pages}</p>
                        <p>Processed: {processed_date}</p>
                    </div>
                </div>
                <div class="section">
                    <div class="header">Chapters Detected: {chapter_count}</div>
                    <div class="content">
                        {chapter_list}
                    </div>
                </div>
                <div class="section">
                    <div class="header">Paragraphs Extracted: {paragraph_count}</div>
                    <div class="content">
                        {paragraph_list}
                    </div>
                </div>
                <div class="section">
                    <div class="header">Citations Found: {citation_count}</div>
                    <div class="content">
                        {citation_list}
                    </div>
                </div>
            </body>
            </html>
            """
            chapters = getattr(self.pdf_tab, 'chapters', [])
            paragraphs = getattr(self.image_tab, 'paragraphs', [])
            citations = getattr(self.citation_tab, 'citations', [])
            chapter_list = "<ul>" + "".join(
                f"<li>{ch.title} (Pages {ch.page_range.start+1}-{ch.page_range.stop})</li>"
                for ch in chapters) + "</ul>"
            paragraph_list = "<ul>" + "".join(
                f"<li>Paragraph {idx+1}: {len(p.text)} characters</li>"
                for idx, p in enumerate(paragraphs)) + "</ul>"
            citation_list = "<ul>" + "".join(f"<li>{c.text[:100]}...</li>"
                                             for c in citations) + "</ul>"
            report_html = template.format(
                pdf_path=self.pdf_path or "No PDF loaded",
                total_pages=self.total_pages,
                processed_date=datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"),
                chapter_count=len(chapters),
                chapter_list=chapter_list,
                paragraph_count=len(paragraphs),
                paragraph_list=paragraph_list,
                citation_count=len(citations),
                citation_list=citation_list)
            with open(output_path, 'w') as f:
                f.write(report_html)
            logger.info(f"Generated processing report at {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return False


def main():
    """Application entry point."""
    try:
        config = AppConfig()
        app = PDFReaderApp(config)
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        state_file = Path(app.config.temp_dir) / "app_state.json"
        if state_file.exists():
            try:
                app.load_application_state()
            except Exception as e:
                logger.warning(f"Failed to load previous state: {e}")
        app.mainloop()
    except Exception as e:
        logger.exception("Application failed to start")
        messagebox.showerror("Startup Error",
                             f"Application failed to start: {e}")


if __name__ == "__main__":
    main()
