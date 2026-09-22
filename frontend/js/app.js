// Legal Metrology Compliance App (SIH26034)
const API_BASE = "http://localhost:8088";

// App State
const state = {
  productType: "general",
  inputMode: "upload", // "upload" | "url"
  selectedFiles: [],
  currentAnalysis: null,
  activeImageIndex: 0,
  activeFilter: "all",
  activeHighlightId: null
};

// DOM Elements
const elements = {
  productTypeRadios: document.querySelectorAll('input[name="productType"]'),
  mandatoryPillsContainer: document.getElementById('mandatoryPillsContainer'),
  checklistCountBadge: document.getElementById('checklistCountBadge'),
  
  tabUploadBtn: document.getElementById('tabUploadBtn'),
  tabUrlBtn: document.getElementById('tabUrlBtn'),
  panelUpload: document.getElementById('panelUpload'),
  panelUrl: document.getElementById('panelUrl'),
  
  dropzone: document.getElementById('dropzone'),
  fileInput: document.getElementById('fileInput'),
  selectedFilesPreview: document.getElementById('selectedFilesPreview'),
  selectedCountText: document.getElementById('selectedCountText'),
  clearFilesBtn: document.getElementById('clearFilesBtn'),
  thumbnailContainer: document.getElementById('thumbnailContainer'),
  
  urlInput: document.getElementById('urlInput'),
  runAnalysisBtn: document.getElementById('runAnalysisBtn'),
  errorAlert: document.getElementById('errorAlert'),
  errorTitle: document.getElementById('errorTitle'),
  errorMessage: document.getElementById('errorMessage'),
  
  loadingSection: document.getElementById('loadingSection'),
  resultsSection: document.getElementById('resultsSection'),
  
  overallStatusHeading: document.getElementById('overallStatusHeading'),
  statusSummaryText: document.getElementById('statusSummaryText'),
  scorePercentText: document.getElementById('scorePercentText'),
  scoreCirclePath: document.getElementById('scoreCirclePath'),
  
  metricTotalMandatory: document.getElementById('metricTotalMandatory'),
  metricPassed: document.getElementById('metricPassed'),
  metricFailed: document.getElementById('metricFailed'),
  metricUnreadable: document.getElementById('metricUnreadable'),
  
  imageTabsContainer: document.getElementById('imageTabsContainer'),
  displayPackagingImg: document.getElementById('displayPackagingImg'),
  bboxSvgOverlay: document.getElementById('bboxSvgOverlay'),
  
  inspectorEmptyState: document.getElementById('inspectorEmptyState'),
  inspectorDetails: document.getElementById('inspectorDetails'),
  inspFieldName: document.getElementById('inspFieldName'),
  inspExtractedVal: document.getElementById('inspExtractedVal'),
  inspSynonym: document.getElementById('inspSynonym'),
  inspConfidence: document.getElementById('inspConfidence'),
  inspLegalRule: document.getElementById('inspLegalRule'),
  inspValidationMsg: document.getElementById('inspValidationMsg'),
  
  toggleRawOcrBtn: document.getElementById('toggleRawOcrBtn'),
  rawOcrChevron: document.getElementById('rawOcrChevron'),
  rawOcrContainer: document.getElementById('rawOcrContainer'),
  rawOcrTextarea: document.getElementById('rawOcrTextarea'),
  
  fieldCardsContainer: document.getElementById('fieldCardsContainer'),
  filterBtns: document.querySelectorAll('.filter-btn'),
  
  downloadPdfBtn: document.getElementById('downloadPdfBtn'),
  downloadJsonBtn: document.getElementById('downloadJsonBtn'),
  jumpToResultsBtn: document.getElementById('jumpToResultsBtn')
};

// Checklist definitions for UI quick preview
const CHECKLIST_SPECS = {
  general: [
    "Net Quantity (SI units)",
    "MRP (incl. of all taxes)",
    "Mfd / Pkd Date",
    "Manufacturer / Packer Address",
    "Consumer Helpline / Email",
    "Country of Origin"
  ],
  medicine: [
    "Net Quantity / Units",
    "MRP (incl. of all taxes)",
    "Batch Number (B.No.)",
    "Mfg License No. (M.L.)",
    "Mfg & Expiry Dates",
    "Active Composition",
    "Storage Conditions",
    "Schedule Drug Warning / Rx"
  ]
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  updateProductTypeUI();
  setupEventListeners();
  checkBackendHealth();
});

// Event Listeners
function setupEventListeners() {
  // Product Type Change
  elements.productTypeRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      state.productType = e.target.value;
      updateProductTypeUI();
      
      // Update visual selection borders
      document.querySelectorAll('.product-type-card').forEach(card => {
        const input = card.querySelector('input');
        if (input.checked) {
          card.classList.add('border-indigo-500/40', 'bg-indigo-500/10');
          card.classList.remove('border-slate-800', 'bg-slate-900');
        } else {
          card.classList.remove('border-indigo-500/40', 'bg-indigo-500/10');
          card.classList.add('border-slate-800', 'bg-slate-900');
        }
      });
    });
  });

  // Tab Switching (Upload vs URL)
  elements.tabUploadBtn.addEventListener('click', () => switchInputTab('upload'));
  elements.tabUrlBtn.addEventListener('click', () => switchInputTab('url'));

  // Drag & Drop
  elements.dropzone.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', handleFileSelect);

  ['dragenter', 'dragover'].forEach(name => {
    elements.dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      elements.dropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    elements.dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      elements.dropzone.classList.remove('drag-over');
    });
  });

  elements.dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt.files && dt.files.length > 0) {
      addFiles(Array.from(dt.files));
    }
  });

  elements.clearFilesBtn.addEventListener('click', clearFiles);

  // Analysis Button
  elements.runAnalysisBtn.addEventListener('click', executeAnalysis);

  // Raw OCR Toggle
  elements.toggleRawOcrBtn.addEventListener('click', () => {
    const isHidden = elements.rawOcrContainer.classList.contains('hidden');
    elements.rawOcrContainer.classList.toggle('hidden', !isHidden);
    elements.rawOcrChevron.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
  });

  // Filter Buttons
  elements.filterBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      elements.filterBtns.forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white');
        b.classList.add('bg-slate-800', 'text-slate-400');
      });
      btn.classList.add('bg-indigo-600', 'text-white');
      btn.classList.remove('bg-slate-800', 'text-slate-400');
      
      state.activeFilter = btn.getAttribute('data-filter');
      renderFieldCards();
    });
  });

  // Export Buttons
  elements.downloadPdfBtn.addEventListener('click', downloadPdfReport);
  elements.downloadJsonBtn.addEventListener('click', downloadJsonReport);

  // Window resize to update SVG bounding box overlay
  window.addEventListener('resize', () => {
    if (state.currentAnalysis) {
      renderBoundingBoxes();
    }
  });
}

function updateProductTypeUI() {
  const items = CHECKLIST_SPECS[state.productType] || CHECKLIST_SPECS.general;
  elements.checklistCountBadge.textContent = `${items.length} mandatory declarations`;
  
  elements.mandatoryPillsContainer.innerHTML = items.map(item => `
    <span class="px-2 py-1 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60 font-medium">
      &bull; ${item}
    </span>
  `).join('');
}

function switchInputTab(mode) {
  state.inputMode = mode;
  hideError();

  if (mode === 'upload') {
    elements.tabUploadBtn.className = "px-3.5 py-1.5 rounded-lg bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5";
    elements.tabUrlBtn.className = "px-3.5 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 transition-all flex items-center space-x-1.5";
    elements.panelUpload.classList.remove('hidden');
    elements.panelUrl.classList.add('hidden');
  } else {
    elements.tabUrlBtn.className = "px-3.5 py-1.5 rounded-lg bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5";
    elements.tabUploadBtn.className = "px-3.5 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 transition-all flex items-center space-x-1.5";
    elements.panelUrl.classList.remove('hidden');
    elements.panelUpload.classList.add('hidden');
  }
  lucide.createIcons();
}

function handleFileSelect(e) {
  if (e.target.files && e.target.files.length > 0) {
    addFiles(Array.from(e.target.files));
  }
}

function addFiles(newFiles) {
  state.selectedFiles = [...state.selectedFiles, ...newFiles];
  renderSelectedFilesPreview();
}

function clearFiles() {
  state.selectedFiles = [];
  elements.fileInput.value = "";
  renderSelectedFilesPreview();
}

function removeFile(index) {
  state.selectedFiles.splice(index, 1);
  renderSelectedFilesPreview();
}

function renderSelectedFilesPreview() {
  if (state.selectedFiles.length === 0) {
    elements.selectedFilesPreview.classList.add('hidden');
    return;
  }

  elements.selectedFilesPreview.classList.remove('hidden');
  elements.selectedCountText.textContent = `Selected ${state.selectedFiles.length} file(s)`;

  elements.thumbnailContainer.innerHTML = state.selectedFiles.map((file, idx) => {
    const isPdf = file.type === "application/pdf" || file.name.endsWith(".pdf");
    const previewSrc = isPdf ? "" : URL.createObjectURL(file);

    return `
      <div class="relative group rounded-xl border border-slate-800 bg-slate-950 p-2 flex flex-col items-center space-y-1">
        ${isPdf ? `
          <div class="w-full h-24 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
            <i data-lucide="file-text" class="w-8 h-8"></i>
          </div>
        ` : `
          <img src="${previewSrc}" class="w-full h-24 object-cover rounded-lg">
        `}
        <span class="text-[11px] text-slate-300 truncate w-full text-center font-mono">${file.name}</span>
        <button onclick="removeFile(${idx})" class="absolute top-1 right-1 w-6 h-6 rounded-full bg-slate-900/90 text-rose-400 hover:bg-rose-500 hover:text-white flex items-center justify-center opacity-80 group-hover:opacity-100 transition-all">
          &times;
        </button>
      </div>
    `;
  }).join('');

  lucide.createIcons();
}

window.removeFile = removeFile;

function setSampleUrl(url, productType = 'general') {
  elements.urlInput.value = url;
  
  // Set product type radio
  const targetRadio = document.querySelector(`input[name="productType"][value="${productType}"]`);
  if (targetRadio) {
    targetRadio.checked = true;
    targetRadio.dispatchEvent(new Event('change'));
  }
}

window.setSampleUrl = setSampleUrl;

// Backend Health Check
async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      document.getElementById('backendStatusBadge').innerHTML = `
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="font-medium text-emerald-400">PP-OCRv4 Active (:8088)</span>
      `;
    }
  } catch (err) {
    document.getElementById('backendStatusBadge').innerHTML = `
      <span class="w-2 h-2 rounded-full bg-amber-400"></span>
      <span class="font-medium text-amber-300">Connecting...</span>
    `;
  }
}

// Error handling
function showError(title, msg) {
  elements.errorTitle.textContent = title;
  elements.errorMessage.textContent = msg;
  elements.errorAlert.classList.remove('hidden');
}

function hideError() {
  elements.errorAlert.classList.add('hidden');
}

// Analysis Execution
async function executeAnalysis() {
  hideError();

  if (state.inputMode === 'upload' && state.selectedFiles.length === 0) {
    showError("Missing Input", "Please select or drag & drop at least one product label image or PDF.");
    return;
  }

  if (state.inputMode === 'url' && !elements.urlInput.value.trim()) {
    showError("Missing URL", "Please enter an image URL or product webpage URL to analyze.");
    return;
  }

  // Show loading
  elements.loadingSection.classList.remove('hidden');
  elements.resultsSection.classList.add('hidden');
  elements.runAnalysisBtn.disabled = true;

  try {
    let responseData;

    if (state.inputMode === 'upload') {
      const formData = new FormData();
      formData.append('product_type', state.productType);
      state.selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      const res = await fetch(`${API_BASE}/api/analyze/upload`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }

      responseData = await res.json();
    } else {
      const payload = {
        url: elements.urlInput.value.trim(),
        product_type: state.productType
      };

      const res = await fetch(`${API_BASE}/api/analyze/url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }

      responseData = await res.json();
    }

    state.currentAnalysis = responseData;
    state.activeImageIndex = 0;
    renderAnalysisResults();

  } catch (err) {
    showError("Verification Failed", err.message || "An error occurred while running Legal Metrology verification.");
  } finally {
    elements.loadingSection.classList.add('hidden');
    elements.runAnalysisBtn.disabled = false;
  }
}

// Render Results
function renderAnalysisResults() {
  const data = state.currentAnalysis;
  if (!data) return;

  const report = data.compliance_report;
  const metrics = report.metrics;

  // 1. Overall Status & Scorecard
  elements.overallStatusHeading.textContent = report.overall_status.replace('_', ' ');
  elements.statusSummaryText.textContent = report.status_summary;
  
  if (report.overall_status === 'COMPLIANT') {
    elements.overallStatusHeading.className = "text-2xl font-black text-emerald-400 mt-1";
    elements.scoreCirclePath.setAttribute('class', 'text-emerald-500 transition-all duration-1000');
  } else if (report.overall_status === 'PARTIALLY_COMPLIANT') {
    elements.overallStatusHeading.className = "text-2xl font-black text-amber-400 mt-1";
    elements.scoreCirclePath.setAttribute('class', 'text-amber-500 transition-all duration-1000');
  } else {
    elements.overallStatusHeading.className = "text-2xl font-black text-rose-400 mt-1";
    elements.scoreCirclePath.setAttribute('class', 'text-rose-500 transition-all duration-1000');
  }

  const score = report.compliance_percentage;
  elements.scorePercentText.textContent = `${score}%`;
  elements.scoreCirclePath.setAttribute('stroke-dasharray', `${score}, 100`);

  elements.metricTotalMandatory.textContent = metrics.total_mandatory_fields;
  elements.metricPassed.textContent = metrics.passed_mandatory_fields;
  elements.metricFailed.textContent = metrics.failed_mandatory_fields;
  elements.metricUnreadable.textContent = metrics.unreadable_fields_count;

  // 2. Image Tabs & Viewer
  renderImageTabs();
  loadActiveImage();

  // 3. Raw OCR Text
  elements.rawOcrTextarea.value = data.raw_extracted_text || "(No text recognized)";

  // 4. Field Breakdown Cards
  renderFieldCards();

  // Reveal results
  elements.resultsSection.classList.remove('hidden');
  elements.jumpToResultsBtn.classList.remove('hidden');
  lucide.createIcons();

  // Smooth scroll
  setTimeout(() => {
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
  }, 100);
}

function renderImageTabs() {
  const images = state.currentAnalysis.processed_images || [];
  if (images.length <= 1) {
    elements.imageTabsContainer.innerHTML = "";
    return;
  }

  elements.imageTabsContainer.innerHTML = images.map((img, idx) => `
    <button onclick="switchActiveImage(${idx})" class="px-3 py-1 text-xs rounded-lg font-medium transition-all ${
      state.activeImageIndex === idx 
        ? 'bg-indigo-600 text-white shadow' 
        : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
    }">
      Photo ${idx + 1} (${img.blocks_count} blocks)
    </button>
  `).join('');
}

window.switchActiveImage = function(index) {
  state.activeImageIndex = index;
  renderImageTabs();
  loadActiveImage();
};

function loadActiveImage() {
  const images = state.currentAnalysis.processed_images || [];
  if (images.length === 0) return;

  const currentImgMeta = images[state.activeImageIndex];
  elements.displayPackagingImg.src = `${API_BASE}${currentImgMeta.url}`;
  
  elements.displayPackagingImg.onload = () => {
    renderBoundingBoxes();
  };
}

function renderBoundingBoxes() {
  const svg = elements.bboxSvgOverlay;
  svg.innerHTML = "";

  const images = state.currentAnalysis.processed_images || [];
  if (images.length === 0) return;

  const currentImgMeta = images[state.activeImageIndex];
  const fields = state.currentAnalysis.compliance_report.fields || [];

  // Map of field bounding boxes on this image
  const fieldBoxes = fields.filter(f => f.bounding_box && f.image_index === state.activeImageIndex);
  
  // All OCR Blocks on this image
  const ocrBlocks = currentImgMeta.ocr_blocks || [];

  // Draw generic OCR blocks first (indigo background)
  ocrBlocks.forEach((block, bIdx) => {
    const bbox = block.bbox_norm;
    if (!bbox) return;

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", `${bbox.x * 100}%`);
    rect.setAttribute("y", `${bbox.y * 100}%`);
    rect.setAttribute("width", `${bbox.width * 100}%`);
    rect.setAttribute("height", `${bbox.height * 100}%`);
    rect.setAttribute("rx", "2");
    
    const isLow = block.is_low_confidence;
    rect.setAttribute("class", `bbox-rect ${isLow ? 'low-confidence' : 'ocr-block'}`);
    rect.setAttribute("data-type", "ocr");
    rect.setAttribute("data-text", block.text);
    rect.setAttribute("data-conf", block.confidence);

    rect.addEventListener('mouseenter', () => {
      showOcrBlockInspector(block);
    });

    svg.appendChild(rect);
  });

  // Draw Legal Field Mapped Boxes (Emerald / Amber highlight)
  fieldBoxes.forEach(field => {
    const bbox = field.bounding_box;
    if (!bbox) return;

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", `${bbox.x * 100}%`);
    rect.setAttribute("y", `${bbox.y * 100}%`);
    rect.setAttribute("width", `${bbox.width * 100}%`);
    rect.setAttribute("height", `${bbox.height * 100}%`);
    rect.setAttribute("rx", "3");
    rect.setAttribute("id", `svg-box-${field.field_key}`);
    
    const isPass = field.status === "PASS";
    const isLow = field.status === "UNREADABLE";
    rect.setAttribute("class", `bbox-rect ${isLow ? 'low-confidence' : 'field-detected'}`);
    
    rect.addEventListener('mouseenter', () => {
      showFieldInspector(field);
      highlightFieldCard(field.field_key);
    });

    rect.addEventListener('click', () => {
      showFieldInspector(field);
      highlightFieldCard(field.field_key);
      const cardEl = document.getElementById(`field-card-${field.field_key}`);
      if (cardEl) {
        cardEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });

    svg.appendChild(rect);
  });
}

function showFieldInspector(field) {
  elements.inspectorEmptyState.classList.add('hidden');
  elements.inspectorDetails.classList.remove('hidden');

  elements.inspFieldName.textContent = field.field_name;
  elements.inspExtractedVal.textContent = field.extracted_value || "(Not detected)";
  elements.inspSynonym.textContent = field.matched_synonym || "Direct Match";
  elements.inspConfidence.textContent = `${(field.confidence_score * 100).toFixed(1)}%`;
  elements.inspLegalRule.textContent = field.legal_rule;

  const isPass = field.status === "PASS";
  const isWarn = field.status === "WARNING";
  const isUnreadable = field.status === "UNREADABLE";

  elements.inspValidationMsg.textContent = field.details;
  if (isPass) {
    elements.inspValidationMsg.className = "text-[11px] text-emerald-300 bg-emerald-500/10 p-2 rounded border border-emerald-500/20 mt-1";
  } else if (isWarn) {
    elements.inspValidationMsg.className = "text-[11px] text-amber-300 bg-amber-500/10 p-2 rounded border border-amber-500/20 mt-1";
  } else {
    elements.inspValidationMsg.className = "text-[11px] text-rose-300 bg-rose-500/10 p-2 rounded border border-rose-500/20 mt-1";
  }
}

function showOcrBlockInspector(block) {
  elements.inspectorEmptyState.classList.add('hidden');
  elements.inspectorDetails.classList.remove('hidden');

  elements.inspFieldName.textContent = "Raw OCR Text Region";
  elements.inspExtractedVal.textContent = block.text;
  elements.inspSynonym.textContent = "PP-OCRv4 Text Line";
  elements.inspConfidence.textContent = `${(block.confidence * 100).toFixed(1)}%`;
  elements.inspLegalRule.textContent = "Scanned packaging text block";
  elements.inspValidationMsg.textContent = `Text Block: ${block.text}`;
  elements.inspValidationMsg.className = "text-[11px] text-indigo-300 bg-indigo-500/10 p-2 rounded border border-indigo-500/20 mt-1";
}

function renderFieldCards() {
  const fields = state.currentAnalysis.compliance_report.fields || [];
  const filter = state.activeFilter;

  const filteredFields = fields.filter(f => {
    if (filter === "all") return true;
    if (filter === "PASS") return f.status === "PASS" || f.status === "WARNING";
    if (filter === "FAIL") return f.status === "FAIL" || f.status === "NOT_FOUND";
    if (filter === "UNREADABLE") return f.status === "UNREADABLE";
    return true;
  });

  elements.fieldCardsContainer.innerHTML = filteredFields.map(field => {
    const status = field.status;
    let badgeClass, badgeText, iconName, borderClass;

    if (status === "PASS") {
      badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      badgeText = "COMPLIANT";
      iconName = "check-circle-2";
      borderClass = "border-slate-800 hover:border-emerald-500/40";
    } else if (status === "WARNING") {
      badgeClass = "bg-amber-500/10 text-amber-400 border-amber-500/20";
      badgeText = "ADVISORY WARNING";
      iconName = "alert-triangle";
      borderClass = "border-slate-800 hover:border-amber-500/40";
    } else if (status === "UNREADABLE") {
      badgeClass = "bg-amber-500/10 text-amber-300 border-amber-500/20";
      badgeText = "OCR UNREADABLE";
      iconName = "help-circle";
      borderClass = "border-amber-500/30 bg-amber-950/10";
    } else {
      badgeClass = "bg-rose-500/10 text-rose-400 border-rose-500/20";
      badgeText = "MISSING / NON-COMPLIANT";
      iconName = "x-circle";
      borderClass = "border-rose-500/30 bg-rose-950/10";
    }

    const hasBbox = field.bounding_box != null;

    return `
      <div id="field-card-${field.field_key}" 
           class="field-card rounded-2xl border ${borderClass} bg-slate-950/90 p-5 space-y-4 transition-all"
           onmouseenter="onFieldCardHover('${field.field_key}')"
           onmouseleave="onFieldCardLeave('${field.field_key}')">
        
        <div class="flex items-start justify-between gap-3">
          <div class="space-y-1">
            <div class="flex items-center space-x-2">
              <h4 class="text-sm font-bold text-white">${field.field_name}</h4>
              ${field.is_mandatory ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">Mandatory</span>` : ''}
            </div>
            <p class="text-[11px] text-slate-400 leading-tight">${field.legal_rule}</p>
          </div>

          <span class="px-2.5 py-1 text-[10px] font-bold rounded-full border ${badgeClass} flex items-center space-x-1 flex-shrink-0">
            <i data-lucide="${iconName}" class="w-3.5 h-3.5"></i>
            <span>${badgeText}</span>
          </span>
        </div>

        <!-- Extracted Value Block -->
        <div class="space-y-1.5 text-xs">
          <span class="text-[10px] text-slate-500 uppercase font-mono">Detected Label Value:</span>
          <div class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs ${field.extracted_value ? 'text-indigo-300' : 'text-slate-500 italic'}">
            ${field.extracted_value || "(Mandatory declaration missing from packaging)"}
          </div>
        </div>

        <!-- Metadata Row -->
        <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/80">
          <div>
            <span class="text-slate-500">Synonym Used:</span>
            <p class="font-medium text-slate-300 truncate">${field.matched_synonym || "—"}</p>
          </div>
          <div>
            <span class="text-slate-500">OCR Confidence:</span>
            <p class="font-medium text-emerald-400 font-mono">${field.confidence_score ? (field.confidence_score * 100).toFixed(1) + '%' : '0.0%'}</p>
          </div>
        </div>

        <!-- Findings & Remediation -->
        <div class="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1 text-xs">
          <div class="flex items-start space-x-1.5 text-slate-300 text-[11px]">
            <span class="font-semibold text-slate-400">Finding:</span>
            <span>${field.details}</span>
          </div>
          ${field.warning ? `
            <div class="flex items-start space-x-1.5 text-amber-300 text-[11px]">
              <span class="font-semibold text-amber-400">Advisory:</span>
              <span>${field.warning}</span>
            </div>
          ` : ''}
        </div>

        ${hasBbox ? `
          <div class="flex items-center justify-end">
            <button onclick="focusFieldBox('${field.field_key}', ${field.image_index})" class="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center space-x-1 transition-colors font-medium">
              <i data-lucide="scan" class="w-3.5 h-3.5"></i>
              <span>Locate on Packaging</span>
            </button>
          </div>
        ` : ''}

      </div>
    `;
  }).join('');

  lucide.createIcons();
}

window.onFieldCardHover = function(fieldKey) {
  const svgBox = document.getElementById(`svg-box-${fieldKey}`);
  if (svgBox) {
    svgBox.classList.add('active-highlight');
  }
};

window.onFieldCardLeave = function(fieldKey) {
  const svgBox = document.getElementById(`svg-box-${fieldKey}`);
  if (svgBox) {
    svgBox.classList.remove('active-highlight');
  }
};

window.focusFieldBox = function(fieldKey, imageIdx) {
  if (state.activeImageIndex !== imageIdx) {
    switchActiveImage(imageIdx);
  }
  
  setTimeout(() => {
    const svgBox = document.getElementById(`svg-box-${fieldKey}`);
    if (svgBox) {
      svgBox.classList.add('active-highlight');
      setTimeout(() => svgBox.classList.remove('active-highlight'), 3000);
    }
    
    // Trigger inspector
    const field = state.currentAnalysis.compliance_report.fields.find(f => f.field_key === fieldKey);
    if (field) {
      showFieldInspector(field);
    }

    elements.displayPackagingImg.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 150);
};

function highlightFieldCard(fieldKey) {
  document.querySelectorAll('.field-card').forEach(c => c.classList.remove('active-card'));
  const card = document.getElementById(`field-card-${fieldKey}`);
  if (card) {
    card.classList.add('active-card');
  }
}

// Download PDF
async function downloadPdfReport() {
  if (!state.currentAnalysis) return;

  try {
    elements.downloadPdfBtn.disabled = true;
    elements.downloadPdfBtn.innerHTML = `<span>Generating PDF...</span>`;

    const res = await fetch(`${API_BASE}/api/export/pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        compliance_report: state.currentAnalysis.compliance_report
      })
    });

    if (!res.ok) throw new Error("Failed to generate PDF");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Legal_Metrology_Compliance_Report_${state.currentAnalysis.session_id}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert("Error downloading PDF: " + err.message);
  } finally {
    elements.downloadPdfBtn.disabled = false;
    elements.downloadPdfBtn.innerHTML = `
      <i data-lucide="file-down" class="w-4 h-4"></i>
      <span>Export PDF Report</span>
    `;
    lucide.createIcons();
  }
}

// Download JSON
function downloadJsonReport() {
  if (!state.currentAnalysis) return;
  const jsonStr = JSON.stringify(state.currentAnalysis, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Legal_Metrology_Compliance_${state.currentAnalysis.session_id}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
