"""
FILE 3 - API & APP CONFIG
Everything that can change (keys, model names, folders, limits) lives here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads the .env file

# ---- Folders --------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"          # PDFs the agent can read (RAG knowledge)
OUTBOX_DIR = BASE_DIR / "outbox"      # simulated emails are saved here
DB_PATH = BASE_DIR / "tickets.db"     # SQLite file for unresolved issues
BROCHURE_PATH = DATA_DIR / "GNDEC_Bidar_TP_Cell_Brochure.pdf"
# Dummy / reference copies that must never enter the RAG corpus or be offered for download.
# Matched on exact file name; deleting the file from data/ makes this entry unnecessary.
RAG_EXCLUDE = {"City_Engineering_College_Campus_Buddy_Brochure.pdf"}

# ---- LLM (Groq free tier) -------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MAIN_MODEL = os.getenv("MAIN_MODEL", "openai/gpt-oss-120b")  # writes answers
FAST_MODEL = os.getenv("FAST_MODEL", "openai/gpt-oss-20b")   # cheap judgement calls

# ---- Agent behaviour ------------------------------------------------------
TOP_K = 4            # how many chunks to retrieve
MAX_RETRIES = 1      # rewrite the search query at most once
CHUNK_SIZE = 2500    # characters per chunk
AUTHORITY_EMAIL = os.getenv("AUTHORITY_EMAIL", "placement@gndecb.ac.in")
CATEGORIES = ["greeting", "scholarships", "admissions", "fees", "courses",
              "placements", "faculty", "hostel", "library", "facilities",
              "management", "brochure", "other"]


def get_llm(fast: bool = False):
    """Return a Groq chat model. fast=True -> small model for guardrail/grading."""
    from langchain_groq import ChatGroq
    return ChatGroq(model=FAST_MODEL if fast else MAIN_MODEL,
                    temperature=0, api_key=GROQ_API_KEY)
