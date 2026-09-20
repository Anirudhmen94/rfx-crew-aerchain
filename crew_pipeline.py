"""
crew_pipeline.py
The main crew pipeline — wires all 5 agents together.
Uses Anthropic Claude throughout.
Assignment: "One flow, end to end."
"""

import json
import os
import sys

import anthropic

sys.path.insert(0, os.path.dirname(__file__))

from agents.rfx_drafter import RFxDrafterAgent
from agents.vendor_dispatcher import VendorDispatcherAgent
from agents.document_parser import DocumentParserAgent
from agents.normalizer import NormalizerAgent, RFX_LINE_ITEMS
from agents.analyst import AnalystAgent

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
VENDOR_DIR = os.path.join(DATA_DIR, "vendor_responses")
OUTPUT_DIR = os.path.join(DATA_DIR, "rfx_output")


class RFxCrew:
    """
    Orchestrates the full RFx pipeline crew.
    Each agent has a single responsibility; this class wires them together.
    """

    def __init__(self, anthropic_api_key: str = None, openai_api_key: str = None):
        # Accept both names for compatibility; anthropic_api_key takes precedence
        api_key = anthropic_api_key or openai_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set (env var or passed directly)")

        self.client = anthropic.Anthropic(api_key=api_key)

        self.drafter = RFxDrafterAgent(self.client)
        self.dispatcher = VendorDispatcherAgent(stub=True, log_dir=OUTPUT_DIR)
        self.parser = DocumentParserAgent(self.client)
        self.normalizer = NormalizerAgent(self.client)
        self.analyst = AnalystAgent(self.client)

        self.rfx = None
        self.raw_extractions = []
        self.normalized_vendors = []
        self.comparison = None

    def load_rfx_from_file(self, path: str = None) -> dict:
        path = path or os.path.join(OUTPUT_DIR, "RFX-2024-001.json")
        with open(path, "r", encoding="utf-8") as f:
            self.rfx = json.load(f)
        print(f"[Drafter] Loaded RFx: {self.rfx['rfx_id']} — "
              f"{len(self.rfx['line_items'])} line items, {len(self.rfx['vendors'])} vendors")
        return self.rfx

    def dispatch_rfx(self) -> list:
        if not self.rfx:
            raise RuntimeError("No RFx loaded.")
        print(f"[Dispatcher] Sending RFx to {len(self.rfx['vendors'])} vendors (stubbed SMTP)...")
        results = self.dispatcher.dispatch(self.rfx)
        for r in results:
            print(f"  → {r['vendor_name']}: {r['status']}")
        return results

    def parse_vendor_responses(self) -> list:
        print(f"[Parser] Parsing vendor responses from: {VENDOR_DIR}")
        self.raw_extractions = self.parser.parse_all(VENDOR_DIR)
        print(f"[Parser] Parsed {len(self.raw_extractions)} vendor responses")
        for r in self.raw_extractions:
            n = len(r.get("line_items_raw", []))
            print(f"  {r.get('vendor_id','?')} {r.get('vendor_name','?')}: "
                  f"{n} lines via {r.get('parse_method','?')} "
                  f"(confidence: {r.get('confidence','?')})")

        raw_path = os.path.join(OUTPUT_DIR, "raw_extractions.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(self.raw_extractions, f, indent=2, ensure_ascii=False)
        return self.raw_extractions

    def normalize(self) -> dict:
        print(f"[Normalizer] Normalizing {len(self.raw_extractions)} vendor extractions...")
        self.normalized_vendors = [
            self.normalizer.normalize_vendor(raw) for raw in self.raw_extractions
        ]
        for v in self.normalized_vendors:
            flags = v.get("vendor_flags", [])
            print(f"  {v['vendor_id']} {v['vendor_name']}: "
                  f"{len(v['lines'])} lines normalized"
                  + (f", {len(flags)} flags" if flags else ""))

        self.comparison = self.normalizer.build_comparison_matrix(self.normalized_vendors)

        comp_path = os.path.join(OUTPUT_DIR, "comparison_matrix.json")
        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(self.comparison, f, indent=2, ensure_ascii=False)
        print(f"[Normalizer] Qualified vendors: {self.comparison['qualified_vendors']}")
        return self.comparison

    def load_analyst(self):
        if not self.comparison:
            raise RuntimeError("No comparison built.")
        self.analyst.load_comparison(self.comparison)
        print("[Analyst] Ready for buyer questions.")

    def run_full_pipeline(self, use_existing_rfx: bool = True) -> dict:
        print("\n" + "=" * 60)
        print("RFx CREW PIPELINE — Starting (Anthropic Claude)")
        print("=" * 60)

        self.load_rfx_from_file()
        self.dispatch_rfx()
        self.parse_vendor_responses()
        self.normalize()
        self.load_analyst()

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE — Buyer can now ask questions")
        print("=" * 60 + "\n")
        return self.comparison


if __name__ == "__main__":
    crew = RFxCrew()
    crew.run_full_pipeline()
    print("\nEnter questions (type 'award' for recommendation, 'quit' to exit):\n")
    while True:
        try:
            q = input("Buyer: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in ("quit", "exit"):
            break
        answer = crew.analyst.get_award_recommendation() if q.lower() == "award" else crew.analyst.ask(q)
        print(f"\nAnalyst:\n{answer}\n")
