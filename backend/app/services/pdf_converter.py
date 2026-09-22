import io
from typing import List
import cv2
import numpy as np
from pypdf import PdfReader
from PIL import Image

class PDFConverter:
    @staticmethod
    def extract_images_from_pdf(pdf_bytes: bytes) -> List[np.ndarray]:
        """
        Extracts embedded images from a PDF file.
        Returns a list of BGR OpenCV images.
        """
        images: List[np.ndarray] = []
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                for img_obj in page.images:
                    try:
                        pil_img = Image.open(io.BytesIO(img_obj.data)).convert("RGB")
                        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        if cv_img.shape[0] >= 100 and cv_img.shape[1] >= 100:
                            images.append(cv_img)
                    except Exception:
                        continue
        except Exception:
            pass
        return images
