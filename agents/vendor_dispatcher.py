"""
agents/vendor_dispatcher.py
Agent 2: Vendor Dispatcher
Assignment requirement: "It goes out to vendors over a channel you choose."
"Fake the SMTP server if you like." — so we stub the send but log everything.
"""

import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


class VendorDispatcherAgent:
    """
    Packages the RFx into vendor emails and 'sends' them.
    Assignment: stub the SMTP plumbing, but the dispatch logic is real.
    """

    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 1025,
                 stub: bool = True, log_dir: str = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.stub = stub  # True = fake SMTP (assignment: "Fake the SMTP server if you like")
        self.log_dir = log_dir or os.path.join(os.path.dirname(__file__), "..", "data", "rfx_output")
        os.makedirs(self.log_dir, exist_ok=True)
        self.dispatch_log = []

    def _build_email_body(self, rfx: dict, vendor: dict) -> str:
        """Construct the RFx email body for a vendor."""
        lines_text = "\n".join(
            f"  {li['id']:>3}. {li['description']:<48} {li['qty']:>8,} {li['uom']}"
            for li in rfx["line_items"]
        )
        q_text = "\n".join(f"  Q{i+1}. {q}" for i, q in enumerate(rfx["questionnaire"]))

        return f"""Dear {vendor['name']},

We invite you to submit your quotation for the following requirements.

RFx Reference : {rfx['rfx_id']}
Title         : {rfx['title']}
Deadline      : {rfx['response_deadline']}
Delivery      : {rfx['delivery_location']}
Payment Terms : {rfx['terms']}
Currency      : {rfx.get('currency', 'INR')} (preferred; conversions acceptable)

── LINE ITEMS ──────────────────────────────────────────────────────────────
{lines_text}

── QUALITY QUESTIONNAIRE ────────────────────────────────────────────────────
Please answer the following for qualification purposes:
{q_text}

── SUBMISSION INSTRUCTIONS ──────────────────────────────────────────────────
You may respond in any format — Excel, PDF, Word, or plain email text.
No fixed template is required. Please include unit prices and the UOM you are quoting.
Quote currency must be stated. Prices exclusive of GST.

We look forward to your response.

Regards,
Procurement Team
"""

    def dispatch(self, rfx: dict) -> list:
        """
        Send (or stub-send) the RFx to all vendors listed in the RFx.
        Returns a dispatch log of all send attempts.
        Assignment: real dispatch logic, stubbed transport.
        """
        results = []
        for vendor in rfx.get("vendors", []):
            body = self._build_email_body(rfx, vendor)
            record = {
                "vendor_id": vendor["id"],
                "vendor_name": vendor["name"],
                "to": vendor["contact"],
                "rfx_id": rfx["rfx_id"],
                "sent_at": datetime.now().isoformat(),
                "status": None,
                "email_body": body,
            }

            if self.stub:
                # Stub: write to disk instead of sending
                email_path = os.path.join(
                    self.log_dir, f"sent_{vendor['id']}_{rfx['rfx_id']}.txt"
                )
                with open(email_path, "w", encoding="utf-8") as f:
                    f.write(f"TO: {vendor['contact']}\n")
                    f.write(f"SUBJECT: RFx Invitation — {rfx['rfx_id']}: {rfx['title']}\n\n")
                    f.write(body)
                record["status"] = "stubbed"
                record["stub_path"] = email_path
            else:
                # Real SMTP send
                try:
                    msg = MIMEMultipart()
                    msg["From"] = "procurement@company.com"
                    msg["To"] = vendor["contact"]
                    msg["Subject"] = f"RFx Invitation — {rfx['rfx_id']}: {rfx['title']}"
                    msg.attach(MIMEText(body, "plain"))

                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.sendmail("procurement@company.com", vendor["contact"], msg.as_string())
                    record["status"] = "sent"
                except Exception as e:
                    record["status"] = f"error: {e}"

            self.dispatch_log.append(record)
            results.append(record)

        # Save dispatch log
        log_path = os.path.join(self.log_dir, f"dispatch_log_{rfx['rfx_id']}.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return results
