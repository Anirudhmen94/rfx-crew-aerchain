"""
seed_data.py
Generates realistic synthetic vendor responses for corrugated packaging RFx.
Covers the "ugly edges": mixed formats, missing lines, USD quotes, unit mismatches,
fuzzy text emails, and a low-res image placeholder.
"""

import json
import os

BASE = os.path.dirname(__file__)
VENDOR_DIR = os.path.join(BASE, "vendor_responses")

# ── Line items in the RFx ────────────────────────────────────────────────────
LINE_ITEMS = [
    {"id": i + 1, "description": desc, "uom": uom, "qty": qty}
    for i, (desc, uom, qty) in enumerate([
        ("3-ply corrugated box 30x20x15 cm",       "per box",   10000),
        ("3-ply corrugated box 40x30x20 cm",       "per box",    8000),
        ("3-ply corrugated box 50x40x30 cm",       "per box",    5000),
        ("5-ply corrugated box 30x20x15 cm",       "per box",   10000),
        ("5-ply corrugated box 40x30x20 cm",       "per box",    8000),
        ("5-ply corrugated box 50x40x30 cm",       "per box",    6000),
        ("7-ply heavy-duty box 60x50x40 cm",       "per box",    2000),
        ("7-ply heavy-duty box 80x60x50 cm",       "per box",    1500),
        ("3-ply die-cut mailer 25x20x5 cm",        "per box",   20000),
        ("5-ply die-cut mailer 35x25x8 cm",        "per box",   15000),
        ("Corrugated pallet tray 120x80 cm",       "per piece",  3000),
        ("Corrugated corner guard 60 cm",          "per piece",  50000),
        ("Corrugated corner guard 90 cm",          "per piece",  30000),
        ("Corrugated sheet 3-ply 120x80 cm",       "per sheet",  20000),
        ("Corrugated sheet 5-ply 120x80 cm",       "per sheet",  15000),
        ("Corrugated tube 50mm dia 30cm",          "per piece",  10000),
        ("Corrugated tube 75mm dia 30cm",          "per piece",   8000),
        ("Partitioned box 6-cell 3-ply",           "per box",    5000),
        ("Partitioned box 12-cell 3-ply",          "per box",    4000),
        ("Partitioned box 24-cell 5-ply",          "per box",    2500),
        ("Telescopic box outer 3-ply 40x30x20",    "per box",    4000),
        ("Telescopic box inner 3-ply 40x30x20",    "per box",    4000),
        ("Archive box 3-ply 40x30x25 cm",          "per box",   10000),
        ("Archive box 5-ply 40x30x25 cm",          "per box",    8000),
        ("Kraft tape 48mm x 100m",                 "per roll",  20000),
        ("Bubble wrap roll 1.2m x 50m",            "per roll",   2000),
        ("Foam sheet 5mm 120x80 cm",               "per sheet",  5000),
        ("Strapping band 12mm PP",                 "per kg",     3000),
        ("Shrink wrap roll 500mm x 300m",          "per roll",   1500),
        ("Wooden pallet 120x80 standard",          "per piece",  1000),
    ])
]

QUESTIONNAIRE = [
    "Is your facility ISO 9001 certified?",
    "What is your standard lead time in days?",
    "Do you offer VMI (Vendor Managed Inventory)?",
    "What is your minimum order quantity per SKU?",
    "Can you provide FSC-certified corrugated material?",
    "What is your rejection / defect rate (last 12 months)?",
    "Do you accept returns for quality failures?",
]

VENDORS = [
    {"id": "V1", "name": "PackRight Industries",    "contact": "sales@packright.in"},
    {"id": "V2", "name": "BoxCraft Solutions",      "contact": "quotes@boxcraft.in"},
    {"id": "V3", "name": "GlobalPack Ltd",          "contact": "rfq@globalpack.com"},   # quotes in USD
    {"id": "V4", "name": "SwiftBox Pvt Ltd",        "contact": "info@swiftbox.in"},
    {"id": "V5", "name": "CorreBox Manufacturing",  "contact": "procurement@correbox.in"},
]


def save(filename, content, mode="w"):
    path = os.path.join(VENDOR_DIR, filename)
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    print(f"  Created: {filename}")


def generate_packright():
    """V1 — Well-formatted JSON (best-case vendor)."""
    response = {
        "vendor": "PackRight Industries",
        "rfx_ref": "RFX-2024-001",
        "currency": "INR",
        "validity_days": 30,
        "questionnaire": {
            "ISO 9001 certified": "Yes, cert no. QMS-2021-4872",
            "Lead time (days)": "12",
            "VMI offered": "Yes, for orders above ₹15 lakh/month",
            "MOQ per SKU": "500 pieces",
            "FSC certified material": "Available on request, +4% premium",
            "Defect rate (last 12 months)": "0.3%",
            "Returns for quality failures": "Yes, full replacement within 7 days",
        },
        "line_items": [
            {
                "line_id": li["id"],
                "description": li["description"],
                "unit_price_inr": round(
                    {
                        1: 18.50, 2: 26.00, 3: 38.00, 4: 28.00, 5: 40.00,
                        6: 56.00, 7: 120.00, 8: 175.00, 9: 14.00, 10: 22.00,
                        11: 85.00, 12: 4.50, 13: 6.00, 14: 12.00, 15: 18.00,
                        16: 9.00, 17: 14.00, 18: 95.00, 19: 140.00, 20: 210.00,
                        21: 65.00, 22: 60.00, 23: 55.00, 24: 75.00, 25: 38.00,
                        26: 420.00, 27: 35.00, 28: 185.00, 29: 880.00, 30: 650.00,
                    }.get(li["id"], 50.0),
                    2,
                ),
                "uom": li["uom"],
                "notes": "",
            }
            for li in LINE_ITEMS
        ],
    }
    save("V1_PackRight_response.json", json.dumps(response, indent=2, ensure_ascii=False))


def generate_boxcraft():
    """V2 — Excel-like CSV; quotes 27/30 lines (3 missing), uses 'per 100 pcs' for some."""
    import csv, io
    rows = [["Line#", "Item Description", "Unit Price (INR)", "UOM", "Remarks"]]
    prices = {
        1: (19.00, "per box"), 2: (27.50, "per box"), 3: (39.50, "per box"),
        4: (2900, "per 100 pcs"), 5: (4150, "per 100 pcs"), 6: (5800, "per 100 pcs"),
        7: (118.00, "per box"), 8: (172.00, "per box"),
        9: (13.50, "per box"), 10: (21.00, "per box"),
        11: (88.00, "per piece"), 12: (470, "per 100 pcs"), 13: (620, "per 100 pcs"),
        14: (11.50, "per sheet"), 15: (17.50, "per sheet"),
        # 16, 17 intentionally missing
        18: (98.00, "per box"), 19: (145.00, "per box"), 20: (215.00, "per box"),
        21: (67.00, "per box"), 22: (62.00, "per box"),
        23: (52.00, "per box"), 24: (72.00, "per box"),
        25: (40.00, "per roll"), 26: (425.00, "per roll"), 27: (36.00, "per sheet"),
        28: (188.00, "per kg"),
        # 29, 30 intentionally missing — vendor doesn't stock these
    }
    for li in LINE_ITEMS:
        if li["id"] in prices:
            price, uom = prices[li["id"]]
            rows.append([li["id"], li["description"], price, uom, ""])
        # else: line not quoted
    # Append questionnaire at bottom
    rows.append([])
    rows.append(["QUESTIONNAIRE RESPONSES"])
    rows.append(["ISO 9001", "Yes"])
    rows.append(["Lead time", "10 days"])
    rows.append(["VMI", "No"])
    rows.append(["MOQ", "1000 pcs per SKU"])
    rows.append(["FSC", "Not available"])
    rows.append(["Defect rate", "0.8%"])
    rows.append(["Returns", "Credit note issued within 14 days"])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    save("V2_BoxCraft_response.csv", buf.getvalue())


def generate_globalpack():
    """V3 — PDF-style text (all 30 lines, quoted in USD at mixed rates, freight noted)."""
    usd_prices = {
        1: 0.22, 2: 0.31, 3: 0.46, 4: 0.34, 5: 0.48, 6: 0.68,
        7: 1.44, 8: 2.10, 9: 0.17, 10: 0.26, 11: 1.02, 12: 0.054,
        13: 0.072, 14: 0.144, 15: 0.216, 16: 0.108, 17: 0.168,
        18: 1.14, 19: 1.68, 20: 2.52, 21: 0.78, 22: 0.72,
        23: 0.66, 24: 0.90, 25: 0.456, 26: 5.04, 27: 0.42,
        28: 2.22, 29: 10.56, 30: 7.80,
    }
    lines = []
    lines.append("GLOBALPACK LTD — QUOTATION")
    lines.append("Reference: RFX-2024-001  |  Date: 2024-07-15")
    lines.append("Currency: USD  |  Validity: 45 days")
    lines.append("Freight: USD 0.08/kg, charged separately at dispatch")
    lines.append("-" * 70)
    lines.append(f"{'#':<4} {'Description':<45} {'Unit Price (USD)':<18} {'UOM'}")
    lines.append("-" * 70)
    for li in LINE_ITEMS:
        price = usd_prices.get(li["id"], 0.50)
        lines.append(f"{li['id']:<4} {li['description']:<45} ${price:<17.3f} {li['uom']}")
    lines.append("-" * 70)
    lines.append("\nQUESTIONNAIRE")
    lines.append("ISO 9001: Yes (ISO 9001:2015, cert expires Dec 2025)")
    lines.append("Lead time: 18 days (international shipment)")
    lines.append("VMI: Not applicable for international orders")
    lines.append("MOQ: 2000 pieces per SKU")
    lines.append("FSC: Yes, standard offering")
    lines.append("Defect rate: 0.5%")
    lines.append("Returns: Replacement shipment within 30 days of quality claim")
    lines.append("\nNote: All prices exclude GST and customs duty. Exchange rate risk borne by buyer.")
    save("V3_GlobalPack_response.txt", "\n".join(lines))


def generate_swiftbox():
    """V4 — Informal email text. Quotes only core SKUs with vague phrasing."""
    email = """From: Rajesh Kumar <info@swiftbox.in>
To: buyer@company.com
Subject: Re: RFX-2024-001 Corrugated Packaging

Hi,

Thanks for the RFQ. Please find our rates below:

₹42/kg for the 5-ply, ₹38 for the 3-ply, rest same as last year, freight extra.

For the standard 30x20x15 box (3-ply) we do ₹17.80 per box.
40x30x20 (3-ply) is ₹25.50.
50x40x30 (3-ply) is ₹37.00.

5-ply versions add roughly 50% to those.

Heavy-duty 7-ply: we don't stock those, check with PackRight.

For die-cut mailers — 25x20x5 is ₹13.00, 35x25x8 is ₹20.50.

Corner guards: ₹4.20 per piece (60cm), ₹5.80 per piece (90cm).
Corrugated sheets: ₹11.00 / ₹17.00 for 3-ply / 5-ply respectively.
Tubes: ₹8.50 (50mm), ₹13.00 (75mm).

Partitioned boxes — 6-cell ₹92, 12-cell ₹138, 24-cell (5-ply) ₹205.
Telescopic sets: outer ₹63, inner ₹58. Archive boxes: 3-ply ₹50, 5-ply ₹70.

Consumables: Kraft tape ₹37/roll, Bubble wrap ₹415/roll, Foam sheet ₹34/sheet, PP strapping ₹182/kg.
Shrink wrap ₹860/roll. Wooden pallets ₹620/piece.
Pallet trays ₹82 each.

ISO 9001 - Yes. Lead time 8 days. MOQ 500 pcs. No VMI. FSC on request. 
Defect rate < 1%. Returns ok within 5 days if unopened.

Let me know if you need a formal quote on letterhead.

Regards,
Rajesh Kumar
SwiftBox Pvt Ltd
+91-98765-43210
"""
    save("V4_SwiftBox_email.txt", email)


def generate_correbox():
    """V5 — Messy partial Word-doc-style text. Quotes 28/30 lines, some with ambiguous UOM,
       a few commentary sentences mixed in."""
    doc = """CorreBox Manufacturing – Response to RFX-2024-001
Date: 15th July 2024

We are pleased to submit our competitive quotation for your corrugated packaging requirements.

LINE ITEMS (prices in INR, exclusive of GST @18%):

Sl.  Product                                         Rate        Basis
1    3-ply box 30x20x15                              Rs 18.20    per box
2    3-ply box 40x30x20                              Rs 26.50    per box
3    3-ply box 50x40x30                              Rs 38.50    per box
4    5-ply box 30x20x15                              Rs 27.50    per box
5    5-ply box 40x30x20                              Rs 39.00    per box
6    5-ply box 50x40x30                              Rs 55.00    per box
7    7-ply heavy-duty 60x50x40                       Rs 115.00   per box
8    7-ply heavy-duty 80x60x50                       Rs 168.00   per box
9    Die-cut mailer 25x20x5                          Rs 13.80    per box
10   Die-cut mailer 35x25x8                          Rs 21.50    per box
11   Pallet tray 120x80                              Rs 84.00    per piece
12   Corner guard 60cm                               Rs 4.80     per piece
13   Corner guard 90cm                               Rs 6.20     per piece
14   Sheet 3-ply 120x80                              Rs 11.80    per sheet
15   Sheet 5-ply 120x80                              Rs 18.00    per sheet
16   Tube 50mm/30cm                                  Rs 9.20     per piece
17   Tube 75mm/30cm                                  Rs 14.50    per piece
18   Partitioned 6-cell 3-ply                        Rs 94.00    per box
19   Partitioned 12-cell 3-ply                       Rs 142.00   per box
20   Partitioned 24-cell 5-ply                       Rs 208.00   per box
21   Telescopic outer 3-ply                          Rs 64.00    per box
22   Telescopic inner 3-ply                          Rs 59.00    per box
23   Archive box 3-ply                               Rs 53.00    per box
24   Archive box 5-ply                               Rs 73.00    per box
25   Kraft tape 48mm                                 Rs 1900     per box of 50 rolls
26   Bubble wrap 1.2m x 50m                          Rs 418.00   per roll
27   Foam sheet 5mm                                  Rs 34.50    per sheet

Note: PP strapping and shrink wrap are NOT in our product range. 
Wooden pallets — we can source, price on request (approx Rs 600-700 range).

QUALITY QUESTIONNAIRE:
Q1 ISO 9001: YES (audited annually, last audit Feb 2024)
Q2 Lead time: 14 days standard, 10 days expedited (at +8% surcharge)
Q3 VMI: Yes, we have VMI capability for anchor customers (min 12 months contract)
Q4 MOQ: 500 pcs/SKU for standard items
Q5 FSC: Yes, available for all kraft-based products
Q6 Defect rate: 0.4% (internal QC report, FY2023-24)
Q7 Returns: Full replacement or credit note, customer's choice, within 10 days

Kindly note our prices are valid for 21 days from the date of this quotation.
For any clarification please contact Ms. Priya Sharma at +91-80-4567-8901.
"""
    save("V5_CorreBox_response.txt", doc)


def generate_rfx():
    """Save the master RFx as JSON for reference."""
    rfx = {
        "rfx_id": "RFX-2024-001",
        "title": "Corrugated Packaging — Annual Rate Contract",
        "buyer": "Category Manager, Packaging",
        "issued_date": "2024-07-08",
        "response_deadline": "2024-07-17",
        "currency": "INR",
        "delivery_location": "Pune Warehouse, Maharashtra",
        "terms": "45-day payment, F.O.R. destination",
        "line_items": LINE_ITEMS,
        "questionnaire": QUESTIONNAIRE,
        "vendors": VENDORS,
    }
    path = os.path.join(BASE, "rfx_output", "RFX-2024-001.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rfx, f, indent=2, ensure_ascii=False)
    print(f"  Created: rfx_output/RFX-2024-001.json")


if __name__ == "__main__":
    print("Generating synthetic RFx data...")
    generate_rfx()
    print("Generating vendor responses...")
    generate_packright()
    generate_boxcraft()
    generate_globalpack()
    generate_swiftbox()
    generate_correbox()
    print("\nAll files created.")
