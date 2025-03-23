#!/usr/bin/env python3
"""
image_processor.py

This module defines the ImageProcessor class which:
- Loads an image.
- Optionally preprocesses the image.
- Uses LayoutParser to detect text blocks.
- Groups text blocks into paragraphs based on vertical proximity.
- Merges bounding boxes with a small margin.
- Uses pytesseract to perform OCR on each cropped paragraph region.
- Saves each paragraph image and returns metadata (text, bounding box, image, filename).
"""

import os
from PIL import Image
import numpy as np
import pytesseract
import layoutparser as lp
from typing import List, Tuple, Dict, Any
from layoutparser.elements.layout_elements import BaseLayoutElement
from loguru import logger

logger.add("image_processor.log", rotation="1 MB", level="DEBUG")


class ImageProcessor:
    def __init__(self, 
                grouping_threshold: int = 20, 
                ocr_lang: str = 'eng', 
                ocr_config: str = '--psm 6',
                layout_model: str = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config",
                label_map: Dict[int, str] = {0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
                ) -> None:
        """
        Initializes the ImageProcessor with customizable parameters for OCR and layout detection.

        Args:
            grouping_threshold (int): Vertical gap (pixels) to group text blocks.
            ocr_lang (str): Language for OCR (e.g., 'eng').
            ocr_config (str): Tesseract configuration string.
            layout_model (str): Path to the layout detection model.
            label_map (Dict[int, str]): Mapping of model output labels to names.
        """
        self.model = lp.Detectron2LayoutModel(
            layout_model, 
            extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5],
            label_map=label_map
        )
        self.grouping_threshold = grouping_threshold
        self.ocr_lang = ocr_lang
        self.ocr_config = ocr_config

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Applies preprocessing to enhance image quality before OCR.

        Args:
            image (Image.Image): Input PIL Image.

        Returns:
            Image.Image: Preprocessed image.
        """
        # Convert to grayscale
        image = image.convert("L")
        # Apply thresholding to reduce noise
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        return image

    def _perform_ocr(self, image: Image.Image) -> str:
        """
        Performs OCR on the given image using Tesseract.

        Args:
            image (Image.Image): Input PIL Image.

        Returns:
            str: Extracted text.
        """
        image = self._preprocess_image(image)
        text = pytesseract.image_to_string(image, lang=self.ocr_lang, config=self.ocr_config)
        return text.strip()

    def _group_text_blocks(self, text_blocks: List[BaseLayoutElement]) -> List[List[BaseLayoutElement]]:
        """
        Groups text blocks into paragraphs based on vertical proximity.

        Args:
            text_blocks (List[BaseLayoutElement]): List of detected text blocks.

        Returns:
            List[List[BaseLayoutElement]]: List of grouped text blocks.
        """
        text_blocks.sort(key=lambda b: b.coordinates[1])
        groups = []
        current_group = []

        for block in text_blocks:
            if not current_group:
                current_group.append(block)
            else:
                prev_block = current_group[-1]
                gap = block.coordinates[1] - prev_block.coordinates[3]
                if gap < self.grouping_threshold:
                    current_group.append(block)
                else:
                    groups.append(current_group)
                    current_group = [block]

        if current_group:
            groups.append(current_group)

        return groups

    def _merge_block_coordinates(self, blocks: List[BaseLayoutElement], 
                                image: Image.Image, margin: int = 10) -> Tuple[int, int, int, int]:
        """
        Merges bounding boxes of text blocks and adds a margin.

        Args:
            blocks (List[BaseLayoutElement]): List of text blocks to merge.
            image (Image.Image): Original image (to get dimensions).
            margin (int): Margin to add around the merged box.

        Returns:
            Tuple[int, int, int, int]: Merged bounding box coordinates (x1, y1, x2, y2).
        """
        xs = []
        ys = []
        for block in blocks:
            x1, y1, x2, y2 = block.coordinates
            xs.extend([x1, x2])
            ys.extend([y1, y2])

        merged_box = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))

        # Apply margin
        x1 = max(0, merged_box[0] - margin)
        y1 = max(0, merged_box[1] - margin)
        x2 = min(image.width, merged_box[2] + margin)
        y2 = min(image.height, merged_box[3] + margin)

        return (x1, y1, x2, y2)

    def detect_paragraphs_with_metadata(self, image: Image.Image, 
                                        chapter: int = 1, 
                                        output_dir: str = "paragraphs") -> List[Dict[str, Any]]:
        """
        Detects paragraphs, extracts text, saves cropped paragraph images,
        and returns metadata including bounding boxes and filenames.

        Args:
            image (Image.Image): Input PIL Image.
            chapter (int): Chapter number for naming output files.
            output_dir (str): Directory to save cropped paragraph images.

        Returns:
            List[Dict[str, Any]]: List of dictionaries with extracted text, bounding box, image, filename.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        image_np = np.array(image)
        layout = self.model.detect(image_np)

        text_blocks = [b for b in layout if b.type == "Text"]
        grouped_blocks = self._group_text_blocks(text_blocks)

        paragraphs = []
        for idx, group in enumerate(grouped_blocks, start=1):
            bbox = self._merge_block_coordinates(group, image, margin=10)
            cropped_img = image.crop(bbox)
            paragraph_text = self._perform_ocr(cropped_img)

            filename = f"chapter{chapter}_paragraph_{idx}.png"
            output_path = os.path.join(output_dir, filename)
            cropped_img.save(output_path)

            paragraphs.append({
                "text": paragraph_text,
                "bbox": bbox,
                "image": cropped_img,
                "filename": filename
            })

        return paragraphs