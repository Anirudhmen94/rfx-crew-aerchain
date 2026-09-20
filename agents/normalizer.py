"""
agents/normalizer.py
Agent 4: Normalizer
Assignment requirement: "lands them all in a single side-by-side comparison —
same lines, same units, same currency"
Assignment ugly edges handled here:
- "The one who quoted in USD" → convert to INR
- "whose 'per box' is someone else's 'per 100 pieces'" → normalize UOM
- "vendor who quoted 27 of 30 lines" → mark missing as None
- Ambiguous references like '5-ply add 50%' → flag with confidence
"""

import json
import os
from typing import Optional
import anthropic

# Reference: 30 RFx line items (canonical IDs and descriptions)
RFX_LINE_ITEMS = [
    {"id": i + 1, "description": desc, "canonical_uom": uom}
    for i, (desc, uom) in enumerate([
        ("3-ply corrugated box 30x20x15 cm",       "per box"),
        ("3-ply corrugated box 40x30x20 cm",       "per box"),
        ("3-ply corrugated box 50x40x30 cm",       "per box"),
        ("5-ply corrugated box 30x20x15 cm",       "per box"),
        ("5-ply corrugated box 40x30x20 cm",       "per box"),
        ("5-ply corrugated box 50x40x30 cm",       "per box"),
        ("7-ply heavy-duty box 60x50x40 cm",       "per box"),
        ("7-ply heavy-duty box 80x60x50 cm",       "per box"),
        ("3-ply die-cut mailer 25x20x5 cm",        "per box"),
        ("5-ply die-cut mailer 35x25x8 cm",        "per box"),
        ("Corrugated pallet tray 120x80 cm",       "per piece"),
        ("Corrugated corner guard 60 cm",          "per piece"),
        ("Corrugated corner guard 90 cm",          "per piece"),
        ("Corrugated sheet 3-ply 120x80 cm",       "per sheet"),
        ("Corrugated sheet 5-ply 120x80 cm",       "per sheet"),
        ("Corrugated tube 50mm dia 30cm",          "per piece"),
        ("Corrugated tube 75mm dia 30cm",          "per piece"),
        ("Partitioned box 6-cell 3-ply",           "per box"),
        ("Partitioned box 12-cell 3-ply",          "per box"),
        ("Partitioned box 24-cell 5-ply",          "per box"),
        ("Telescopic box outer 3-ply 40x30x20",    "per box"),
        ("Telescopic box inner 3-ply 40x30x20",    "per box"),
        ("Archive box 3-ply 40x30x25 cm",          "per box"),
        ("Archive box 5-ply 40x30x25 cm",          "per box"),
        ("Kraft tape 48mm x 100m",                 "per roll"),
        ("Bubble wrap roll 1.2m x 50m",            "per roll"),
        ("Foam sheet 5mm 120x80 cm",               "per sheet"),
        ("Strapping band 12mm PP",                 "per kg"),
        ("Shrink wrap roll 500mm x 300m",          "per roll"),
        ("Wooden pallet 120x80 standard",          "per piece"),
    ])
]

# UOM conversion factors to canonical UOM
# Key: (quoted_uom, canonical_uom) → multiplier
# "per 100 pcs" → "per box" means divide by 100
UOM_CONVERSIONS = {
    ("per 100 pcs", "per box"): 1 / 100,
    ("per 100 pcs", "per piece"): 1 / 100,
    ("per box of 50 rolls", "per roll"): 1 / 50,
    ("per 100 pieces", "per piece"): 1 / 100,
    ("per 100 pieces", "per box"): 1 / 100,
}

# USD → INR exchange rate (fixed for demo; in production, fetch live)
USD_TO_INR = 83.5


class NormalizerAgent:
    """
    Takes raw extracted data from all vendors and normalizes to:
    - Common currency (INR)
    - Common unit of measure (per RFx canonical UOM)
    - Matched to the 30 RFx line items by ID or fuzzy description match
    Assignment: "same lines, same units, same currency"
    """

    def __init__(self, client: anthropic.Anthropic, usd_to_inr: float = USD_TO_INR):
        self.client = client
        self.usd_to_inr = usd_to_inr

    def _convert_currency(self, price: float, from_currency: str) -> tuple[float, str]:
        """Convert price to INR. Returns (inr_price, conversion_note)."""
        if from_currency.upper() == "USD":
            inr = price * self.usd_to_inr
            note = f"Converted from USD at ₹{self.usd_to_inr}/USD"
            return inr, note
        return price, ""

    def _normalize_uom(
        self, price: float, quoted_uom: str, canonical_uom: str
    ) -> tuple[float, str, str]:
        """
        Normalize price to canonical UOM. Returns (normalized_price, normalized_uom, flag).
        Assignment ugly edge: 'per box' vs 'per 100 pieces'
        """
        quoted_lower = quoted_uom.lower().strip()
        canonical_lower = canonical_uom.lower().strip()

        if quoted_lower == canonical_lower:
            return price, canonical_uom, ""

        # Check known conversion table
        factor = UOM_CONVERSIONS.get((quoted_lower, canonical_lower))
        if factor is not None:
            normalized = price * factor
            flag = f"UOM converted: {quoted_uom} → {canonical_uom} (×{factor:.4f})"
            return normalized, canonical_uom, flag

        # Unknown conversion — flag it for buyer attention
        flag = f"⚠️ UOM mismatch: vendor quoted '{quoted_uom}', RFx expects '{canonical_uom}'. Manual verification needed."
        return price, quoted_uom, flag

    def _match_line_item(self, raw_item: dict) -> Optional[dict]:
        """
        Match a raw extracted line item to an RFx line item.
        Uses line_id if present; falls back to description matching.
        """
        # Try exact ID match first
        line_id = raw_item.get("line_id")
        if line_id:
            try:
                lid = int(line_id)
                for rfx_li in RFX_LINE_ITEMS:
                    if rfx_li["id"] == lid:
                        return rfx_li
            except (ValueError, TypeError):
                pass

        # Fall back to fuzzy description match (simple keyword overlap)
        raw_desc = raw_item.get("description", "").lower()
        best_match = None
        best_score = 0
        for rfx_li in RFX_LINE_ITEMS:
            rfx_desc = rfx_li["description"].lower()
            # Score: count shared words
            raw_words = set(raw_desc.split())
            rfx_words = set(rfx_desc.split())
            score = len(raw_words & rfx_words)
            if score > best_score:
                best_score = score
                best_match = rfx_li

        if best_score >= 2:
            return best_match
        return None

    def normalize_vendor(self, raw: dict) -> dict:
        """
        Normalize one vendor's raw extraction.
        Returns a dict keyed by RFx line_id with normalized prices.
        """
        vendor_currency = raw.get("currency", "INR").upper()
        normalized_lines = {}
        flags = []

        for raw_item in raw.get("line_items_raw", []):
            price = raw_item.get("unit_price")
            if price is None:
                continue

            # Match to RFx line item
            rfx_li = self._match_line_item(raw_item)
            if rfx_li is None:
                flags.append(f"Could not match '{raw_item.get('description')}' to any RFx line")
                continue

            line_id = rfx_li["id"]
            item_currency = raw_item.get("currency", vendor_currency)
            canonical_uom = rfx_li["canonical_uom"]
            quoted_uom = raw_item.get("uom", canonical_uom)

            # Step 1: Currency normalization
            price_inr, currency_note = self._convert_currency(price, item_currency)

            # Step 2: UOM normalization
            price_norm, uom_norm, uom_flag = self._normalize_uom(price_inr, quoted_uom, canonical_uom)

            item_flags = []
            if currency_note:
                item_flags.append(currency_note)
            if uom_flag:
                item_flags.append(uom_flag)
            if raw_item.get("notes"):
                item_flags.append(raw_item["notes"])

            normalized_lines[line_id] = {
                "line_id": line_id,
                "description": rfx_li["description"],
                "unit_price_inr": round(price_norm, 2),
                "uom": uom_norm,
                "original_price": price,
                "original_uom": quoted_uom,
                "original_currency": item_currency,
                "flags": item_flags,
                "confidence": raw_item.get("confidence", "medium"),
            }

        # Normalize questionnaire answers
        q_raw = raw.get("questionnaire_raw", {})
        questionnaire_normalized = {}
        if isinstance(q_raw, dict):
            # Map to standard questions
            std_keys = {
                "iso": "ISO 9001 certified",
                "lead": "Lead time (days)",
                "vmi": "VMI offered",
                "moq": "MOQ per SKU",
                "fsc": "FSC certified material",
                "defect": "Defect rate",
                "return": "Returns policy",
            }
            for raw_key, raw_val in q_raw.items():
                matched = False
                for kw, std_q in std_keys.items():
                    if kw in raw_key.lower():
                        questionnaire_normalized[std_q] = raw_val
                        matched = True
                        break
                if not matched:
                    questionnaire_normalized[raw_key] = raw_val

        return {
            "vendor_id": raw.get("vendor_id"),
            "vendor_name": raw.get("vendor_name"),
            "currency_used": vendor_currency,
            "usd_rate_applied": self.usd_to_inr if vendor_currency == "USD" else None,
            "lines": normalized_lines,
            "questionnaire": questionnaire_normalized,
            "extraction_confidence": raw.get("confidence", "medium"),
            "extraction_notes": raw.get("extraction_notes", ""),
            "parse_method": raw.get("parse_method"),
            "source_file": raw.get("source_file"),
            "vendor_flags": flags,
        }

    def build_comparison_matrix(self, normalized_vendors: list) -> dict:
        """
        Build the side-by-side comparison matrix.
        Assignment: 'single side-by-side comparison — same lines, same units, same currency'
        Marks missing lines explicitly. Shows questionnaire pass/fail.
        """
        # Build matrix: line_id → {vendor_id: {price, flags}}
        matrix = {}
        for rfx_li in RFX_LINE_ITEMS:
            lid = rfx_li["id"]
            matrix[lid] = {
                "description": rfx_li["description"],
                "canonical_uom": rfx_li["canonical_uom"],
                "vendors": {},
            }

        vendor_names = {}
        for v in normalized_vendors:
            vid = v["vendor_id"] or v["vendor_name"]
            vendor_names[vid] = v["vendor_name"]
            for lid, item in v["lines"].items():
                if lid in matrix:
                    matrix[lid]["vendors"][vid] = {
                        "unit_price_inr": item["unit_price_inr"],
                        "flags": item["flags"],
                        "confidence": item["confidence"],
                        "original_price": item["original_price"],
                        "original_currency": item["original_currency"],
                        "original_uom": item["original_uom"],
                    }
            # Mark missing lines explicitly
            quoted_ids = set(v["lines"].keys())
            for rfx_li in RFX_LINE_ITEMS:
                lid = rfx_li["id"]
                if lid not in quoted_ids and vid not in matrix[lid]["vendors"]:
                    matrix[lid]["vendors"][vid] = {
                        "unit_price_inr": None,
                        "flags": ["Not quoted"],
                        "confidence": "none",
                        "original_price": None,
                        "original_currency": None,
                        "original_uom": None,
                    }

        # Add cheapest-per-line analysis
        # Assignment: "cheapest per line, but only among vendors who cleared the quality questionnaire"
        qual_vendors = self._get_qualified_vendors(normalized_vendors)

        for lid, row in matrix.items():
            prices = {
                vid: row["vendors"][vid]["unit_price_inr"]
                for vid in qual_vendors
                if vid in row["vendors"] and row["vendors"][vid]["unit_price_inr"] is not None
            }
            if prices:
                cheapest_vid = min(prices, key=prices.get)
                row["cheapest_qualified_vendor"] = cheapest_vid
                row["cheapest_qualified_price"] = prices[cheapest_vid]
            else:
                row["cheapest_qualified_vendor"] = None
                row["cheapest_qualified_price"] = None

        return {
            "matrix": matrix,
            "vendor_names": vendor_names,
            "qualified_vendors": qual_vendors,
            "usd_rate": self.usd_to_inr,
            "vendor_summaries": {
                v["vendor_id"]: {
                    "name": v["vendor_name"],
                    "lines_quoted": len(v["lines"]),
                    "lines_total": len(RFX_LINE_ITEMS),
                    "questionnaire": v["questionnaire"],
                    "extraction_notes": v["extraction_notes"],
                    "vendor_flags": v["vendor_flags"],
                    "parse_method": v["parse_method"],
                }
                for v in normalized_vendors
            },
        }

    def _get_qualified_vendors(self, normalized_vendors: list) -> list:
        """
        Determine which vendors cleared the quality questionnaire.
        A vendor is qualified if they answered 'Yes' to ISO 9001 certification.
        Assignment: "cheapest per line, but only among vendors who cleared the quality questionnaire"
        """
        qualified = []
        for v in normalized_vendors:
            q = v.get("questionnaire", {})
            iso_answer = q.get("ISO 9001 certified", "").lower()
            if "yes" in iso_answer or "certified" in iso_answer:
                qualified.append(v["vendor_id"])
        return qualified
