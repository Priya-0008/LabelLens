import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.rules.validators import (
    validate_net_quantity,
    validate_mrp,
    validate_mfg_date,
    validate_expiry_date,
    validate_address,
    validate_consumer_care,
    validate_pharma_license,
    validate_pharma_batch,
    validate_pharma_composition,
    validate_country_of_origin
)

RULES_JSON_PATH = Path(__file__).resolve().parent / "synonyms.json"

class ComplianceRuleEngine:
    def __init__(self):
        with open(RULES_JSON_PATH, "r", encoding="utf-8") as f:
            self.rules_config = json.load(f)

    def get_rule_config(self, product_type: str = "general") -> Dict[str, Any]:
        p_type = "medicine" if product_type.lower() in ["medicine", "pharma", "pharmaceutical"] else "general"
        return self.rules_config.get(p_type, self.rules_config["general"])

    def evaluate_compliance(
        self,
        product_type: str,
        mapped_fields: Dict[str, Any],
        full_extracted_text: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluates the mapped extracted fields against Legal Metrology Rules, 2011 
        and Drugs & Cosmetics Rules.
        """
        config = self.get_rule_config(product_type)
        fields_config = config["fields"]
        
        field_results: List[Dict[str, Any]] = []
        
        total_mandatory = 0
        passed_mandatory = 0
        warnings_count = 0
        failed_count = 0
        unreadable_count = 0
        
        mfg_date_str = ""
        if "mfg_pkd_date" in mapped_fields and mapped_fields["mfg_pkd_date"].get("extracted_value"):
            mfg_date_str = mapped_fields["mfg_pkd_date"]["extracted_value"]

        for field_key, field_spec in fields_config.items():
            is_mandatory = field_spec.get("is_mandatory", True)
            if is_mandatory:
                total_mandatory += 1
                
            field_data = mapped_fields.get(field_key)
            
            # Case 1: Field completely not found
            if not field_data or not field_data.get("found"):
                status = "FAIL" if is_mandatory else "NOT_FOUND"
                if is_mandatory:
                    failed_count += 1
                
                field_results.append({
                    "field_key": field_key,
                    "field_name": field_spec["name"],
                    "legal_rule": field_spec["legal_rule"],
                    "is_mandatory": is_mandatory,
                    "importance": field_spec.get("importance", "medium"),
                    "status": status,
                    "status_code": "MISSING_FIELD",
                    "extracted_value": None,
                    "matched_synonym": None,
                    "confidence_score": 0.0,
                    "bounding_box": None,
                    "image_index": None,
                    "details": f"Mandatory declaration '{field_spec['name']}' was not found under any recognized synonym.",
                    "remediation": "Ensure this mandatory declaration is clearly printed on the product label as per Legal Metrology Rules."
                })
                continue

            extracted_value = field_data.get("extracted_value", "").strip()
            matched_synonym = field_data.get("matched_synonym", "")
            confidence = field_data.get("confidence", 1.0)
            is_low_confidence = field_data.get("is_low_confidence", False)
            bbox = field_data.get("bounding_box")
            image_idx = field_data.get("image_index", 0)

            # Case 2: Low confidence OCR extraction
            if is_low_confidence and confidence < 0.45:
                unreadable_count += 1
                field_results.append({
                    "field_key": field_key,
                    "field_name": field_spec["name"],
                    "legal_rule": field_spec["legal_rule"],
                    "is_mandatory": is_mandatory,
                    "importance": field_spec.get("importance", "medium"),
                    "status": "UNREADABLE",
                    "status_code": "LOW_CONFIDENCE_OCR",
                    "extracted_value": extracted_value,
                    "matched_synonym": matched_synonym,
                    "confidence_score": round(confidence, 3),
                    "bounding_box": bbox,
                    "image_index": image_idx,
                    "details": f"Text detected near '{matched_synonym}', but OCR confidence ({confidence:.1%}) is too low to guarantee compliance accuracy.",
                    "remediation": "Re-upload a clearer, higher-resolution photo of this label section without glare or shadows."
                })
                continue

            # Case 3: Validate field format & rules
            validation = self._run_field_validator(
                field_key=field_key,
                value=extracted_value,
                product_type=product_type,
                full_text=full_extracted_text,
                mfg_date_str=mfg_date_str
            )
            
            val_status = validation.get("status", "PASS")
            val_msg = validation.get("message", "Compliant declaration.")
            warning = validation.get("warning")
            
            if val_status == "PASS":
                if is_mandatory:
                    passed_mandatory += 1
                final_status = "PASS"
                status_code = "COMPLIANT"
            elif val_status == "WARNING":
                if is_mandatory:
                    passed_mandatory += 1  # counts as pass with note
                warnings_count += 1
                final_status = "WARNING"
                status_code = "ADVISORY_WARNING"
            else:
                if is_mandatory:
                    failed_count += 1
                final_status = "FAIL"
                status_code = "FORMAT_NON_COMPLIANT"

            field_results.append({
                "field_key": field_key,
                "field_name": field_spec["name"],
                "legal_rule": field_spec["legal_rule"],
                "is_mandatory": is_mandatory,
                "importance": field_spec.get("importance", "medium"),
                "status": final_status,
                "status_code": status_code,
                "extracted_value": extracted_value,
                "matched_synonym": matched_synonym,
                "confidence_score": round(confidence, 3),
                "bounding_box": bbox,
                "image_index": image_idx,
                "details": val_msg,
                "warning": warning,
                "remediation": "Compliant." if final_status == "PASS" else ("Review advisory recommendations." if final_status == "WARNING" else "Correct label printing to match Legal Metrology standards.")
            })

        # Calculate Compliance Score
        compliance_pct = round((passed_mandatory / total_mandatory * 100), 1) if total_mandatory > 0 else 100.0
        
        # Determine overall status
        if compliance_pct >= 90 and failed_count == 0:
            overall_status = "COMPLIANT"
            status_summary = "Fully Compliant with Legal Metrology Regulations"
        elif compliance_pct >= 70:
            overall_status = "PARTIALLY_COMPLIANT"
            status_summary = "Partially Compliant - Minor infractions or missing non-critical items detected"
        else:
            overall_status = "NON_COMPLIANT"
            status_summary = "Non-Compliant - Critical mandatory declarations are missing or invalid"

        return {
            "product_type": product_type,
            "rule_framework": config["legal_basis"],
            "overall_status": overall_status,
            "status_summary": status_summary,
            "compliance_percentage": compliance_pct,
            "metrics": {
                "total_mandatory_fields": total_mandatory,
                "passed_mandatory_fields": passed_mandatory,
                "failed_mandatory_fields": failed_count,
                "warnings_count": warnings_count,
                "unreadable_fields_count": unreadable_count
            },
            "fields": field_results
        }

    def _run_field_validator(
        self,
        field_key: str,
        value: str,
        product_type: str,
        full_text: str,
        mfg_date_str: str = ""
    ) -> Dict[str, Any]:
        if field_key == "net_quantity":
            return validate_net_quantity(value, product_type)
        elif field_key == "mrp":
            return validate_mrp(value, full_text)
        elif field_key == "mfg_pkd_date":
            return validate_mfg_date(value)
        elif field_key == "expiry_date":
            return validate_expiry_date(value, mfg_date_str)
        elif field_key == "manufacturer_packer_importer":
            return validate_address(value)
        elif field_key == "consumer_care":
            return validate_consumer_care(value)
        elif field_key == "mfg_license_no":
            return validate_pharma_license(value)
        elif field_key == "batch_number":
            return validate_pharma_batch(value)
        elif field_key == "dosage_composition":
            return validate_pharma_composition(value)
        elif field_key == "country_of_origin":
            return validate_country_of_origin(value)
        elif field_key == "schedule_drug_warning":
            return {"valid": True, "status": "PASS", "message": f"Schedule warning / Rx marker detected: {value}"}
        
        return {"valid": True, "status": "PASS", "message": f"Declaration detected: {value}"}
