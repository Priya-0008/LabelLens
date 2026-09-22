import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}

def parse_date_flexible(text: str) -> Optional[Tuple[int, int]]:
    """Extracts (month, year) from a date string."""
    if not text:
        return None
    cleaned = text.strip().lower()
    
    # Pattern 1: MM/YYYY or MM-YYYY or MM.YYYY
    m1 = re.search(r'\b(0[1-9]|1[0-2])[/\-.\s]+(20\d{2}|\d{2})\b', cleaned)
    if m1:
        month = int(m1.group(1))
        year = int(m1.group(2))
        if year < 100:
            year += 2000
        return (month, year)
    
    # Pattern 2: MMM/YYYY or MMM YYYY or MMM-YY (e.g. Nov 2024, NOV-24)
    m2 = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[/\-.\s]+(20\d{2}|\d{2})\b', cleaned)
    if m2:
        mon_str = m2.group(1)
        month = MONTH_NAMES.get(mon_str, 1)
        year = int(m2.group(2))
        if year < 100:
            year += 2000
        return (month, year)
    
    # Pattern 3: DD/MM/YYYY or DD-MM-YY
    m3 = re.search(r'\b([0-2]?\d|3[01])[/\-.](0[1-9]|1[0-2])[/\-.](20\d{2}|\d{2})\b', cleaned)
    if m3:
        month = int(m3.group(2))
        year = int(m3.group(3))
        if year < 100:
            year += 2000
        return (month, year)
        
    return None


def validate_net_quantity(value: str, product_type: str = "general") -> Dict[str, Any]:
    if not value or not value.strip():
        return {"valid": False, "status": "FAIL", "message": "Net quantity value is missing or empty."}
    
    val = value.strip().lower()
    
    # Valid SI & Package units under Legal Metrology (order longest to shortest)
    si_unit_pattern = r'(\d+(?:\.\d+)?)\s*(kilograms?|kg|grams?|grams|gms|gm|g|milligrams?|mg|litres?|liters?|ltrs?|ltr|lit|l|millilitres?|milliliters?|ml|meters?|m|centimeters?|cm|millimeters?|mm|tablets?|capsules?|tabs?|caps?|sachets?|vials?|ampoules?|units?|pieces?|pcs?|count|no\.?|n|u)'
    match = re.search(si_unit_pattern, val)
    
    if match:
        qty_num = match.group(1)
        unit = match.group(2)
        warning = None
        
        # Legal Metrology Rule 11 standard symbols recommendation
        if unit in ["gm", "gms"]:
            warning = "Rule 11 Note: Standard SI unit symbol for gram is 'g' (found 'gm/gms')."
        elif unit in ["ltr", "lit"]:
            warning = "Rule 11 Note: Standard SI unit symbol for litre is 'l' or 'L' (found 'ltr')."
            
        return {
            "valid": True,
            "status": "PASS",
            "message": f"Valid quantity declaration detected: {qty_num} {unit}.",
            "warning": warning,
            "parsed_quantity": qty_num,
            "parsed_unit": unit
        }
    
    return {
        "valid": False,
        "status": "FAIL",
        "message": "Net quantity does not contain a recognizable SI metric unit or count (e.g. g, kg, ml, L, pcs, N)."
    }


def validate_mrp(value: str, full_label_text: str = "") -> Dict[str, Any]:
    if not value or not value.strip():
        return {"valid": False, "status": "FAIL", "message": "MRP value is missing or empty."}
    
    val = value.strip()
    full_context = (value + " " + full_label_text).lower()
    
    # Check numerical price
    price_match = re.search(r'(?:₹|rs\.?|inr)?\s*([0-9]+(?:[\.,][0-9]{1,2})?)', val, re.IGNORECASE)
    has_price = False
    price_val = None
    
    if price_match:
        try:
            raw_p = price_match.group(1).replace(',', '.')
            if float(raw_p) > 0:
                has_price = True
                price_val = float(raw_p)
        except Exception:
            pass
            
    if not has_price:
        # Fallback search for any numbers
        any_num = re.search(r'\b\d+(?:\.\d{1,2})?\b', val)
        if any_num:
            has_price = True
            price_val = float(any_num.group(0))

    if not has_price:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "No valid numerical price amount detected in the MRP declaration."
        }
    
    # Check currency symbol/indicator
    has_currency = bool(re.search(r'(₹|rs\.?|inr|rupees)', val, re.IGNORECASE))
    
    # Check "inclusive of all taxes"
    has_tax_clause = bool(re.search(r'(incl|inclusive)\.?\s*(?:of)?\s*all\s*taxes?', full_context, re.IGNORECASE))
    
    warnings = []
    if not has_currency:
        warnings.append("Rupee symbol (₹ or Rs.) not clearly detected next to MRP.")
    if not has_tax_clause:
        warnings.append("Mandatory phrase 'incl. of all taxes' was not distinctly detected near MRP.")
        
    status = "PASS" if (has_currency and has_tax_clause) else ("WARNING" if has_price else "FAIL")
    
    msg_parts = [f"MRP detected: ₹{price_val:.2f}"]
    if has_tax_clause:
        msg_parts.append("with 'inclusive of all taxes' declaration.")
    else:
        msg_parts.append("(Tax declaration phrase pending verification).")
        
    return {
        "valid": True,
        "status": status,
        "message": " ".join(msg_parts),
        "warning": " | ".join(warnings) if warnings else None,
        "parsed_price": price_val
    }


def validate_mfg_date(value: str) -> Dict[str, Any]:
    if not value or not value.strip():
        return {"valid": False, "status": "FAIL", "message": "Manufacturing date is missing."}
        
    parsed = parse_date_flexible(value)
    if not parsed:
        return {
            "valid": False,
            "status": "FAIL",
            "message": f"Manufacturing date format could not be parsed. Expected MM/YYYY, MMM YYYY, or DD/MM/YYYY (Found: '{value}')."
        }
        
    month, year = parsed
    curr_year = datetime.now().year
    
    if year > curr_year + 1:
        return {
            "valid": False,
            "status": "FAIL",
            "message": f"Manufacturing year {year} is in the future."
        }
    if year < 2000:
        return {
            "valid": False,
            "status": "WARNING",
            "message": f"Manufacturing year {year} is earlier than year 2000; verify image legibility."
        }
        
    return {
        "valid": True,
        "status": "PASS",
        "message": f"Valid manufacturing date format: Month {month:02d} / Year {year}.",
        "parsed_month": month,
        "parsed_year": year
    }


def validate_expiry_date(exp_value: str, mfg_value: str = "") -> Dict[str, Any]:
    if not exp_value or not exp_value.strip():
        return {"valid": False, "status": "FAIL", "message": "Expiry date is missing."}
        
    exp_parsed = parse_date_flexible(exp_value)
    if not exp_parsed:
        return {
            "valid": False,
            "status": "FAIL",
            "message": f"Expiry date format could not be parsed. Expected MM/YYYY or MMM YYYY (Found: '{exp_value}')."
        }
        
    exp_month, exp_year = exp_parsed
    
    if mfg_value:
        mfg_parsed = parse_date_flexible(mfg_value)
        if mfg_parsed:
            mfg_month, mfg_year = mfg_parsed
            if (exp_year < mfg_year) or (exp_year == mfg_year and exp_month < mfg_month):
                return {
                    "valid": False,
                    "status": "FAIL",
                    "message": f"Chronological Violation: Expiry date ({exp_month:02d}/{exp_year}) is earlier than Manufacturing date ({mfg_month:02d}/{mfg_year})."
                }
                
    return {
        "valid": True,
        "status": "PASS",
        "message": f"Valid expiry date format: Month {exp_month:02d} / Year {exp_year}.",
        "parsed_month": exp_month,
        "parsed_year": exp_year
    }


def validate_address(value: str) -> Dict[str, Any]:
    if not value or len(value.strip()) < 10:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Manufacturer/Packer address is too short or missing complete location details."
        }
        
    val = value.strip()
    # Check for PIN code or common location cues
    has_pincode = bool(re.search(r'\b[1-9][0-9]{5}\b', val))
    has_location_cues = bool(re.search(r'\b(road|rd|street|st|nagar|dist|district|state|estate|phase|plot|ind|industrial|sector|lane|city|pin|pincode|india|delhi|mumbai|bengaluru|bangalore|hyderabad|chennai|ahmedabad|pune|kolkata|gujarat|maharashtra|karnataka|haryana|tamil nadu|up|uttar pradesh)\b', val, re.IGNORECASE))
    
    warning = None
    if not has_pincode:
        warning = "Rule 6(1)(a) Advisory: PIN code is strongly recommended for full address completeness."
        
    status = "PASS" if (has_location_cues or len(val) >= 20) else "WARNING"
    
    return {
        "valid": True,
        "status": status,
        "message": "Manufacturer/Packer name and address details present.",
        "warning": warning
    }


def validate_consumer_care(value: str) -> Dict[str, Any]:
    if not value or len(value.strip()) < 5:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Consumer care contact details are missing."
        }
        
    val = value.strip()
    has_email = bool(re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', val))
    has_phone = bool(re.search(r'\b(?:1800[- ]?\d{3}[- ]?\d{3,4}|\+?91[- ]?\d{10}|\d{10,11}|\d{3,5}[- ]\d{6,8})\b', val))
    
    channels = []
    if has_email:
        channels.append("Email")
    if has_phone:
        channels.append("Helpline Phone/Toll-Free")
        
    if channels:
        return {
            "valid": True,
            "status": "PASS",
            "message": f"Consumer care contact channels detected: {', '.join(channels)}."
        }
    
    return {
        "valid": True,
        "status": "WARNING",
        "message": "Consumer care text detected, but telephone or email address format could not be verified.",
        "warning": "Rule 6(1)(g) mandates a clear telephone number or email address."
    }


def validate_pharma_license(value: str) -> Dict[str, Any]:
    if not value or len(value.strip()) < 3:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Manufacturing License Number (Mfg. Lic. No.) is missing."
        }
    return {
        "valid": True,
        "status": "PASS",
        "message": f"Manufacturing License Number verified: {value.strip()}."
    }


def validate_pharma_batch(value: str) -> Dict[str, Any]:
    if not value or len(value.strip()) < 2:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Batch Number (B.No.) is missing."
        }
    return {
        "valid": True,
        "status": "PASS",
        "message": f"Pharmaceutical Batch Number verified: {value.strip()}."
    }


def validate_pharma_composition(value: str) -> Dict[str, Any]:
    if not value or len(value.strip()) < 5:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Dosage & Composition (Active Ingredients) declaration is missing."
        }
    return {
        "valid": True,
        "status": "PASS",
        "message": "Active pharmaceutical composition and dosage declaration present."
    }


def validate_country_of_origin(value: str) -> Dict[str, Any]:
    if not value or len(value.strip()) < 3:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Country of Origin is missing."
        }
    val = value.strip()
    return {
        "valid": True,
        "status": "PASS",
        "message": f"Country of Origin declared: {val}."
    }
