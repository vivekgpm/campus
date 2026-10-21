"""
FILE 1 - AI ASSISTANT UI  (Streamlit)
Run:  streamlit run app.py
The UI only collects input and shows output. All thinking happens in agents.py.
"""
import importlib
import streamlit as st
import prompts
import config
import agents

# Ensure hot reloading picks up changes to prompts, config, and agents immediately
importlib.reload(prompts)
importlib.reload(config)
importlib.reload(agents)

st.set_page_config(page_title="Campus Buddy - GNDEC Bidar T&P Cell", page_icon="🎓", layout="wide")
st.title("🎓 GNDEC Bidar - T&P Cell Assistant")
st.caption("Guru Nanak Dev Engineering College, Bidar — Training & Placement Cell and Campus Query Assistant")

if not config.GROQ_API_KEY:
    st.error("GROQ_API_KEY missing. Copy .env.example to .env and add your free key.")
    st.stop()

if config.BROCHURE_PATH.exists():
    brochure_bytes = config.BROCHURE_PATH.read_bytes()
else:
    brochure_bytes = b""

# ---------------- Session State ---------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_contact" not in st.session_state:
    st.session_state.student_contact = ""

# ---------------- Sidebar: controls + "look inside the harness" -------------
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Retrieval mode", ["Vector", "Keyword"],
                    help="Vector = search by meaning. Keyword = BM25 word match.")
    name = st.text_input("Your name (optional)", value=st.session_state.student_name, key="sidebar_name")
    contact = st.text_input("Email / phone (optional)", value=st.session_state.student_contact, key="sidebar_contact")
    
    # Sync if user typed in sidebar
    if name != st.session_state.student_name:
        st.session_state.student_name = name
    if contact != st.session_state.student_contact:
        st.session_state.student_contact = contact

    if brochure_bytes:
        st.download_button("📄 Download T&P Brochure", brochure_bytes,
                           file_name="GNDEC_Bidar_TP_Cell_Brochure.pdf",
                           mime="application/pdf", key="brochure_sidebar")
    show_trace = st.checkbox("Show agent trace", value=True)

    with st.expander("Agents in this app"):
        for agent, (role, uses) in agents.AGENTS.items():
            st.markdown(f"**{agent}** - {role}  \n`{uses}`")
    with st.expander("Graph (paste in mermaid.live)"):
        st.code(agents.graph_diagram(), language="text")
    with st.expander("Tickets (SQLite)"):
        rows = agents.list_tickets()
        st.dataframe(rows, column_order=None) if rows else st.write("No tickets yet.")

# ---------------- Chat -------------------------------------------------------
def render(msg, idx):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + " • ".join(msg["sources"]))
        if msg.get("show_brochure") and brochure_bytes:
            st.download_button("📄 Download T&P Brochure", brochure_bytes,
                               file_name="GNDEC_Bidar_TP_Cell_Brochure.pdf",
                               mime="application/pdf", key=f"brochure_{idx}")
        if show_trace and msg.get("trace"):
            with st.expander("Agent trace"):
                st.write(" → ".join(msg["trace"]))
                st.json(msg["debug"])


for i, m in enumerate(st.session_state.messages):
    render(m, i)

if question := st.chat_input("Ask about placements, packages, recruiters, TPO contact, internships, programs…"):
    # Extract name and contact from chat if shared by the student
    ext_name, ext_contact = agents.extract_contact_info(
        question, st.session_state.student_name, st.session_state.student_contact
    )
    st.session_state.student_name = ext_name
    st.session_state.student_contact = ext_contact

    st.session_state.messages.append({"role": "user", "content": question})
    render(st.session_state.messages[-1], len(st.session_state.messages))

    with st.spinner("Agents working…"):
        result = agents.run_agent(
            question, mode, st.session_state.student_name, st.session_state.student_contact
        )
        if result.get("student_name"):
            st.session_state.student_name = result["student_name"]
        if result.get("student_contact"):
            st.session_state.student_contact = result["student_contact"]

    st.session_state.messages.append({
        "role": "assistant", "content": result["answer"],
        "sources": result.get("sources"), "show_brochure": result.get("show_brochure"),
        "trace": result["trace"],
        "debug": {k: result.get(k) for k in
                  ["verdict", "category", "query", "sufficient", "grade_reason", "retries", "ticket_id"]},
    })
    st.rerun()
