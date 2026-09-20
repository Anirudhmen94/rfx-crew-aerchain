"""
agents/rfx_drafter.py
Agent 1: RFx Drafter — uses Anthropic Claude
"""

import json
import os
import re
from typing import Optional
import anthropic


class RFxDrafterAgent:
    """
    Conversational co-pilot that helps a buyer draft an RFx.
    Assignment: 'buyer talks an RFx into existence with an AI co-pilot'
    """

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.history = []
        self.rfx = {}

    def _system_prompt(self):
        return """You are an AI procurement co-pilot helping a category buyer draft an RFx (Request for Quotation).
Your job is to help the buyer define:
1. Category and 30 line items (description, unit of measure, estimated quantity)
2. A quality questionnaire (5-7 questions for vendor qualification)
3. Commercial terms (payment terms, delivery location, validity period)
4. A list of 5 vendors to send the RFx to

Ask clarifying questions. Once you have enough information, output a JSON block starting with ```json
and ending with ``` that contains the complete RFx. The JSON must have these fields:
- rfx_id (generate as RFX-YYYY-NNN)
- title
- buyer
- issued_date (today)
- response_deadline (9 days from today, per the scenario)
- currency (default INR)
- delivery_location
- terms
- line_items: [{id, description, uom, qty}] — exactly 30 items
- questionnaire: [string] — 5-7 questions
- vendors: [{id, name, contact}] — exactly 5 vendors

Be conversational but efficient. If the buyer says 'corrugated packaging' use the standard 30-item set."""

    def chat(self, user_message: str) -> str:
        """Send a message to the drafter agent and get a response."""
        self.history.append({"role": "user", "content": user_message})
        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            system=self._system_prompt(),
            messages=self.history,
        )
        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def extract_rfx_from_reply(self, reply: str) -> Optional[dict]:
        """Parse the JSON block from the agent's reply if present."""
        match = re.search(r"```json\s*(.*?)```", reply, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    def quick_draft(self, category: str = "corrugated packaging") -> tuple:
        """
        Shortcut: produce a complete RFx for demo purposes using the AI.
        Assignment: 'don't hardcode the answers to your demo questions'
        """
        prompt = f"""Draft a complete RFx for {category}. 
30 line items, 5 realistic vendors in India, 7 questionnaire items, 
payment terms 45 days, delivery Pune warehouse.
Output the JSON block immediately."""
        reply = self.chat(prompt)
        rfx = self.extract_rfx_from_reply(reply)
        if rfx:
            self.rfx = rfx
        return rfx, reply
