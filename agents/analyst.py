"""
agents/analyst.py
Agent 5: Analyst
Assignment requirement: "the buyer stops clicking and starts asking. Natural language,
over the whole comparison. Text answers, tables, charts, exports."
"don't fake the reasoning, don't hardcode the answers to your demo questions"
This agent answers buyer questions over the normalized comparison matrix using real LLM reasoning.
"""

import json
from openai import OpenAI


class AnalystAgent:
    """
    Answers buyer natural-language questions over the comparison matrix.
    Assignment: "Real analysis on real extracted data, all the way to a defensible award decision."
    Uses the LLM to reason; never hardcodes answers.
    """

    def __init__(self, client: OpenAI):
        self.client = client
        self.comparison = None
        self.chat_history = []

    def load_comparison(self, comparison: dict):
        """Load the normalized comparison matrix."""
        self.comparison = comparison
        self.chat_history = []

    def _build_context_summary(self) -> str:
        """
        Build a compact, token-efficient JSON summary of the comparison for the LLM.
        The LLM reasons over real data — not hardcoded.
        """
        if not self.comparison:
            return "No comparison data loaded."

        matrix = self.comparison["matrix"]
        vendor_names = self.comparison["vendor_names"]
        qual_vendors = self.comparison["qualified_vendors"]
        vendor_summaries = self.comparison["vendor_summaries"]
        usd_rate = self.comparison.get("usd_rate", 83.5)

        # Build compact line-item table
        lines = []
        for lid in sorted(matrix.keys()):
            row = matrix[lid]
            entry = {
                "id": lid,
                "item": row["description"],
                "uom": row["canonical_uom"],
                "prices_inr": {},
                "flags": {},
            }
            for vid, vdata in row["vendors"].items():
                entry["prices_inr"][vid] = vdata["unit_price_inr"]
                if vdata["flags"] and vdata["flags"] != ["Not quoted"]:
                    entry["flags"][vid] = vdata["flags"]
            entry["cheapest_qualified"] = {
                "vendor": row.get("cheapest_qualified_vendor"),
                "price": row.get("cheapest_qualified_price"),
            }
            lines.append(entry)

        # Vendor summaries
        vendor_info = {}
        for vid, summary in vendor_summaries.items():
            vendor_info[vid] = {
                "name": summary["name"],
                "lines_quoted": summary["lines_quoted"],
                "lines_total": summary["lines_total"],
                "questionnaire": summary["questionnaire"],
                "notes": summary["extraction_notes"],
                "parse_method": summary["parse_method"],
                "flags": summary.get("vendor_flags", []),
            }

        context = {
            "usd_to_inr_rate_used": usd_rate,
            "qualified_vendors": qual_vendors,
            "vendor_names": vendor_names,
            "vendor_info": vendor_info,
            "line_items": lines,
        }

        return json.dumps(context, indent=2, ensure_ascii=False)

    def _system_prompt(self) -> str:
        context = self._build_context_summary()
        return f"""You are an expert procurement analyst. You have access to a normalized vendor comparison for a corrugated packaging RFx (30 line items, 5 vendors).

IMPORTANT RULES:
1. Base ALL answers on the actual data provided — never hallucinate or assume prices not in the data
2. When you're uncertain (e.g. vendor didn't quote a line), say so explicitly
3. For currency: all prices in the comparison are already in INR. GlobalPack (V3) originally quoted in USD and was converted at ₹{self.comparison.get('usd_rate', 83.5) if self.comparison else 83.5}/USD — flag this exchange rate risk when relevant
4. When a vendor quoted "per 100 pcs" and it was converted to "per piece", mention that the original UOM was different
5. Qualify your award recommendations — state what assumptions were made
6. The VP's question ("cheapest per line, among vendors who cleared the quality questionnaire") is a key analysis you should always be able to answer
7. Format tables using markdown when the answer benefits from it
8. For export requests, acknowledge and note that the UI will generate the file

COMPARISON DATA:
{context}"""

    def ask(self, question: str) -> str:
        """
        Answer a buyer's natural-language question.
        Assignment: "don't fake the reasoning, don't hardcode the answers"
        """
        self.chat_history.append({"role": "user", "content": question})

        messages = [{"role": "system", "content": self._system_prompt()}] + self.chat_history

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
        )

        answer = response.choices[0].message.content
        self.chat_history.append({"role": "assistant", "content": answer})
        return answer

    def get_award_recommendation(self) -> str:
        """
        Generate a defensible award decision.
        Assignment: "all the way to a defensible award decision"
        """
        prompt = """Generate a complete award recommendation for this RFx.

Structure your answer as:
1. Executive Summary (2-3 sentences)
2. Vendor Qualification Summary (who passed/failed questionnaire and why)
3. Recommended Award (line-by-line: vendor, price, any flags)
4. Total estimated spend (sum of cheapest qualified vendor × quantity per line)
5. Risk flags (lines where no qualified vendor quoted, UOM/currency conversion risks, low-confidence extractions)
6. What was deliberately left out or uncertain

Be honest about gaps. A buyer with ₹4 crore on the line needs to trust this."""

        return self.ask(prompt)

    def reset(self):
        """Reset conversation history (not the comparison data)."""
        self.chat_history = []
