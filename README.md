# RFx Crew — Kill the Quote Spreadsheet

Aerchain Product Management Take-Home Assignment.

One flow, end to end: draft an RFx → dispatch to 5 vendors → parse any format they send back → normalize to same units/currency → buyer asks questions in plain language → defensible award decision.

## Quick Start

**1. Install dependencies**
```
pip install -r requirements.txt
```

**2. Set your OpenAI API key**
```
# Windows
set OPENAI_API_KEY=sk-...

# Mac/Linux
export OPENAI_API_KEY=sk-...
```

**3. Generate the demo data (vendor responses)**
```
python data/seed_data.py
```

**4. Launch the UI**
```
streamlit run ui/app.py
```

Then open http://localhost:8501 in your browser. Enter your API key in the sidebar if not set via env var.

---

## The 5 Agents

| Agent | File | Responsibility |
|---|---|---|
| RFx Drafter | `agents/rfx_drafter.py` | AI co-pilot that drafts the RFx from buyer conversation |
| Vendor Dispatcher | `agents/vendor_dispatcher.py` | Packages RFx into emails, sends to 5 vendors (SMTP stubbed) |
| Document Parser | `agents/document_parser.py` | Reads vendor responses in any format (JSON/CSV/text) |
| Normalizer | `agents/normalizer.py` | Converts to same currency, same UOM, maps to 30 line items |
| Analyst | `agents/analyst.py` | Answers buyer natural-language questions over the comparison |

## The 5 Vendor Response Formats (Ugly Edges)

| Vendor | File | Format | Ugly Edge |
|---|---|---|---|
| PackRight Industries | `V1_PackRight_response.json` | JSON | Clean (best case) |
| BoxCraft Solutions | `V2_BoxCraft_response.csv` | CSV | 26/30 lines quoted; uses "per 100 pcs" UOM |
| GlobalPack Ltd | `V3_GlobalPack_response.txt` | PDF-style text | All in USD; freight charged separately |
| SwiftBox Pvt Ltd | `V4_SwiftBox_email.txt` | Email text | ₹X/kg rate reference; no template |
| CorreBox Manufacturing | `V5_CorreBox_response.txt` | Word-doc text | 28/30 lines; 2 items not in product range |

## CLI Demo (no UI)
```
python crew_pipeline.py
```
Runs the full pipeline then opens an interactive Q&A loop in the terminal.

## What Was Deliberately Left Out
See [DECISIONS.md](DECISIONS.md).
