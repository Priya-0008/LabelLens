import sys
import os
import unittest
import numpy as np
import cv2
from pathlib import Path

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BASE_DIR))

from app.rules.validators import (
    validate_net_quantity,
    validate_mrp,
    validate_mfg_date,
    validate_expiry_date,
    validate_address,
    validate_consumer_care,
    validate_pharma_license,
    validate_pharma_batch
)
from app.rules.rule_engine import ComplianceRuleEngine
from app.services.field_mapper import FieldMapper
from app.ocr.preprocessor import ImagePreprocessor
from app.ocr.ocr_engine import ocr_engine
from app.services.report_exporter import ReportExporter

class TestLegalMetrologyCompliance(unittest.TestCase):

    def setUp(self):
        self.engine = ComplianceRuleEngine()
        self.mapper = FieldMapper()

    def test_net_quantity_validation(self):
        # Valid SI units
        res1 = validate_net_quantity("500 g")
        self.assertTrue(res1["valid"])
        self.assertEqual(res1["status"], "PASS")

        res2 = validate_net_quantity("1.5 L")
        self.assertTrue(res2["valid"])

        res3 = validate_net_quantity("10 Tablets", product_type="medicine")
        self.assertTrue(res3["valid"])

        # Warning for non-standard 'gms'
        res4 = validate_net_quantity("250 gms")
        self.assertTrue(res4["valid"])
        self.assertIsNotNone(res4["warning"])

        # Invalid without SI unit
        res5 = validate_net_quantity("Huge Box")
        self.assertFalse(res5["valid"])

    def test_mrp_validation(self):
        # Valid price with rupee and taxes
        res1 = validate_mrp("₹ 149.00", full_label_text="MRP Rs. 149.00 (Incl. of all taxes)")
        self.assertTrue(res1["valid"])
        self.assertEqual(res1["status"], "PASS")
        self.assertEqual(res1["parsed_price"], 149.00)

        # Price without tax statement gives advisory warning
        res2 = validate_mrp("Rs. 99", full_label_text="MRP Rs. 99")
        self.assertTrue(res2["valid"])
        self.assertEqual(res2["status"], "WARNING")

        # No numerical price
        res3 = validate_mrp("Free Sample")
        self.assertFalse(res3["valid"])

    def test_date_validations(self):
        # Mfg date
        res_mfg = validate_mfg_date("08/2024")
        self.assertTrue(res_mfg["valid"])
        self.assertEqual(res_mfg["parsed_month"], 8)
        self.assertEqual(res_mfg["parsed_year"], 2024)

        # Expiry date valid
        res_exp = validate_expiry_date("12/2026", mfg_value="08/2024")
        self.assertTrue(res_exp["valid"])
        self.assertEqual(res_exp["status"], "PASS")

        # Expiry earlier than Mfg (Violation)
        res_exp_bad = validate_expiry_date("01/2023", mfg_value="08/2024")
        self.assertFalse(res_exp_bad["valid"])
        self.assertIn("Chronological Violation", res_exp_bad["message"])

    def test_consumer_care_validation(self):
        res_email = validate_consumer_care("care@company.com")
        self.assertTrue(res_email["valid"])
        self.assertEqual(res_email["status"], "PASS")

        res_tollfree = validate_consumer_care("Toll-Free: 1800 123 4567")
        self.assertTrue(res_tollfree["valid"])

    def test_pharma_specific_validations(self):
        res_lic = validate_pharma_license("DL-12345/MH/2020")
        self.assertTrue(res_lic["valid"])

        res_batch = validate_pharma_batch("B240901A")
        self.assertTrue(res_batch["valid"])

    def test_rule_engine_evaluation(self):
        mock_mapped_fields = {
            "net_quantity": {
                "found": True,
                "extracted_value": "500 g",
                "matched_synonym": "Net Wt.",
                "confidence": 0.98,
                "is_low_confidence": False,
                "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.2, "height": 0.05},
                "image_index": 0
            },
            "mrp": {
                "found": True,
                "extracted_value": "₹ 249.00 (Incl. of all taxes)",
                "matched_synonym": "MRP",
                "confidence": 0.95,
                "is_low_confidence": False,
                "bounding_box": {"x": 0.1, "y": 0.3, "width": 0.3, "height": 0.05},
                "image_index": 0
            },
            "manufacturer_packer_importer": {
                "found": True,
                "extracted_value": "Hindustan FMCG Ltd, Plot 42, GIDC Industrial Estate, Ahmedabad, Gujarat - 380015",
                "matched_synonym": "Manufactured By",
                "confidence": 0.96,
                "is_low_confidence": False,
                "bounding_box": {"x": 0.1, "y": 0.4, "width": 0.5, "height": 0.1},
                "image_index": 0
            },
            "consumer_care": {
                "found": True,
                "extracted_value": "Consumer Care Cell: care@fmcg.com | Toll-Free 1800 222 333",
                "matched_synonym": "Consumer Care",
                "confidence": 0.94,
                "is_low_confidence": False,
                "bounding_box": {"x": 0.1, "y": 0.55, "width": 0.4, "height": 0.05},
                "image_index": 0
            },
            "mfg_pkd_date": {
                "found": True,
                "extracted_value": "09/2024",
                "matched_synonym": "Mfg Date",
                "confidence": 0.92,
                "is_low_confidence": False,
                "bounding_box": {"x": 0.1, "y": 0.65, "width": 0.2, "height": 0.05},
                "image_index": 0
            },
            "country_of_origin": {
                "found": True,
                "extracted_value": "Made in India",
                "matched_synonym": "Made In",
                "confidence": 0.97,
                "is_low_confidence": False,
                "bounding_box": {"x": 0.1, "y": 0.75, "width": 0.2, "height": 0.05},
                "image_index": 0
            }
        }

        report = self.engine.evaluate_compliance(
            product_type="general",
            mapped_fields=mock_mapped_fields,
            full_extracted_text="Sample Packaging Text"
        )

        self.assertEqual(report["overall_status"], "COMPLIANT")
        self.assertEqual(report["compliance_percentage"], 100.0)
        self.assertEqual(report["metrics"]["failed_mandatory_fields"], 0)

    def test_image_preprocessor_pipeline(self):
        # Create a test synthetic label image with text
        test_img = np.ones((400, 600, 3), dtype=np.uint8) * 240
        cv2.putText(test_img, "NET WT: 250 g", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
        cv2.putText(test_img, "MRP: Rs. 99.00 (Incl. of all taxes)", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
        cv2.putText(test_img, "Mfd By: Green Foods Pvt Ltd, Bangalore", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)

        enhanced, sharpened = ImagePreprocessor.preprocess_pipeline(test_img)
        self.assertEqual(enhanced.shape, test_img.shape)
        self.assertEqual(sharpened.shape, test_img.shape)

        # Run OCR engine
        ocr_out = ocr_engine.extract_text_and_boxes(test_img, image_index=0)
        self.assertTrue(len(ocr_out["blocks"]) > 0)
        self.assertIn("NET", ocr_out["full_text"].upper())

    def test_pdf_report_exporter(self):
        mock_report = {
            "product_type": "general",
            "overall_status": "COMPLIANT",
            "status_summary": "Fully Compliant with Legal Metrology Regulations",
            "compliance_percentage": 100.0,
            "fields": [
                {
                    "field_name": "Net Quantity",
                    "legal_rule": "Rule 6(1)(d)",
                    "extracted_value": "500 g",
                    "matched_synonym": "Net Wt.",
                    "confidence_score": 0.98,
                    "status": "PASS",
                    "details": "Valid SI unit."
                }
            ]
        }
        pdf_bytes = ReportExporter.generate_pdf_report(mock_report)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()
