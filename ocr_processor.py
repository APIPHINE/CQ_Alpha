#!/usr/bin/env python3
"""
ocr_processor.py

Encapsulates OCR functionalities including text extraction and citation extraction.
"""

import os
from PIL import Image
import pytesseract
try:
    import tesserocr
except ImportError:
    tesserocr = None
import numpy as np
import re
from loguru import logger
from typing import Optional, List, Tuple, Dict, Any

logger.add("ocr_processor.log", rotation="1 MB", level="DEBUG")

class OCRProcessor:
    """
    Encapsulates OCR functionalities, including text extraction and paragraph detection via bounding boxes.
    """
    def __init__(self, tesseract_cmd: Optional[str] = None) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def ocr_page_as_text(self, pil_image: Image.Image) -> str:
        """
        Extracts text from a PIL image using Tesseract.
        
        Args:
            pil_image (Image.Image): The image to process.
        
        Returns:
            str: The extracted text.
        """
        return pytesseract.image_to_string(pil_image)

    def extract_headings(self, image_path: str) -> List[str]:
        """
        Extract headings from an image using OCR by detecting bold or large fonts.
        
        Args:
            image_path (str): Path to the input image.
        
        Returns:
            List[str]: A list of extracted headings.
        """
        pil_img = Image.open(image_path)
        img_cv = np.array(pil_img)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

        headings = []
        for i, conf in enumerate(data['conf']):
            if int(conf) > 80 and data['text'][i].strip():  # High-confidence text
                if int(data['height'][i]) > 20:  # Larger text suggests a heading
                    headings.append(data['text'][i].strip())
                    logger.info(f"Detected heading: {data['text'][i]}")
        
        return headings

    def extract_paragraphs(self, image_path: str, output_dir: str = "image_paragraphs", margin: int = 10) -> List[str]:
        """
        Extract paragraphs from an image using OCR and save each paragraph as an image file.
        A margin is applied around each detected paragraph.
        
        Args:
            image_path (str): Path to the input image.
            output_dir (str): Directory to save the paragraph images.
            margin (int): Margin in pixels to add around each paragraph.
        
        Returns:
            List[str]: A list of extracted paragraph texts.
        """
        os.makedirs(output_dir, exist_ok=True)
        pil_img = Image.open(image_path)
        img_cv = np.array(pil_img)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

        paragraphs_boxes = {}
        for i, level in enumerate(data["level"]):
            txt = data["text"][i].strip()
            if not txt:
                continue
            p_num = data["par_num"][i]
            x, y = data["left"][i], data["top"][i]
            w, h = data["width"][i], data["height"][i]
            if p_num not in paragraphs_boxes:
                paragraphs_boxes[p_num] = {
                    "x1": x,
                    "y1": y,
                    "x2": x + w,
                    "y2": y + h,
                    "text": txt,
                }
            else:
                paragraphs_boxes[p_num]["x1"] = min(paragraphs_boxes[p_num]["x1"], x)
                paragraphs_boxes[p_num]["y1"] = min(paragraphs_boxes[p_num]["y1"], y)
                paragraphs_boxes[p_num]["x2"] = max(paragraphs_boxes[p_num]["x2"], x + w)
                paragraphs_boxes[p_num]["y2"] = max(paragraphs_boxes[p_num]["y2"], y + h)
                paragraphs_boxes[p_num]["text"] += " " + txt

        paragraph_texts: List[str] = []
        sorted_pnums = sorted(paragraphs_boxes.keys())
        for idx, p_num in enumerate(sorted_pnums, start=1):
            bbox = paragraphs_boxes[p_num]
            x1, y1, x2, y2 = self._apply_margin(bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"], img_cv, margin)
            logger.info(f"Paragraph {p_num}: Original bbox {bbox}, Adjusted bbox: {(x1, y1, x2, y2)}")
            cropped = img_cv[y1:y2, x1:x2]
            crop_img = Image.fromarray(cropped)
            filename = f"paragraph_{idx}.png"
            crop_img.save(os.path.join(output_dir, filename))
            paragraph_texts.append(bbox["text"])

        return paragraph_texts

    def _apply_margin(self, x1: int, y1: int, x2: int, y2: int, img_cv: np.ndarray, margin: int) -> Tuple[int, int, int, int]:
        """
        Apply a margin to the bounding box coordinates, ensuring they stay within image boundaries.
        
        Args:
            x1, y1, x2, y2 (int): Original bounding box coordinates.
            img_cv (np.ndarray): The image array.
            margin (int): Margin in pixels to add.
        
        Returns:
            Tuple[int, int, int, int]: The adjusted bounding box coordinates.
        """
        new_x1 = max(0, x1 - margin)
        new_y1 = max(0, y1 - margin)
        new_x2 = min(img_cv.shape[1], x2 + margin)
        new_y2 = min(img_cv.shape[0], y2 + margin)
        return new_x1, new_y1, new_x2, new_y2

def extract_citations_from_paragraph(paragraph_image: Image.Image) -> dict:
    """
    Runs OCR on the given paragraph image and extracts key quotations.
    Returns a dictionary with the full text, any detected quotes, a context placeholder, and an OCR confidence value.
    """
    # Extract full text from the image using Tesseract
    text = pytesseract.image_to_string(paragraph_image)
    # Use a simple regex to capture any text within double quotes as quotes
    pattern = r'"([^"]+)"'
    found_quotes = re.findall(pattern, text)
    quotes_list = [{"quote_text": q, "confidence": 0.9} for q in found_quotes]

    result = {
        "full_text": text,
        "quotes": quotes_list,
        "context": "",
        "ocr_confidence": 0.95
    }
    return result