# Legal Metrology (Packaged Commodities) Compliance Checker - SIH26034

Automated software system for scanning product packaging labels, images, and e-commerce URLs to verify compliance under the **Legal Metrology (Packaged Commodities) Rules, 2011** and **Drugs and Cosmetics Rules, 1945**.

---

## 🌟 Key Capabilities

1. **Dual Input Methods**:
   - **Multi-Image & PDF Upload**: Upload multiple photos (front, back, MRP sticker) or multi-page label PDFs.
   - **Server-Side URL Fetcher**: Safe image fetching from direct image URLs or e-commerce listing pages (Amazon, Flipkart, Blinkit, etc.) with SSRF protection and content-type validation.
   - **Zero Hardcoding**: Every compliance score and validation is dynamically extracted from the active session's image.

2. **Dual Regulatory Framework Toggle**:
   - **General Packaged Commodities**: Rule 6 mandatory declarations (Net Quantity with SI units, MRP inclusive of all taxes, Manufacturer/Packer name & address, Consumer Helpline/Email, Month & Year of Mfg/Packing, Country of Origin).
   - **Medicine / Pharmaceutical**: General declarations plus Drugs & Cosmetics Act mandatory fields (Batch Number `B.No.`, Manufacturing License `Mfg. Lic. No.`, Expiry Date, Active Composition, Storage Conditions, Schedule Drug / Rx classification).

3. **Preprocessing & OCR Pipeline**:
   - Automated skew angle correction (deskew).
   - CLAHE (Contrast Limited Adaptive Histogram Equalization) on luminance channel for glossy/glare packaging.
   - Edge-preserving bilateral denoising & sharpening.
   - **PP-OCRv4 ONNX / PaddleOCR** recognition with polygon coordinates, normalized bounding boxes, and per-token confidence scores.

4. **Extensible JSON Synonym Mapping & NLP**:
   - Configurable synonym dictionary (`synonyms.json`) supporting diverse industrial abbreviations (`Net Wt.`, `Net Vol.`, `Mfd. By`, `Pkd By`, `B.No.`, `Lic. No.`, `Exp.`, `Rx only`).
   - Fuzzy string matching via **RapidFuzz** to handle crumpled packaging OCR typos and abbreviations.
   - Spatial proximity pairing to bind label headers to adjacent value blocks.

5. **Compliance Rule Engine & Scorecard**:
   - Field format validators (SI metric symbols, rupee format, date validity, chronological expiry check).
   - Distinguishes between **Missing Declarations** vs **Low-Confidence OCR Readings**.
   - Generates official **PDF Audit Reports** and structured **JSON Export**.

6. **Interactive Dashboard**:
   - SVG Bounding Box overlay viewer with hover inspection and coordinate tracking.
   - Distinct ports: Backend on `http://localhost:8088` and Frontend on `http://localhost:5188`.

---

## 🚀 Quick Start

### 1. Launch Servers
Run the unified launcher:
```bash
python start_servers.py
```

Or start them individually:
```bash
# Terminal 1: Backend API (Port 8088)
python backend/run_backend.py

# Terminal 2: Frontend Dashboard (Port 5188)
python frontend/serve_frontend.py
```

### 2. Access the Application
- **Frontend Dashboard**: [http://localhost:5188](http://localhost:5188)
- **Backend API & Swagger Docs**: [http://localhost:8088/docs](http://localhost:8088/docs)

---

## 📁 Project Architecture

```
legal_metrology_compliance/
├── backend/
│   ├── app/
│   │   ├── config.py                   # Port settings, file limits, confidence thresholds
│   │   ├── main.py                     # FastAPI server with CORS & endpoints
│   │   ├── rules/
│   │   │   ├── synonyms.json           # Extensible JSON rules & synonyms config
│   │   │   ├── validators.py           # SI unit, MRP, Date, Address, & Pharma validators
│   │   │   └── rule_engine.py          # Dynamic Legal Metrology verification engine
│   │   ├── ocr/
│   │   │   ├── preprocessor.py         # Deskew, CLAHE contrast boost, noise reduction
│   │   │   └── ocr_engine.py           # PP-OCRv4 extraction & bounding boxes
│   │   └── services/
│   │       ├── url_fetcher.py          # Safe HTTP fetcher for direct images and web pages
│   │       ├── field_mapper.py         # NLP + RapidFuzz synonym mapper
│   │       ├── pdf_converter.py        # PDF page extraction service
│   │       └── report_exporter.py      # PDF / JSON audit report exporter
│   └── run_backend.py                  # Backend server entrypoint (:8088)
├── frontend/
│   ├── index.html                      # Interactive dashboard UI
│   ├── css/
│   │   └── styles.css                  # Bounding box overlays, glassmorphism, responsive styles
│   ├── js/
│   │   └── app.js                      # UI logic, SVG overlays, API integration
│   └── serve_frontend.py              # Frontend server entrypoint (:5188)
├── tests/
│   └── test_compliance.py             # Automated unit & integration tests
├── start_servers.py                    # Dual-server concurrent runner
└── README.md
```

---

## 🧪 Running Automated Tests

```bash
python tests/test_compliance.py
```
All unit tests verify:
- SI unit compliance & Legal Metrology Rule 11 standard symbol rules
- MRP formatting & "inclusive of all taxes" detection
- Date parsing & Chronological expiry check
- Manufacturer address & Consumer Helpline format verification
- PP-OCRv4 text detection and bounding box extraction
- PDF Report generation
