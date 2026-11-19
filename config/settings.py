"""Application-wide settings loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "samples"
TEMP_DIR = BASE_DIR / "tmp"
TEMP_DIR.mkdir(exist_ok=True)

# ── Groq / LLM ─────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ── Embedding / FAISS ───────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
FAISS_TOP_K: int = int(os.getenv("FAISS_TOP_K", "5"))

# ── Chunking ────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

# ── Sample contracts ────────────────────────────────────────────────────
SAMPLE_CONTRACTS: dict[str, str] = {
    "IT Offer Letter": str(DATA_DIR / "it_offer_letter.pdf"),
    "Rental Agreement": str(DATA_DIR / "rental_agreement.pdf"),
    "Freelance Contract": str(DATA_DIR / "freelance_contract.pdf"),
}

APP_TITLE = "ClauseGuard AI"
APP_SUBTITLE = "AI-Assisted Contract Analysis & Risk Identification"
DISCLAIMER = (
    "⚠️ **Disclaimer:** ClauseGuard AI provides AI-assisted analysis for "
    "informational purposes only. It does **not** constitute professional legal "
    "advice. Always consult a qualified legal professional before making decisions "
    "based on this analysis."
)
