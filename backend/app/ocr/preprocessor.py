import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional

class ImagePreprocessor:
    @staticmethod
    def deskew_image(cv_img: np.ndarray) -> np.ndarray:
        """Corrects slight skew angles (-45 to 45 deg) using minAreaRect on text contours."""
        try:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img
            # Invert colors (text as foreground)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            
            # Find coordinates of all foreground pixels
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return cv_img
                
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = -(angle - 90)
            else:
                angle = -angle
                
            # Only correct if skew is noticeable but not 90 deg rotation
            if abs(angle) > 0.8 and abs(angle) < 40:
                (h, w) = cv_img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    cv_img, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated
        except Exception:
            pass
        return cv_img

    @staticmethod
    def enhance_contrast_clahe(cv_img: np.ndarray) -> np.ndarray:
        """Applies CLAHE on luminance channel to fix glare and shadows on glossy packaging."""
        try:
            if len(cv_img.shape) == 3:
                # Convert to LAB color space
                lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
                l_channel, a_channel, b_channel = cv2.split(lab)
                
                # Apply CLAHE to L channel
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                cl = clahe.apply(l_channel)
                
                # Merge back
                merged = cv2.merge((cl, a_channel, b_channel))
                return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
            else:
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                return clahe.apply(cv_img)
        except Exception:
            return cv_img

    @staticmethod
    def remove_noise(cv_img: np.ndarray) -> np.ndarray:
        """Applies bilateral filter to smooth noise while preserving crisp text edges."""
        try:
            return cv2.bilateralFilter(cv_img, d=7, sigmaColor=50, sigmaSpace=50)
        except Exception:
            return cv_img

    @staticmethod
    def sharpen_text(cv_img: np.ndarray) -> np.ndarray:
        """Applies unsharp masking to enhance fine small-print details."""
        try:
            gaussian = cv2.GaussianBlur(cv_img, (0, 0), 2.0)
            unsharp = cv2.addWeighted(cv_img, 1.5, gaussian, -0.5, 0)
            return unsharp
        except Exception:
            return cv_img

    @classmethod
    def preprocess_pipeline(cls, image_input: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Runs the full preprocessing pipeline.
        Returns:
            - enhanced_display_bgr: Enhanced image ready for web visualization
            - ocr_ready_img: Fully processed image for OCR recognition
        """
        # Ensure BGR
        if len(image_input.shape) == 2:
            bgr = cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
        else:
            bgr = image_input.copy()

        # Step 1: Deskew / Rotation correction
        deskewed = cls.deskew_image(bgr)

        # Step 2: CLAHE Contrast enhancement
        contrast_enhanced = cls.enhance_contrast_clahe(deskewed)

        # Step 3: Noise reduction preserving edges
        denoised = cls.remove_noise(contrast_enhanced)

        # Step 4: Sharpening for OCR
        sharpened = cls.sharpen_text(denoised)

        return contrast_enhanced, sharpened
