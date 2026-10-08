import os
import uuid
import base64
from typing import List, Optional
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import (
    UPLOAD_DIR,
    PROCESSED_DIR,
    ALLOWED_EXTENSIONS,
    BACKEND_PORT,
    FRONTEND_PORT
)
from app.ocr.ocr_engine import ocr_engine
from app.services.field_mapper import field_mapper
from app.rules.rule_engine import ComplianceRuleEngine
from app.services.url_fetcher import URLFetcher
from app.services.pdf_converter import PDFConverter
from app.services.report_exporter import ReportExporter

app = FastAPI(
    title="Legal Metrology Compliance API (SIH26034)",
    description="Automated compliance verification of packaged commodities under Legal Metrology Rules, 2011 & Drugs Act",
    version="1.0.0"
)

# Enable CORS for frontend on port 5188 or other origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded & processed images statically
app.mount("/static/processed", StaticFiles(directory=str(PROCESSED_DIR)), name="processed_static")

compliance_engine = ComplianceRuleEngine()

class URLAnalyzeRequest(BaseModel):
    url: str
    product_type: str = "general"

class ExportPDFRequest(BaseModel):
    compliance_report: dict


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Legal Metrology Compliance API",
        "ocr_engine": "PP-OCRv4 ONNX",
        "backend_port": BACKEND_PORT,
        "frontend_port": FRONTEND_PORT
    }


@app.get("/api/rules/config")
def get_rules(product_type: str = "general"):
    return compliance_engine.get_rule_config(product_type)


@app.post("/api/analyze/upload")
async def analyze_upload(
    product_type: str = Form("general"),
    files: List[UploadFile] = File(...)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    session_id = str(uuid.uuid4())[:8]
    images_to_process: List[np.ndarray] = []
    original_filenames: List[str] = []

    for file in files:
        filename = file.filename or "upload.jpg"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        contents = await file.read()
        if ext == ".pdf":
            pdf_imgs = PDFConverter.extract_images_from_pdf(contents)
            if not pdf_imgs:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not extract any product label images from PDF '{filename}'."
                )
            images_to_process.extend(pdf_imgs)
            original_filenames.extend([f"{filename}_page_{i+1}" for i in range(len(pdf_imgs))])
        else:
            nparr = np.frombuffer(contents, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_img is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to decode image file '{filename}'."
                )
            images_to_process.append(cv_img)
            original_filenames.append(filename)

    if not images_to_process:
        raise HTTPException(status_code=400, detail="No valid images found to process.")

    return _process_images_pipeline(images_to_process, product_type, session_id, original_filenames)


@app.post("/api/analyze/url")
def analyze_url(req: URLAnalyzeRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    fetch_res = URLFetcher.fetch_image_from_url(req.url)
    if not fetch_res.get("success"):
        raise HTTPException(
            status_code=400,
            detail=fetch_res.get("error", "Failed to fetch image from the provided URL.")
        )

    images_to_process = fetch_res["images"]
    session_id = str(uuid.uuid4())[:8]
    source_names = [f"url_image_{i+1}.jpg" for i in range(len(images_to_process))]

    report = _process_images_pipeline(
        images_to_process,
        req.product_type,
        session_id,
        source_names
    )
    report["source_url"] = req.url
    report["page_title"] = fetch_res.get("page_title", "")
    return report


@app.post("/api/export/pdf")
def export_pdf(req: ExportPDFRequest):
    try:
        pdf_bytes = ReportExporter.generate_pdf_report(req.compliance_report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Legal_Metrology_Compliance_Report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")


# Serve frontend statically so it all runs on one port for cloud deployment
import pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
frontend_dir = BASE_DIR / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

def _process_images_pipeline(
    images: List[np.ndarray],
    product_type: str,
    session_id: str,
    filenames: List[str]
) -> dict:
    """Executes OCR, Field Mapping, and Compliance Engine across provided images."""
    ocr_blocks_by_image: List[List[dict]] = []
    processed_image_metadata = []
    all_extracted_text = []

    for idx, img in enumerate(images):
        # Run OCR with preprocessor
        ocr_out = ocr_engine.extract_text_and_boxes(img, image_index=idx)
        ocr_blocks_by_image.append(ocr_out["blocks"])
        all_extracted_text.append(ocr_out["full_text"])

        # Save enhanced display image for frontend
        saved_filename = f"{session_id}_img_{idx}.jpg"
        save_path = PROCESSED_DIR / saved_filename
        cv2.imwrite(str(save_path), ocr_out["display_image"])

        processed_image_metadata.append({
            "image_index": idx,
            "filename": filenames[idx] if idx < len(filenames) else f"image_{idx}.jpg",
            "url": f"/static/processed/{saved_filename}",
            "width": ocr_out["image_width"],
            "height": ocr_out["image_height"],
            "blocks_count": len(ocr_out["blocks"]),
            "ocr_blocks": ocr_out["blocks"]
        })

    # Step 2: Synonym-based NLP & Regex Field Mapping
    mapped_fields = field_mapper.map_extracted_fields(
        ocr_blocks_by_image=ocr_blocks_by_image,
        product_type=product_type
    )

    # Step 3: Run Dynamic Compliance Rule Engine
    full_text_combined = "\n---\n".join(all_extracted_text)
    compliance_report = compliance_engine.evaluate_compliance(
        product_type=product_type,
        mapped_fields=mapped_fields,
        full_extracted_text=full_text_combined
    )

    return {
        "session_id": session_id,
        "product_type": product_type,
        "processed_images": processed_image_metadata,
        "raw_extracted_text": full_text_combined,
        "compliance_report": compliance_report,
        "mapped_fields": mapped_fields
    }
