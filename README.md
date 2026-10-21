# Campus Buddy — GNDEC Bidar T&P Cell Assistant

A Streamlit chat assistant for the **Training & Placement Cell** of Guru Nanak Dev Engineering College (GNDEC), Bidar. It answers student questions about placements, packages, recruiters, TPO contacts, internships, programs, fees, admissions, and campus facilities — strictly grounded in official college PDFs — and escalates anything it cannot answer to a human ticket.

Built as a teaching/demo project: every LLM instruction is in one file, every agent is a small function, and the whole orchestration graph is visible from the sidebar.

---

## Features

- **Grounded answers only** — the answerer may use nothing but retrieved PDF chunks; no outside knowledge.
- **Dual retrieval** — switch live between vector search (Chroma, MiniLM embeddings) and keyword search (BM25).
- **Multi-stage agent harness** — 9 named agents over a LangGraph state machine with a self-correcting retry loop.
- **Layered guardrails** — instant regex screening for profanity, prompt injection, greetings, and brochure requests, with a single fast LLM call only as fallback.
- **Graceful human handoff** — when retrieval fails after one rewrite, a ticket is written to SQLite and an escalation email is generated.
- **Full transparency** — optional agent trace, debug JSON, live Mermaid graph, and a ticket table in the UI.
- **Contact capture** — name and email/phone are picked up from chat text or the sidebar and attached to escalation tickets.

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit 1.65.0 |
| Orchestration | LangGraph 1.2.12 (`StateGraph`, conditional edges) |
| LLM | Groq via `langchain-groq` 1.1.3 |
| Main model | `openai/gpt-oss-120b` (answer generation) |
| Fast model | `openai/gpt-oss-20b` (routing, grading, rewriting) |
| Vector store | ChromaDB 1.5.9, in-memory `EphemeralClient` |
| Keyword search | `rank-bm25` 0.2.2 (`BM25Okapi`) |
| PDF parsing | pypdf 6.19.0 |
| Ticket store | SQLite (`tickets.db`) |
| Secrets/config | python-dotenv 1.2.4 |
| Corpus generation | reportlab 5.0.1 |
| Runtime | Python 3.14 (developed on 3.14.2, `.venv`) |

All LLM calls run at `temperature=0`.

---

## Project structure

```
campus/
├── app.py              # Streamlit UI — collects input, renders output, shows trace
├── agents.py           # Agent roles, state, tools, guardrails, graph, run_agent()
├── prompts.py          # Every LLM instruction + fixed replies + email template
├── config.py           # API keys, model names, folders, limits, categories
├── generate_pdfs.py    # Builds the knowledge-base PDFs into data/
├── requirements.txt
├── .env.example        # Copy to .env and fill in
├── data/               # Knowledge base: the PDFs the assistant may read
│   ├── GNDEC_Bidar_TP_Cell_Brochure.pdf
│   ├── GNDEC_Bidar_College_Programs_Facilities.pdf
│   └── City_Engineering_College_Campus_Buddy_Brochure.pdf
├── outbox/             # Escalation emails are written here, not sent
└── tickets.db          # SQLite tickets table
```

---

## Setup

1. **Clone the repository**
   ```bash
   git clone <this-repo>
   cd campus
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - **Windows**
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS / Linux**
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure your key**
   ```bash
   cp .env.example .env      # Windows: copy .env.example .env
   ```

   ```dotenv
   GROQ_API_KEY=gsk_...                      # free key from console.groq.com
   MAIN_MODEL=openai/gpt-oss-120b            # writes answers
   FAST_MODEL=openai/gpt-oss-20b             # cheap judgement calls
   AUTHORITY_EMAIL=placement@gndecb.ac.in    # who unresolved queries go to
   ```

6. **Generate the knowledge-base PDFs (optional — they are already committed)**
   ```bash
   pip install reportlab
   python generate_pdfs.py
   ```

7. **Run the app**
   ```bash
   streamlit run app.py
   ```

8. **Open the URL**
   Then open the URL Streamlit prints (default http://localhost:8501).

---

## How it works

### Agent graph

```
START → guardian_router
   ├─ blocked  → refuser → END
   ├─ greeting → greeting_agent → END
   ├─ brochure → brochure_agent → END
   └─ search   → researcher → grader ─┬─ sufficient → answerer → END
                                       ├─ retry (≤ MAX_RETRIES) → rewriter → researcher  ⟲ loop
                                       └─ escalate → escalation_officer → END
```

### Agents

| Agent | Role | Uses |
|---|---|---|
| `guardian_router` | Safety check + category routing in one step | regex fast paths, then fast LLM |
| `refuser` | Polite refusal for blocked questions | no LLM |
| `greeting_agent` | Warm welcome, asks for name/email | no LLM |
| `brochure_agent` | Points to the brochure download | no LLM |
| `researcher` | Searches the PDFs (vector or keyword) | tool: `retrieve()` |
| `grader` | Judges whether retrieved context is sufficient | fast LLM |
| `rewriter` | Rewrites the query for a second attempt | fast LLM |
| `answerer` | Writes the grounded answer | main LLM |
| `escalation_officer` | Logs a ticket and emails the authority | tools: `create_ticket`, `send_authority_email` |

### Request flow

1. **Guardrails first** — profanity, prompt-injection, greeting, and brochure regexes run in under a millisecond. Most greetings, refusals, and brochure requests never reach an LLM.
2. **Router fallback** — anything left is classified by one fast LLM call returning `{"verdict", "category"}`. Verdict is `ok`, `profanity`, `injection`, or `off_topic`; categories are defined in `config.CATEGORIES` (placements, fees, admissions, scholarships, hostel, library, faculty, facilities, courses, management, brochure, …).
3. **Retrieval** — all PDFs in `data/` are read once and cached, page text is cleaned, and split into ~800-character chunks on line boundaries. Top 4 chunks are returned by either Chroma vector search or BM25, depending on the sidebar toggle.
4. **Grading** — a fast LLM strictly judges whether the chunks actually answer the question. Related-but-not-answering counts as insufficient.
5. **Retry or answer** — if insufficient, the rewriter produces a keyword-rich alternate query and the researcher searches again (once by default). If sufficient, the answerer writes the reply with `source.pdf p.N` citations.
6. **Escalation** — after retries are exhausted, a row is inserted into `tickets` and an escalation email is rendered from `prompts.EMAIL_TEMPLATE` into `outbox/ticket_<id>.txt`. The student gets the ticket number and is asked for contact details.

### Shared state

`AgentState` (a `TypedDict` in `agents.py`) carries `question`, `mode`, `student_name`, `student_contact`, `verdict`, `category`, `query`, `chunks`, `sufficient`, `grade_reason`, `retries`, `answer`, `sources`, `ticket_id`, `show_brochure`, and `trace`. The `trace` list is what the sidebar renders as the agent chain.

### Tools

| Tool | What it does |
|---|---|
| `retrieve(query, mode, k)` | Searches the PDF corpus by meaning (`Vector`) or by word (`Keyword`) |
| `create_ticket(...)` | Inserts an unresolved query into SQLite, returns the ticket id |
| `list_tickets()` | Returns recent tickets for the sidebar table |
| `send_authority_email(ticket_id, state)` | **Simulated** — writes the email to `outbox/` and prints it |
| `extract_contact_info(text, ...)` | Regex extraction of name, email, and Indian phone number |

---

## Configuration

All tunables live in `config.py`:

| Setting | Default | Meaning |
|---|---|---|
| `TOP_K` | `4` | Chunks retrieved per search |
| `MAX_RETRIES` | `1` | Query rewrites before escalating |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `MAIN_MODEL` | `openai/gpt-oss-120b` | Answer-writing model |
| `FAST_MODEL` | `openai/gpt-oss-20b` | Router / grader / rewriter model |
| `AUTHORITY_EMAIL` | `placement@gndecb.ac.in` | Escalation recipient |
| `CATEGORIES` | 13 categories | Router label set |

Model names change often — check `console.groq.com/docs/models` and update `.env`.

---

## Using the sidebar

- **Retrieval mode** — `Vector` (semantic) or `Keyword` (BM25). Useful for comparing answers.
- **Name / Email** — optional; synced into session state and attached to any escalation ticket.
- **Show agent trace** — expands each reply to show which agents ran, in order, plus verdict, category, query, sufficiency, retries, and ticket id.
- **Graph** — Mermaid source for the compiled LangGraph; paste into mermaid.live to draw it.
- **Tickets (SQLite)** — live table of unresolved queries.
- **Download T&P Brochure** — serves `data/GNDEC_Bidar_TP_Cell_Brochure.pdf`.

---

## Extending it

- **Add knowledge** — drop another PDF into `data/`; it is picked up automatically on the next run (the chunk cache is process-level, so restart Streamlit after adding files).
- **Add a category** — add it to `config.CATEGORIES` and mention it in `prompts.GUARD_ROUTER_PROMPT`.
- **Change the tone or rules** — edit `ANSWER_PROMPT` / `GREETING_REPLY` in `prompts.py`. `app.py` and `agents.py` reload that module, so edits appear on the next interaction.
- **Real email** — replace the body of `send_authority_email` in `agents.py` with an SMTP or API call; the template in `prompts.py` stays the same.
- **Different college** — change `COLLEGE` in `prompts.py`, the category list in `config.py`, and regenerate the PDFs with `generate_pdfs.py`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `GROQ_API_KEY missing` banner | `.env` not created, or the key is empty |
| Answers say nothing was found | The PDF corpus may be empty — confirm files exist in `data/`; restart the app so the cache rebuilds |
| ChromaDB version errors on Python 3.14 | Pin an older Python (3.11/3.12) in a fresh venv |
| Model name rejected by Groq | Model IDs change; pick a current one from the Groq docs |
| No ticket row created | The grader judged the context sufficient — toggle **Show agent trace** to see why |

---

## Security notes

- `.env` holds the API key and must never be committed. `.env.example` should contain placeholders only — if a real key was ever pasted there, rotate it at console.groq.com.
- Retrieved PDF text is passed to the LLM as **data, not instructions** (enforced in `ANSWER_PROMPT`), so document contents cannot override the assistant's rules.
- Guardrails are defence-in-depth, not a guarantee: regex screening plus a routing LLM is a reasonable demo guard, and `LLM_GUARDRAIL`/`llm-guard` style validation is the next step for production.
- The escalation email is simulated on purpose; do not point `AUTHORITY_EMAIL` at real infrastructure until a real sender is configured.

---

## License

Provided for educational and demonstration purposes. The college data is sample content generated by `generate_pdfs.py`; verify facts against official GNDEC Bidar sources before publishing.