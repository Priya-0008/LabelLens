import io
from datetime import datetime
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportExporter:
    @staticmethod
    def generate_pdf_report(compliance_data: Dict[str, Any]) -> bytes:
        """
        Generates a PDF Legal Metrology Compliance Audit Report.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#1E293B')
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B')
        )
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=12,
            spaceAfter=6
        )
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11
        )
        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=11
        )

        story = []

        # Header Title
        story.append(Paragraph("LEGAL METROLOGY COMPLIANCE AUDIT REPORT", title_style))
        story.append(Paragraph("Smart India Hackathon SIH26034 Automated Verification System", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=12))

        # Metadata Table
        product_type = compliance_data.get("product_type", "General").title()
        overall_status = compliance_data.get("overall_status", "UNKNOWN")
        score = compliance_data.get("compliance_percentage", 0.0)
        timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

        status_color = colors.HexColor('#16A34A') if overall_status == "COMPLIANT" else (colors.HexColor('#D97706') if overall_status == "PARTIALLY_COMPLIANT" else colors.HexColor('#DC2626'))

        meta_data = [
            [
                Paragraph("<b>Product Type:</b> " + product_type, cell_style),
                Paragraph(f"<b>Compliance Score:</b> {score}%", cell_style)
            ],
            [
                Paragraph("<b>Audit Date:</b> " + timestamp, cell_style),
                Paragraph(f"<b>Status:</b> <font color='{status_color.hexval()}'><b>{overall_status}</b></font>", cell_style)
            ],
            [
                Paragraph(f"<b>Legal Basis:</b> {compliance_data.get('rule_framework', 'Legal Metrology Rules, 2011')}", cell_style),
                Paragraph(f"<b>Summary:</b> {compliance_data.get('status_summary', '')}", cell_style)
            ]
        ]
        t_meta = Table(meta_data, colWidths=[260, 280])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 14))

        # Field Breakdown Section
        story.append(Paragraph("Mandatory Field Verification Breakdown", section_style))

        table_rows = [
            [
                Paragraph("<b>Mandatory Field</b>", cell_bold),
                Paragraph("<b>Legal Rule Citation</b>", cell_bold),
                Paragraph("<b>Extracted Value / Synonym</b>", cell_bold),
                Paragraph("<b>OCR Conf.</b>", cell_bold),
                Paragraph("<b>Status</b>", cell_bold)
            ]
        ]

        for f in compliance_data.get("fields", []):
            st = f.get("status", "FAIL")
            st_color = "#16A34A" if st == "PASS" else ("#D97706" if st == "WARNING" else "#DC2626")
            
            ext_val = f.get("extracted_value") or "<i>(Not Detected)</i>"
            syn_used = f" [Synonym: {f.get('matched_synonym')}]" if f.get('matched_synonym') else ""
            conf = f"{f.get('confidence_score', 0)*100:.1f}%" if f.get("confidence_score") else "N/A"

            table_rows.append([
                Paragraph(f"<b>{f.get('field_name')}</b>", cell_style),
                Paragraph(f.get("legal_rule", ""), cell_style),
                Paragraph(f"{ext_val}{syn_used}", cell_style),
                Paragraph(conf, cell_style),
                Paragraph(f"<font color='{st_color}'><b>{st}</b></font>", cell_bold)
            ])

        col_widths = [110, 130, 190, 50, 60]
        t_fields = Table(table_rows, colWidths=col_widths, repeatRows=1)
        t_fields.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ]))
        story.append(t_fields)

        # Footer Notice
        story.append(Spacer(1, 16))
        footer_text = "Notice: This automated report is generated using PaddleOCR/PP-OCRv4 and NLP rule validation under the Legal Metrology (Packaged Commodities) Rules, 2011 and Drugs & Cosmetics Rules. For regulatory enforcement, physical specimen verification is advised."
        story.append(Paragraph(footer_text, subtitle_style))

        doc.build(story)
        return buffer.getvalue()
