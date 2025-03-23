#!/usr/bin/env python3
"""
app_events.py

Handles application-level events and tab coordination.
"""

import os
from typing import Optional
from pathlib import Path
from loguru import logger
from PIL import Image

class AppEventHandler:
    """Coordinates events between application tabs."""
    
    def __init__(self, app):
        """Initialize with application instance."""
        self.app = app
        self._bind_events()
        
    def _bind_events(self):
        """Bind event handlers."""
        # Tab switching
        self.app.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
    def _on_tab_changed(self, event):
        """Handle tab change events."""
        current_tab = self.app.notebook.select()
        tab_id = self.app.notebook.index(current_tab)
        
        try:
            if tab_id == 1:  # Image Processing tab
                self._update_image_tab()
            elif tab_id == 2:  # Citation Management tab
                self._update_citation_tab()
                
        except Exception as e:
            logger.error(f"Tab change error: {e}")
            self.app.update_status(f"Error updating tab: {e}")
            
    def _update_image_tab(self):
        """Update Image Processing tab."""
        # Check if chapters were processed
        output_dir = self.app.config['paths']['output_dir']
        chapters_dir = os.path.join(output_dir, 'chapters')
        
        if os.path.exists(chapters_dir):
            self.app.image_tab.last_directory = chapters_dir
            self.app.update_status("Chapter images available for processing")
        else:
            self.app.update_status("No processed chapters found")
            
    def _update_citation_tab(self):
        """Update Citation Management tab."""
        # Check if paragraphs were processed
        output_dir = self.app.config['paths']['output_dir']
        paragraphs_dir = os.path.join(output_dir, 'paragraphs')
        
        if os.path.exists(paragraphs_dir):
            self.app.citation_tab.last_directory = paragraphs_dir
            self.app.update_status("Paragraphs available for citation extraction")
        else:
            self.app.update_status("No processed paragraphs found")
            
    def handle_chapter_extraction(self, chapter_data):
        """Handle chapter extraction completion."""
        try:
            # Update image tab
            if hasattr(self.app.image_tab, 'refresh_chapter_list'):
                self.app.image_tab.refresh_chapter_list()
                
            # Update status
            self.app.update_status(f"Extracted {len(chapter_data)} chapters")
            
        except Exception as e:
            logger.error(f"Chapter extraction handling error: {e}")
            self.app.update_status("Error handling chapter extraction")
            
    def handle_paragraph_extraction(self, paragraph_data):
        """Handle paragraph extraction completion."""
        try:
            # Update citation tab
            if hasattr(self.app.citation_tab, 'refresh_paragraph_list'):
                self.app.citation_tab.refresh_paragraph_list()
                
            # Update status
            self.app.update_status(f"Extracted {len(paragraph_data)} paragraphs")
            
        except Exception as e:
            logger.error(f"Paragraph extraction handling error: {e}")
            self.app.update_status("Error handling paragraph extraction")
    
    def handle_citation_export(self, export_path: Path):
        """Handle citation export completion."""
        try:
            if export_path.exists():
                self.app.update_status(f"Citations exported to {export_path}")
            else:
                raise FileNotFoundError("Export file not found")
                
        except Exception as e:
            logger.error(f"Citation export handling error: {e}")
            self.app.update_status("Error handling citation export")

    def get_current_chapter_image(self) -> Optional[Image.Image]:
        """Get current chapter image if available."""
        try:
            if hasattr(self.app.image_tab, 'current_image'):
                return self.app.image_tab.current_image
            return None
            
        except Exception as e:
            logger.error(f"Error getting chapter image: {e}")
            return None
