# What I Built — and What I Deliberately Left Out

**RFx Crew | Corrugated Packaging | 5 Vendors, 30 Line Items**

---

## What I decided

**Category:** Corrugated packaging. The assignment named it first and it's the cleanest demo for unit-mismatch ugliness (a box manufacturer easily quotes in "per 100 pcs" vs "per piece").

**Agent framework:** A simple sequential crew of 5 agents, each with one job. No orchestration framework dependency (no CrewAI, LangChain) — each agent is a plain Python class that uses the OpenAI API directly. I made this choice because the assignment values judgment over framework knowledge, and a dependency-light system is easier to demo live without setup surprises.

**The five agents and why:**
1. **RFx Drafter** — the "co-pilot" the assignment describes. Conversational, produces structured JSON. For the demo I also support loading a pre-seeded RFx so the demo doesn't block on AI latency at startup.
2. **Vendor Dispatcher** — real dispatch logic, stubbed SMTP. Assignment explicitly permits this. Every "email" is written to disk so you can see what went out.
3. **Document Parser** — this is where the assignment's rule "don't fake the extraction" lives. JSON and CSV are parsed deterministically. Unstructured formats (email text, Word-doc text, PDF-style text) go through the LLM with a tight extraction prompt. The LLM actually reads the text and extracts; I don't pre-seed its answers.
4. **Normalizer** — handles the three ugly edges the assignment calls out: USD→INR conversion, per-100-pcs→per-piece UOM normalization, and missing lines (vendor who quoted 27/30). All flagged explicitly, never silently dropped.
5. **Analyst** — the buyer's chat interface. Real GPT-4o reasoning over the normalized matrix. The system prompt carries the full comparison data. I don't hardcode answers; I also don't let the LLM hallucinate — the system prompt explicitly forbids inventing prices not in the data.

**Storage:** JSON files on disk. SQLite was considered but overkill for a 5-vendor demo. In production: Postgres with pgvector for the chat history.

**UI:** Streamlit. Four tabs: comparison table, analyst chat, award recommendation, extraction debug. The debug tab directly addresses the assignment's question — "what does your system show the buyer when it isn't sure?" Answer: it shows the flag, the source, and the confidence level, inline with the data.

**The VP's question** ("cheapest per line, but only among vendors who cleared the quality questionnaire") is a first-class feature, not a demo question. The comparison matrix pre-computes it, and the analyst agent is explicitly primed to answer it.

---

## What I deliberately left out

**Real SMTP / email ingestion.** The assignment explicitly permits stubbing this. Adding an actual inbox-polling loop (IMAP) would take a week and add no AI insight. The interesting problem is the extraction and normalization, not the email transport.

**Image / OCR parsing.** The assignment mentions "a photo of a printed rate card, taken at an angle, on a phone." I acknowledged this as an "ugly edge" vendor format but didn't implement a full vision-model pipeline for it. In production: GPT-4o Vision or Tesseract + preprocessing. The parser architecture already has a hook for it (extend `_parse_text_with_llm` with image input).

**Multi-turn RFx drafting.** The drafter agent supports full conversation, but the demo loads a pre-seeded RFx for startup speed. A live walkthrough of the drafting conversation would take 3-5 minutes of the demo.

**Persistent database and multi-user session state.** Streamlit's session state is single-user and in-memory. Production needs proper persistence.

**Guardrails on the analyst.** I added a system-prompt instruction not to hallucinate prices, but I didn't build a structured output validator or a "cite your source" tracing layer. For a ₹4 crore award decision in production, every analyst answer should cite the exact line in the vendor's source file.

---

## The interesting problem I actually found

The hardest part is not parsing. It's the **"same as last year"** case — a vendor who references a prior contract rather than quoting fresh. The system correctly extracts the reference and flags it ("vendor said 'same as last year'"), but it cannot resolve it without historical data. That's the real trust problem: a buyer who can't see last year's rate can't act on this quote. The right fix is a contract history database the analyst can query. I noted this as the next layer to build.

---

*Built for Aerchain Product Management take-home, September 2024.*
