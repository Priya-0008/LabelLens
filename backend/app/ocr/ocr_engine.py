import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from rapidocr_onnxruntime import RapidOCR
from app.config import OCR_CONFIDENCE_THRESHOLD
from app.ocr.preprocessor import ImagePreprocessor

class OCREngine:
    def __init__(self):
        # Initialize RapidOCR with PP-OCRv4 ONNX model
        self.engine = RapidOCR()

    def extract_text_and_boxes(
        self,
        image_bgr: np.ndarray,
        image_index: int = 0
    ) -> Dict[str, Any]:
        """
        Preprocesses image and runs PP-OCRv4 OCR detection and recognition.
        Returns:
            - blocks: list of detected text items with bboxes and confidence
            - full_text: concatenated recognized text
            - display_image: enhanced BGR image
        """
        display_img, ocr_img = ImagePreprocessor.preprocess_pipeline(image_bgr)
        h, w = display_img.shape[:2]

        # Run OCR
        ocr_result, elapse = self.engine(ocr_img)

        blocks: List[Dict[str, Any]] = []
        full_text_lines: List[str] = []

        if ocr_result:
            for item in ocr_result:
                # item structure: [box_points, text, confidence]
                box_pts, text, score = item
                text_clean = str(text).strip()
                score_val = float(score) if score is not None else 0.0

                if not text_clean:
                    continue

                # Ensure box points are standard [[x, y], ...]
                raw_box = [[float(pt[0]), float(pt[1])] for pt in box_pts]
                
                # Compute Axis-Aligned Bounding Box (AABB) for convenience
                xs = [pt[0] for pt in raw_box]
                ys = [pt[1] for pt in raw_box]
                min_x, max_x = max(0.0, min(xs)), min(float(w), max(xs))
                min_y, max_y = max(0.0, min(ys)), min(float(h), max(ys))

                # Normalized coordinates (0.0 to 1.0) for frontend canvas
                norm_box = {
                    "x": round(min_x / w, 4),
                    "y": round(min_y / h, 4),
                    "width": round((max_x - min_x) / w, 4),
                    "height": round((max_y - min_y) / h, 4)
                }

                is_low_conf = score_val < OCR_CONFIDENCE_THRESHOLD

                block_dict = {
                    "text": text_clean,
                    "confidence": round(score_val, 3),
                    "is_low_confidence": is_low_conf,
                    "polygon": raw_box,
                    "bbox_norm": norm_box,
                    "bbox_pixels": {
                        "x": int(min_x),
                        "y": int(min_y),
                        "width": int(max_x - min_x),
                        "height": int(max_y - min_y)
                    },
                    "image_index": image_index,
                    "image_width": w,
                    "image_height": h
                }

                blocks.append(block_dict)
                full_text_lines.append(text_clean)

        return {
            "blocks": blocks,
            "full_text": "\n".join(full_text_lines),
            "image_width": w,
            "image_height": h,
            "display_image": display_img
        }

# Global singleton OCR engine instance
ocr_engine = OCREngine()
