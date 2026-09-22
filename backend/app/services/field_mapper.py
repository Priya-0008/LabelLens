import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz
from app.config import FUZZY_MATCH_THRESHOLD

RULES_JSON_PATH = Path(__file__).resolve().parent.parent / "rules" / "synonyms.json"

class FieldMapper:
    def __init__(self):
        with open(RULES_JSON_PATH, "r", encoding="utf-8") as f:
            self.rules_config = json.load(f)

    def map_extracted_fields(
        self,
        ocr_blocks_by_image: List[List[Dict[str, Any]]],
        product_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Maps OCR text blocks to mandatory Legal Metrology fields using NLP, Regex, and RapidFuzz.
        Returns a dictionary keyed by field_key with extraction metadata and bounding boxes.
        """
        p_type = "medicine" if product_type.lower() in ["medicine", "pharma", "pharmaceutical"] else "general"
        fields_config = self.rules_config.get(p_type, self.rules_config["general"])["fields"]

        # Flatten blocks while preserving image index
        all_blocks: List[Dict[str, Any]] = []
        for img_idx, blocks in enumerate(ocr_blocks_by_image):
            for b_idx, block in enumerate(blocks):
                block_copy = dict(block)
                block_copy["global_block_idx"] = len(all_blocks)
                block_copy["image_index"] = img_idx
                block_copy["local_block_idx"] = b_idx
                all_blocks.append(block_copy)

        mapped_results: Dict[str, Any] = {}

        # Track used blocks to avoid redundant conflicting mappings where appropriate
        for field_key, field_spec in fields_config.items():
            best_match = self._find_best_field_match(field_key, field_spec, all_blocks, ocr_blocks_by_image)
            mapped_results[field_key] = best_match

        return mapped_results

    def _find_best_field_match(
        self,
        field_key: str,
        field_spec: Dict[str, Any],
        all_blocks: List[Dict[str, Any]],
        blocks_by_image: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        synonyms: List[str] = field_spec.get("synonyms", [])
        value_regex: Optional[str] = field_spec.get("value_regex")
        
        candidates: List[Dict[str, Any]] = []

        for block in all_blocks:
            text = block.get("text", "").strip()
            if not text:
                continue

            text_lower = text.lower()
            confidence = block.get("confidence", 0.9)
            img_idx = block.get("image_index", 0)

            # Strategy 1: Check Synonyms with Fuzzy Matching
            matched_synonym = None
            highest_fuzzy_score = 0

            for syn in synonyms:
                syn_lower = syn.lower()
                
                # Direct substring check
                if syn_lower in text_lower:
                    fuzzy_score = 100
                    matched_synonym = syn
                    highest_fuzzy_score = 100
                    break
                
                # Token Sort / Partial Ratio check
                score = fuzz.partial_ratio(syn_lower, text_lower)
                if score >= FUZZY_MATCH_THRESHOLD and score > highest_fuzzy_score:
                    highest_fuzzy_score = score
                    matched_synonym = syn

            # If synonym matched
            if matched_synonym:
                extracted_val = self._extract_field_value(
                    field_key=field_key,
                    synonym=matched_synonym,
                    block=block,
                    all_blocks_in_img=blocks_by_image[img_idx] if img_idx < len(blocks_by_image) else [],
                    value_regex=value_regex
                )
                
                if extracted_val:
                    candidates.append({
                        "found": True,
                        "matched_synonym": matched_synonym,
                        "extracted_value": extracted_val["value"],
                        "confidence": min(confidence, extracted_val.get("confidence", confidence)),
                        "is_low_confidence": block.get("is_low_confidence", False),
                        "bounding_box": extracted_val.get("bbox", block.get("bbox_norm")),
                        "bbox_pixels": extracted_val.get("bbox_pixels", block.get("bbox_pixels")),
                        "image_index": img_idx,
                        "match_score": highest_fuzzy_score + 20  # boosted for synonym presence
                    })

            # Strategy 2: Direct Regex match even if synonym header was separated or implicit
            elif value_regex:
                rgx_match = re.search(value_regex, text, re.IGNORECASE)
                if rgx_match:
                    match_text = rgx_match.group(0).strip()
                    # Exclude general noise
                    if len(match_text) >= 2:
                        candidates.append({
                            "found": True,
                            "matched_synonym": f"Pattern ({field_spec['name']})",
                            "extracted_value": text,
                            "confidence": confidence,
                            "is_low_confidence": block.get("is_low_confidence", False),
                            "bounding_box": block.get("bbox_norm"),
                            "bbox_pixels": block.get("bbox_pixels"),
                            "image_index": img_idx,
                            "match_score": 75
                        })

        if not candidates:
            return {
                "found": False,
                "matched_synonym": None,
                "extracted_value": None,
                "confidence": 0.0,
                "is_low_confidence": False,
                "bounding_box": None,
                "bbox_pixels": None,
                "image_index": None
            }

        # Select highest scoring candidate
        candidates.sort(key=lambda c: (c["match_score"], c["confidence"]), reverse=True)
        return candidates[0]

    def _extract_field_value(
        self,
        field_key: str,
        synonym: str,
        block: Dict[str, Any],
        all_blocks_in_img: List[Dict[str, Any]],
        value_regex: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        text = block.get("text", "").strip()
        syn_lower = synonym.lower()

        # Check if value is in the same block after delimiter
        # e.g., "Net Wt: 500g" or "MRP: Rs. 149.00"
        delimiters = [":", "-", "=", "–", "."]
        for d in delimiters:
            if d in text:
                parts = text.split(d, 1)
                if len(parts) == 2 and fuzz.partial_ratio(syn_lower, parts[0].lower()) >= 70:
                    val_candidate = parts[1].strip()
                    if val_candidate:
                        return {
                            "value": val_candidate,
                            "bbox": block.get("bbox_norm"),
                            "bbox_pixels": block.get("bbox_pixels"),
                            "confidence": block.get("confidence", 0.9)
                        }

        # If synonym is a standalone heading, search spatial neighbor blocks (right or below)
        local_idx = block.get("local_block_idx", -1)
        if local_idx != -1 and local_idx + 1 < len(all_blocks_in_img):
            # Check immediately next OCR block
            next_block = all_blocks_in_img[local_idx + 1]
            next_text = next_block.get("text", "").strip()
            
            # Combine bounding boxes if value is in next block
            merged_bbox, merged_pixels = self._merge_bboxes(block, next_block)

            # If regex provided, see if next block satisfies it
            if value_regex and re.search(value_regex, next_text, re.IGNORECASE):
                return {
                    "value": f"{next_text}",
                    "bbox": merged_bbox,
                    "bbox_pixels": merged_pixels,
                    "confidence": (block.get("confidence", 0.9) + next_block.get("confidence", 0.9)) / 2
                }
            
            # If text length in same block is just the synonym, take next block
            if len(text) <= len(synonym) + 4:
                return {
                    "value": next_text,
                    "bbox": merged_bbox,
                    "bbox_pixels": merged_pixels,
                    "confidence": (block.get("confidence", 0.9) + next_block.get("confidence", 0.9)) / 2
                }

        # Default fallback: return current block text
        return {
            "value": text,
            "bbox": block.get("bbox_norm"),
            "bbox_pixels": block.get("bbox_pixels"),
            "confidence": block.get("confidence", 0.9)
        }

    def _merge_bboxes(self, b1: Dict[str, Any], b2: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, int]]:
        n1 = b1.get("bbox_norm", {"x": 0, "y": 0, "width": 0, "height": 0})
        n2 = b2.get("bbox_norm", {"x": 0, "y": 0, "width": 0, "height": 0})

        min_x = min(n1.get("x", 0), n2.get("x", 0))
        min_y = min(n1.get("y", 0), n2.get("y", 0))
        max_x = max(n1.get("x", 0) + n1.get("width", 0), n2.get("x", 0) + n2.get("width", 0))
        max_y = max(n1.get("y", 0) + n1.get("height", 0), n2.get("y", 0) + n2.get("height", 0))

        merged_norm = {
            "x": round(min_x, 4),
            "y": round(min_y, 4),
            "width": round(max_x - min_x, 4),
            "height": round(max_y - min_y, 4)
        }

        p1 = b1.get("bbox_pixels", {"x": 0, "y": 0, "width": 0, "height": 0})
        p2 = b2.get("bbox_pixels", {"x": 0, "y": 0, "width": 0, "height": 0})

        p_min_x = min(p1.get("x", 0), p2.get("x", 0))
        p_min_y = min(p1.get("y", 0), p2.get("y", 0))
        p_max_x = max(p1.get("x", 0) + p1.get("width", 0), p2.get("x", 0) + p2.get("width", 0))
        p_max_y = max(p1.get("y", 0) + p1.get("height", 0), p2.get("y", 0) + p2.get("height", 0))

        merged_pix = {
            "x": p_min_x,
            "y": p_min_y,
            "width": p_max_x - p_min_x,
            "height": p_max_y - p_min_y
        }

        return merged_norm, merged_pix

# Global instance
field_mapper = FieldMapper()
