"""
FILE 5 - AGENTS & HARNESS  (the heart of the session)

HARNESS = everything around the LLM that makes it an agent:
    state (memory)  +  tools  +  guardrails  +  control flow (the graph)  +  trace

This app is a WORKFLOW-style harness: WE draw the graph, the LLM makes small
judgements inside each node. Read the file top to bottom:
    1. AGENT ROLES   2. STATE   3. TOOLS (RAG + tickets + email)
    4. GUARDRAILS    5. AGENT NODES   6. THE GRAPH   7. run_agent()
"""
import json
import re
import sqlite3
import datetime
import hashlib
from functools import lru_cache
from typing import TypedDict

import chromadb
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from langgraph.graph import StateGraph, START, END

import config
import prompts
import importlib

importlib.reload(prompts)

# ===========================================================================
# 1. AGENT ROLES  (shown in the UI sidebar)
# ===========================================================================
AGENTS = {
    "guardian_router":    ("Safety check + category router in 1 fast step", "fast-path rules + fast LLM"),
    "greeting_agent":     ("Greets student warmly & asks for name/email",   "no LLM"),
    "researcher":         ("Searches the PDFs (vector or keyword)",         "TOOL: retrieve()"),
    "grader":             ("Judges: is the context enough?",                "fast LLM"),
    "rewriter":           ("Rewrites the query for a 2nd attempt",          "fast LLM"),
    "answerer":           ("Writes a grounded answer from context",         "main LLM"),
    "escalation_officer": ("Logs ticket + emails authority",                "TOOLS: create_ticket, send_email"),
    "brochure_agent":     ("Points student to the brochure download",       "no LLM"),
    "refuser":            ("Politely refuses blocked questions",            "no LLM"),
}

# ===========================================================================
# 2. STATE - the shared notebook every agent reads from and writes to
# ===========================================================================
class AgentState(TypedDict, total=False):
    question: str
    mode: str              # "Vector" or "Keyword"
    student_name: str
    student_contact: str
    verdict: str           # ok | profanity | injection | off_topic
    category: str
    query: str             # the search query actually used
    chunks: list           # retrieved pieces of the PDFs
    sufficient: bool       # grader's decision
    grade_reason: str
    retries: int
    answer: str
    sources: list
    ticket_id: int
    show_brochure: bool
    trace: list            # names of agents that ran, in order

# ===========================================================================
# 3. TOOLS
# ===========================================================================
# ---- 3a. RAG: load PDFs -> chunks -> two ways to search --------------------
def _split(text: str, size: int = None) -> list:
    """Cut a page into ~size-char chunks on line boundaries."""
    if size is None:
        size = config.CHUNK_SIZE
    chunks, current = [], ""
    for line in text.splitlines():
        if current and len(current) + len(line) > size:
            chunks.append(current.strip())
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


@lru_cache(maxsize=1)
def _load_chunks() -> list:
    """Read every real PDF in data/ (config.RAG_EXCLUDE skipped). Runs once, then cached."""
    chunks = []
    pdfs = [p for p in sorted(config.DATA_DIR.glob("*.pdf")) if p.name not in config.RAG_EXCLUDE]
    for pdf in pdfs:
        for page_no, page in enumerate(PdfReader(pdf).pages, start=1):
            text = (page.extract_text() or "").replace("■", "₹")  # PDF rupee glyph fix
            for piece in _split(text):
                chunks.append({"text": piece, "source": pdf.name, "page": page_no})
    return chunks


def _tokens(text: str) -> list:
    return re.findall(r"\w+", text.lower())


@lru_cache(maxsize=1)
def _bm25() -> BM25Okapi:
    return BM25Okapi([_tokens(c["text"]) for c in _load_chunks()])


def _corpus_tag(chunks: list) -> str:
    """Fingerprint of the loaded corpus, so a changed data/ folder means a fresh collection."""
    digest = hashlib.sha1("\n".join(c["text"] for c in chunks).encode("utf-8", "ignore")).hexdigest()[:8]
    return f"{len(chunks)}-{digest}"


@lru_cache(maxsize=1)
def _vector_db():
    """In-memory Chroma. Uses its built-in free MiniLM embeddings.

    Chroma's EphemeralClient store is shared for the whole process, and add() silently
    skips duplicate ids, so the collection name carries the corpus fingerprint and the
    count is re-checked. Otherwise a stale collection would hand back ids that no longer
    index into _load_chunks() and retrieve() would raise IndexError.
    """
    chunks = _load_chunks()
    collection = chromadb.EphemeralClient().get_or_create_collection(f"college_{_corpus_tag(chunks)}")
    if collection.count() != len(chunks):
        collection.add(ids=[str(i) for i in range(len(chunks))],
                       documents=[c["text"] for c in chunks])
    return collection


def retrieve(query: str, mode: str, k: int = config.TOP_K) -> list:
    """TOOL: search the college documents. mode = 'Vector' (meaning) or 'Keyword' (BM25)."""
    chunks = _load_chunks()
    if not chunks:
        return []
    if mode == "Keyword":
        scores = _bm25().get_scores(_tokens(query))
        best = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [chunks[i] for i in best if scores[i] > 0]
    collection = _vector_db()
    result = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    return [chunks[int(i)] for i in (result.get("ids") or [[]])[0]
            if str(i).lstrip("-").isdigit() and 0 <= int(i) < len(chunks)]


def _format_context(chunks: list) -> str:
    return "\n\n".join(f"[{c['source']} p.{c['page']}]\n{c['text']}" for c in chunks) or "(nothing found)"


# ---- 3b. Tickets (SQLite) --------------------------------------------------
def _db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, student_name TEXT,
        student_contact TEXT, category TEXT, question TEXT, status TEXT DEFAULT 'OPEN')""")
    return conn


def create_ticket(question: str, category: str, student_name: str, student_contact: str) -> int:
    """TOOL: log an unresolved issue. Returns the ticket id."""
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (created_at, student_name, student_contact, category, question) "
            "VALUES (?,?,?,?,?)",
            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), student_name or "Anonymous",
             student_contact or "not given", category, question))
        return cur.lastrowid


def list_tickets() -> list:
    with _db() as conn:
        return conn.execute("SELECT id, created_at, category, question, status "
                            "FROM tickets ORDER BY id DESC").fetchall()


def update_ticket_contact(ticket_id: int, student_name: str = "", student_contact: str = "") -> bool:
    """Attach later-provided contact details to an open ticket and refresh its draft email."""
    with _db() as conn:
        row = conn.execute(
            "SELECT category, question, student_name, student_contact "
            "FROM tickets WHERE id=? AND status='OPEN'", (ticket_id,)
        ).fetchone()
        if not row:
            return False

        category, question, old_name, old_contact = row
        name = student_name or ("" if old_name == "Anonymous" else old_name)
        contact = student_contact or ("" if old_contact == "not given" else old_contact)
        conn.execute(
            "UPDATE tickets SET student_name=?, student_contact=? WHERE id=?",
            (name or "Anonymous", contact or "not given", ticket_id)
        )

    # This project saves a draft locally rather than sending real email.
    send_authority_email(ticket_id, {
        "category": category,
        "question": question,
        "student_name": name,
        "student_contact": contact,
        "query": "Contact details added after ticket creation",
        "grade_reason": "Student supplied contact details after the original request.",
    })
    return True


def send_authority_email(ticket_id: int, state: dict) -> str:
    """TOOL: SIMULATED email - saved as a file and printed to the console."""
    config.OUTBOX_DIR.mkdir(exist_ok=True)
    body = prompts.EMAIL_TEMPLATE.format(
        to=config.AUTHORITY_EMAIL, ticket_id=ticket_id,
        time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        category=state.get("category", "other"),
        student_name=state.get("student_name") or "Anonymous",
        student_contact=state.get("student_contact") or "not given",
        question=state["question"], query=state.get("query", ""),
        reason=state.get("grade_reason", ""))
    path = config.OUTBOX_DIR / f"ticket_{ticket_id}.txt"
    path.write_text(body, encoding="utf-8")
    try:
        print("\n===== SIMULATED EMAIL =====\n" + body)
    except Exception:
        print(f"\n===== SIMULATED EMAIL (saved to {path}) =====")
    return str(path)

# ===========================================================================
# 4. GUARDRAILS & FAST-PATH RULES (run in < 1ms BEFORE using LLM)
# ===========================================================================
PROFANITY = re.compile(r"\b(fuck\w*|shit\w*|bastard|bitch|asshole|idiot|stupid|moron)\b", re.I)
INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|your) (instructions|rules|prompt)",
    r"(reveal|show|print|repeat).{0,30}(system prompt|your instructions)",
    r"you are now", r"developer mode", r"jailbreak", r"disregard .{0,20}(rules|instructions)",
]
GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening|day)|namaste|who\s+are\s+you|what\s+can\s+you\s+do|help)\b[!?.\s]*$",
    re.I
)
BROCHURE_PATTERN = re.compile(
    r"\b(download|get|view|see|show|send)?\s*(the\s*)?(college\s*)?(brochure|prospectus)\b",
    re.I
)


def extract_contact_info(text: str, existing_name: str = "", existing_contact: str = "") -> tuple:
    """Extract email, phone, and clean name from user message if present."""
    name = (existing_name or "").strip()
    contact = (existing_contact or "").strip()
    
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    if email_match and not contact:
        contact = email_match.group(0)
        
    if not contact:
        phone_match = re.search(r"(?:\+?91[\-\s]?)?[6789]\d{9}", text)
        if phone_match:
            contact = phone_match.group(0)
            
    if not name:
        name_match = re.search(r"(?:my name is|i am|i\'m|this is|myself|name\s*[:\-])\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.I)
        if name_match:
            candidate = name_match.group(1).strip()
            candidate = re.sub(r"\b(and|my|email|phone|contact|here)\b.*$", "", candidate, flags=re.I).strip()
            if candidate and len(candidate.split()) <= 3:
                name = candidate
        elif email_match:
            prefix = text[:email_match.start()].strip(" ,:-")
            if prefix and len(prefix.split()) <= 3 and re.match(r"^[A-Za-z\s]+$", prefix):
                clean_prefix = re.sub(r"\b(hi|hello|hey|dear|and|my|name|is)\b", "", prefix, flags=re.I).strip()
                if clean_prefix and len(clean_prefix.split()) <= 2:
                    name = clean_prefix
    return name, contact


def is_contact_only_message(text: str, student_name: str = "", student_contact: str = "") -> bool:
    """Recognize a contact-details follow-up without intercepting a real question."""
    email = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    phone = re.search(r"(?:\+?91[\-\s]?)?[6789]\d{9}", text)
    if not (email or phone):
        return False
    if "?" in text:
        return False

    without_contact = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", " ", text)
    without_contact = re.sub(r"(?:\+?91[\-\s]?)?[6789]\d{9}", " ", without_contact)
    tokens = re.findall(r"[a-z]+", without_contact.lower())
    allowed = {
        "my", "name", "is", "i", "am", "im", "this", "myself", "and", "email", "e", "mail",
        "id", "address", "phone", "number", "contact", "details", "here", "are", "the", "a",
        "provided", "sharing", "share", "please", "kindly", "thanks", "thank", "you", "for",
        "with", "also", "this", "to", "reach", "me", "at", ":",
    }
    name_tokens = set(re.findall(r"[a-z]+", (student_name or "").lower()))
    remaining = [token for token in tokens if token not in allowed and token not in name_tokens]
    return not remaining

# ===========================================================================
# 5. AGENT NODES - each is a small function: state in -> changes out
# ===========================================================================
def _ask(prompt: str, fast: bool = True) -> str:
    return str(config.get_llm(fast).invoke(prompt).content).strip()


def _ask_json(prompt: str, default: dict) -> dict:
    """Ask the fast LLM for JSON; fall back to a safe default if it misbehaves."""
    try:
        return json.loads(re.search(r"\{.*\}", _ask(prompt), re.S).group(0))
    except Exception:
        return default


def _trace(state: dict, name: str) -> dict:
    return {"trace": state.get("trace", []) + [name]}


def guardian_router(state):
    """Unified single-stage safety check + topic classification."""
    q = state["question"].strip()
    
    # Fast path 1: Profanity filter (instant)
    if PROFANITY.search(q):
        return {"verdict": "profanity", "category": "other", **_trace(state, "guardian_router")}
    
    # Fast path 2: Prompt injection filter (instant)
    if any(re.search(p, q, re.I) for p in INJECTION_PATTERNS):
        return {"verdict": "injection", "category": "other", **_trace(state, "guardian_router")}
    
    # Fast path 3: Greetings / introductions (instant, 0ms LLM latency)
    if GREETING_PATTERN.match(q):
        return {"verdict": "ok", "category": "greeting", **_trace(state, "guardian_router")}
    
    # Fast path 4: Brochure requests (instant)
    if BROCHURE_PATTERN.search(q) and len(q.split()) <= 6:
        return {"verdict": "ok", "category": "brochure", "show_brochure": True, **_trace(state, "guardian_router")}
    
    # Fast LLM Call: Single unified safety and categorization
    r = _ask_json(
        prompts.GUARD_ROUTER_PROMPT.format(college=prompts.COLLEGE, categories=", ".join(config.CATEGORIES), question=q),
        {"verdict": "ok", "category": "other"}
    )
    verdict = r.get("verdict", "ok")
    category = r.get("category", "other").lower()
    if category not in config.CATEGORIES:
        category = next((c for c in config.CATEGORIES if c in category), "other")
    
    return {"verdict": verdict, "category": category, "show_brochure": category == "brochure",
            **_trace(state, "guardian_router")}


def refuser(state):
    verdict = state.get("verdict", "off_topic")
    msg = prompts.REFUSALS.get(verdict, prompts.REFUSALS["off_topic"]).format(college=prompts.COLLEGE)
    return {"answer": msg, **_trace(state, "refuser")}


def greeting_agent(state):
    name = (state.get("student_name") or "").strip()
    contact = (state.get("student_contact") or "").strip()
    
    greeting_prefix = f"Hello **{name}**!" if name else "Hello!"
    contact_ack = (
        f"\n\nThank you for providing your contact details (**{contact}**). We will use this for any official ticket updates."
        if contact else (
            "\n\nTo help us communicate better and assist you with any follow-up queries or official tickets, "
            "could you please share your **Name** and **Email address** (you can also fill them in the sidebar)?"
        )
    )
    
    msg = (
        f"{greeting_prefix} Welcome to **{prompts.COLLEGE}**! 🎓\n\n"
        f"I'm **Campus Buddy**, your virtual assistant for the **Training & Placement Cell** and college queries. I'm here to help you with:\n"
        f"• 💼 **Placements, Packages & Top Recruiters** (90%+ placement rate, ₹12 LPA highest package)\n"
        f"• 📞 **TPO & Placement Committee Contacts** (Prof. Shravan Kumar, `placement@gndecb.ac.in`)\n"
        f"• 🛠️ **Internship & Technical Skill Development Programs**\n"
        f"• 📚 **Academic Programs (B.E, M.Tech, MBA, MCA) & Admissions**\n"
        f"• 🏛️ **Campus Facilities, Central Library & Hostels**\n"
        f"• 📄 **T&P Cell Information Brochure Download**"
        f"{contact_ack}\n\n"
        f"How can I help you today?"
    )
    return {"answer": msg, **_trace(state, "greeting_agent")}


def brochure_agent(state):
    return {"answer": prompts.BROCHURE_REPLY, **_trace(state, "brochure_agent")}


def researcher(state):
    query = state.get("query") or state["question"]
    return {"query": query, "chunks": retrieve(query, state["mode"]), **_trace(state, "researcher")}


def grader(state):
    r = _ask_json(prompts.GRADE_PROMPT.format(
        question=state["question"], context=_format_context(state["chunks"])),
        {"sufficient": False, "reason": "grader output unreadable"})
    return {"sufficient": bool(r.get("sufficient")), "grade_reason": r.get("reason", ""),
            **_trace(state, "grader")}


def rewriter(state):
    new_query = _ask(prompts.REWRITE_PROMPT.format(
        question=state["question"], old_query=state["query"]))
    return {"query": new_query, "retries": state.get("retries", 0) + 1, **_trace(state, "rewriter")}


def answerer(state):
    answer = _ask(prompts.ANSWER_PROMPT.format(
        college=prompts.COLLEGE, context=_format_context(state["chunks"]),
        question=state["question"]), fast=False)
    sources = sorted({f"{c['source']} p.{c['page']}" for c in state["chunks"]})
    return {"answer": answer, "sources": sources, **_trace(state, "answerer")}


def escalation_officer(state):
    ticket_id = create_ticket(state["question"], state.get("category", "other"),
                              state.get("student_name", ""), state.get("student_contact", ""))
    send_authority_email(ticket_id, state)
    student_contact = (state.get("student_contact") or "").strip()
    if student_contact:
        contact_note = (
            f"Your contact details (**{student_contact}**) are attached to the ticket and its saved email draft. "
            "A staff member must review and send that draft before the college can contact you."
        )
    else:
        contact_note = (
            "To ensure our administration can reach you with the answer, "
            "please provide your **Name** and **Email address / Contact** in the sidebar (or in your reply)."
        )
    answer = prompts.ESCALATION_REPLY.format(
        ticket_id=ticket_id,
        college=prompts.COLLEGE,
        contact_note=contact_note
    )
    return {"ticket_id": ticket_id,
            "answer": answer,
            **_trace(state, "escalation_officer")}

# ===========================================================================
# 6. THE GRAPH - who runs after whom (the "control flow" of the harness)
# ===========================================================================
def after_guardian_router(state):
    if state.get("verdict") != "ok":
        return "blocked"
    if state.get("category") == "greeting":
        return "greeting"
    if state.get("category") == "brochure":
        return "brochure"
    return "search"


def after_grader(state):
    if state["sufficient"]:
        return "answer"
    if state.get("retries", 0) < config.MAX_RETRIES:
        return "retry"          # <-- the LOOP: rewrite and search again
    return "escalate"           # <-- give up gracefully: human handoff


def build_graph():
    g = StateGraph(AgentState)
    for name, fn in [("guardian_router", guardian_router), ("refuser", refuser),
                     ("greeting_agent", greeting_agent), ("brochure_agent", brochure_agent),
                     ("researcher", researcher), ("grader", grader), ("rewriter", rewriter),
                     ("answerer", answerer), ("escalation_officer", escalation_officer)]:
        g.add_node(name, fn)

    g.add_edge(START, "guardian_router")
    g.add_conditional_edges("guardian_router", after_guardian_router,
                            {"blocked": "refuser", "greeting": "greeting_agent",
                             "brochure": "brochure_agent", "search": "researcher"})
    g.add_edge("researcher", "grader")
    g.add_conditional_edges("grader", after_grader,
                            {"answer": "answerer", "retry": "rewriter", "escalate": "escalation_officer"})
    g.add_edge("rewriter", "researcher")
    for end_node in ["refuser", "greeting_agent", "brochure_agent", "answerer", "escalation_officer"]:
        g.add_edge(end_node, END)
    return g.compile()


GRAPH = build_graph()


def graph_diagram() -> str:
    """Mermaid text of the graph - paste into mermaid.live to draw it."""
    return GRAPH.get_graph().draw_mermaid()

# ===========================================================================
# 7. ENTRY POINT used by the UI
# ===========================================================================
def run_agent(question: str, mode: str = "Vector", student_name: str = "", student_contact: str = "") -> dict:
    extracted_name, extracted_contact = extract_contact_info(question, student_name, student_contact)
    result = GRAPH.invoke({
        "question": question,
        "mode": mode,
        "student_name": extracted_name,
        "student_contact": extracted_contact,
        "retries": 0,
        "trace": []
    })
    result["student_name"] = extracted_name
    result["student_contact"] = extracted_contact
    return result
