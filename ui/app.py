"""
ui/app.py
Streamlit buyer interface — Streamlit Cloud compatible.
Assignment requirement:
- "buyer stops clicking and starts asking" → chat interface
- "Text answers, tables, charts, exports" → all four in the UI
- "ready for a live demo we'll drive with you" → fully interactive
"""

import json
import os
import sys
import io

import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crew_pipeline import RFxCrew
from agents.normalizer import RFX_LINE_ITEMS

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RFx Analyzer — Aerchain Demo",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "rfx_output")
VENDOR_DIR = os.path.join(BASE_DIR, "data", "vendor_responses")

VENDOR_DISPLAY = {
    "V1": "PackRight Industries",
    "V2": "BoxCraft Solutions",
    "V3": "GlobalPack Ltd (USD→INR)",
    "V4": "SwiftBox Pvt Ltd",
    "V5": "CorreBox Manufacturing",
}

DEMO_QUESTIONS = [
    "Which vendor is cheapest overall?",
    "Split by cheapest per line, qualified vendors only?",
    "How does GlobalPack's USD quote affect the award?",
    "BoxCraft skipped lines 16 and 17 — what are our options?",
    "Which vendors passed the quality questionnaire?",
    "Total estimated spend per vendor if we award everything they quoted?",
    "What's the risk if we award everything to the cheapest vendor?",
]

# ── Resolve API key ───────────────────────────────────────────────────────────
def resolve_api_key() -> str:
    """Check Streamlit secrets first (Cloud deployment), then env var, then session state."""
    # Streamlit Cloud: key stored in app secrets
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    # Local: env var
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    # UI input (fallback for local dev)
    return st.session_state.get("api_key", "")


# ── Session state helpers ─────────────────────────────────────────────────────
def get_crew() -> RFxCrew:
    if "crew" not in st.session_state:
        api_key = resolve_api_key()
        if not api_key:
            return None
        with st.spinner("🔄 Running pipeline: parsing vendor responses & normalizing..."):
            crew = RFxCrew(openai_api_key=api_key)
            crew.run_full_pipeline(use_existing_rfx=True)
        st.session_state["crew"] = crew
    return st.session_state["crew"]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 RFx Analyzer")
    st.caption("Aerchain Product Demo")
    st.divider()

    # Only show API key input if not resolved from secrets/env
    auto_key = resolve_api_key()
    if not auto_key:
        st.markdown("### ⚙️ Configuration")
        api_key_input = st.text_input(
            "OpenAI API Key",
            value="",
            type="password",
            help="Enter your OpenAI API key to run the AI agents",
            placeholder="sk-...",
        )
        if api_key_input:
            st.session_state["api_key"] = api_key_input
    else:
        st.success("✅ API key configured")

    st.divider()
    st.markdown("### 📋 RFx Details")
    rfx_path = os.path.join(OUTPUT_DIR, "RFX-2024-001.json")
    if os.path.exists(rfx_path):
        with open(rfx_path) as f:
            rfx_meta = json.load(f)
        st.markdown(f"**ID:** `{rfx_meta.get('rfx_id', '—')}`")
        st.markdown(f"**Category:** Corrugated Packaging")
        st.markdown(f"**Vendors:** {len(rfx_meta.get('vendors', []))}")
        st.markdown(f"**Line items:** {len(rfx_meta.get('line_items', []))}")
        st.markdown(f"**Deadline:** {rfx_meta.get('response_deadline', '—')}")

    st.divider()
    if st.button("🔄 Re-run Pipeline", use_container_width=True):
        if "crew" in st.session_state:
            del st.session_state["crew"]
        if "chat_history" in st.session_state:
            del st.session_state["chat_history"]
        if "award_rec" in st.session_state:
            del st.session_state["award_rec"]
        st.rerun()

    st.divider()
    st.markdown("**Assumptions:**")
    st.caption("• USD→INR at ₹83.50 (fixed for demo)")
    st.caption("• SMTP stubbed (no real email sent)")
    st.caption("• Qualification = ISO 9001 Yes")


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("Kill the Quote Spreadsheet")
st.markdown(
    "**One flow, end to end:** AI co-pilot drafts the RFx → dispatches to 5 vendors → "
    "reads whatever they send back → normalizes to same units & currency → "
    "buyer asks in plain language → defensible award decision."
)
st.divider()

# Load pipeline
api_key = resolve_api_key()
if not api_key:
    st.warning("👈 Enter your OpenAI API key in the sidebar to start the demo.")
    st.stop()

crew = get_crew()
if crew is None:
    st.error("Could not initialize crew. Check your API key.")
    st.stop()

comparison = crew.comparison
matrix = comparison["matrix"]
vendor_ids = sorted(comparison["vendor_names"].keys())
qual_ids = comparison["qualified_vendors"]
rfx_qty = {li["id"]: li["qty"] for li in RFX_LINE_ITEMS}

# ── Pipeline status banner ────────────────────────────────────────────────────
with st.expander("✅ Pipeline complete — see what each agent did", expanded=False):
    vendor_summaries = comparison.get("vendor_summaries", {})
    cols = st.columns(5)
    steps = [
        ("1️⃣ RFx Drafter", "Drafted RFX-2024-001\n30 line items, 5 vendors"),
        ("2️⃣ Dispatcher", "Sent to 5 vendors\n(SMTP stubbed)"),
        ("3️⃣ Parser", "\n".join(
            f"{vid}: {s['parse_method'].replace('_', ' ')}"
            for vid, s in sorted(vendor_summaries.items())
        )),
        ("4️⃣ Normalizer", "USD→INR converted\nUOM mismatches flagged\nMissing lines marked"),
        ("5️⃣ Analyst", "Ready for Q&A\nGPT-4o reasoning\nReal data only"),
    ]
    for i, (title, detail) in enumerate(steps):
        with cols[i]:
            st.markdown(f"**{title}**")
            st.caption(detail)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_compare, tab_chat, tab_award, tab_debug = st.tabs([
    "📊 Comparison", "💬 Ask the Analyst", "🏆 Award Decision", "🔍 Extraction Debug"
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1: Comparison Table
# ════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.subheader("Side-by-Side Vendor Comparison")
    st.caption(
        "All prices in **INR**. GlobalPack originally quoted in USD (converted at ₹83.50). "
        "⚠ = UOM converted  |  $ = originally in USD  |  ? = low confidence  |  — = not quoted"
    )

    # Vendor qualification row
    qual_cols = st.columns(len(vendor_ids))
    for i, vid in enumerate(vendor_ids):
        with qual_cols[i]:
            name = VENDOR_DISPLAY.get(vid, vid).split(" (")[0]
            if vid in qual_ids:
                st.success(f"✅ {name}\nQualified")
            else:
                st.error(f"❌ {name}\nNot qualified")

    st.markdown("")

    # Build DataFrame
    rows = []
    for lid in sorted(matrix.keys()):
        row = matrix[lid]
        entry = {"#": lid, "Item": row["description"], "UOM": row["canonical_uom"]}
        for vid in vendor_ids:
            vdata = row["vendors"].get(vid, {})
            price = vdata.get("unit_price_inr")
            flags = vdata.get("flags", [])
            conf = vdata.get("confidence", "")
            if price is None:
                cell = "—"
            else:
                cell = f"₹{price:,.2f}"
                if any("UOM converted" in f for f in flags):
                    cell += " ⚠"
                if vdata.get("original_currency") == "USD":
                    cell += " $"
                if conf == "low":
                    cell += " ?"
            short_name = VENDOR_DISPLAY.get(vid, vid).split(" (")[0]
            entry[short_name] = cell

        cheap_vid = row.get("cheapest_qualified_vendor")
        cheap_price = row.get("cheapest_qualified_price")
        if cheap_vid and cheap_price:
            short = VENDOR_DISPLAY.get(cheap_vid, cheap_vid).split(" (")[0]
            entry["Best (Qual.)"] = f"{short}: ₹{cheap_price:,.2f}"
        else:
            entry["Best (Qual.)"] = "—"
        rows.append(entry)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=550)

    # Coverage summary
    st.markdown("**Coverage summary:**")
    cov_cols = st.columns(len(vendor_ids))
    for i, vid in enumerate(vendor_ids):
        quoted = sum(
            1 for row in matrix.values()
            if row["vendors"].get(vid, {}).get("unit_price_inr") is not None
        )
        short = VENDOR_DISPLAY.get(vid, vid).split(" (")[0]
        with cov_cols[i]:
            pct = quoted / 30 * 100
            color = "green" if pct == 100 else ("orange" if pct >= 87 else "red")
            st.markdown(f":{color}[**{short}**: {quoted}/30 lines]")

    st.divider()

    # Spend chart
    st.subheader("Estimated Total Spend by Vendor")
    st.caption("Unit price × RFx quantity for all quoted lines. Lower = cheaper if they quoted everything.")
    spend_data = {}
    for vid in vendor_ids:
        total = sum(
            matrix[lid]["vendors"].get(vid, {}).get("unit_price_inr", 0) * rfx_qty.get(lid, 0)
            for lid in matrix
            if matrix[lid]["vendors"].get(vid, {}).get("unit_price_inr") is not None
        )
        spend_data[VENDOR_DISPLAY.get(vid, vid).split(" (")[0]] = round(total / 1e5, 2)

    spend_df = pd.DataFrame(list(spend_data.items()), columns=["Vendor", "₹ Lakh"]).sort_values("₹ Lakh")
    st.bar_chart(spend_df.set_index("Vendor"))

    st.divider()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button(
        "⬇️ Download Comparison CSV",
        data=buf.getvalue().encode("utf-8"),
        file_name="rfx_comparison.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2: Analyst Chat
# ════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.subheader("Ask the Analyst")
    st.caption(
        "Real AI reasoning (GPT-4o) over real extracted data. "
        "Answers are grounded in the comparison — not hardcoded."
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Demo question chips
    st.markdown("**Try these questions:**")
    q_cols = st.columns(4)
    for i, dq in enumerate(DEMO_QUESTIONS):
        with q_cols[i % 4]:
            label = dq[:42] + ("…" if len(dq) > 42 else "")
            if st.button(label, key=f"dq_{i}", use_container_width=True):
                st.session_state["pending_question"] = dq

    st.divider()

    # Chat history
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending = st.session_state.pop("pending_question", None)
    question = st.chat_input("Ask about the vendor comparison…") or pending

    if question:
        st.session_state["chat_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing…"):
                answer = crew.analyst.ask(question)
            st.markdown(answer)
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state["chat_history"]:
        if st.button("🗑 Clear chat", use_container_width=True):
            st.session_state["chat_history"] = []
            crew.analyst.reset()
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 3: Award Recommendation
# ════════════════════════════════════════════════════════════════════════════
with tab_award:
    st.subheader("Award Recommendation")
    st.caption(
        "AI-generated, grounded in the comparison data. "
        "Covers qualification status, pricing, coverage gaps, and risk flags."
    )

    if "award_rec" not in st.session_state:
        if st.button("Generate Award Recommendation", type="primary", use_container_width=True):
            with st.spinner("Generating defensible award recommendation…"):
                rec = crew.analyst.get_award_recommendation()
            st.session_state["award_rec"] = rec
            st.rerun()
    else:
        st.markdown(st.session_state["award_rec"])
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Download as TXT",
                data=st.session_state["award_rec"].encode("utf-8"),
                file_name="award_recommendation.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with c2:
            if st.button("🔄 Regenerate", use_container_width=True):
                del st.session_state["award_rec"]
                crew.analyst.reset()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 4: Extraction Debug
# "What does your system show the buyer when it isn't sure?"
# ════════════════════════════════════════════════════════════════════════════
with tab_debug:
    st.subheader("Extraction & Normalization Debug")
    st.caption(
        "This tab shows exactly how each vendor's response was parsed and every flag raised. "
        "A buyer with ₹4 crore on the line should be able to see every assumption the system made."
    )

    vendor_summaries = comparison.get("vendor_summaries", {})
    for vid in sorted(vendor_summaries.keys()):
        v = vendor_summaries[vid]
        quoted = len([
            lid for lid in matrix
            if matrix[lid]["vendors"].get(vid, {}).get("unit_price_inr") is not None
        ])
        with st.expander(
            f"{VENDOR_DISPLAY.get(vid, vid)} — {quoted}/30 lines  |  Method: {v['parse_method']}",
            expanded=False,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Questionnaire Answers:**")
                if v["questionnaire"]:
                    for k, val in v["questionnaire"].items():
                        st.markdown(f"- **{k}:** {val}")
                else:
                    st.warning("No questionnaire data extracted")

            with col2:
                st.markdown("**Vendor-level Flags:**")
                flags = v.get("flags", [])
                if flags:
                    for fl in flags:
                        st.warning(fl)
                else:
                    st.success("No flags")
                if v.get("extraction_notes"):
                    st.info(f"**Extraction notes:** {v['extraction_notes']}")

            # Per-line flags
            line_flags = []
            for lid in sorted(matrix.keys()):
                row = matrix[lid]
                vdata = row["vendors"].get(vid, {})
                item_flags = [f for f in vdata.get("flags", []) if f and f != "Not quoted"]
                if item_flags:
                    line_flags.append({
                        "#": lid,
                        "Item": row["description"],
                        "Flags": " | ".join(item_flags),
                    })
            if line_flags:
                st.markdown("**Per-line flags:**")
                st.dataframe(pd.DataFrame(line_flags), use_container_width=True, hide_index=True)

            # Not-quoted lines
            not_quoted = [
                f"#{lid} {matrix[lid]['description']}"
                for lid in sorted(matrix.keys())
                if matrix[lid]["vendors"].get(vid, {}).get("unit_price_inr") is None
            ]
            if not_quoted:
                st.markdown(f"**Not quoted ({len(not_quoted)} lines):**")
                st.caption(", ".join(not_quoted[:10]) + (f" … +{len(not_quoted)-10} more" if len(not_quoted) > 10 else ""))
