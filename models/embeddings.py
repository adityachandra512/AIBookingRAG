import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

def get_gemini_embeddings():
    """Initialize Gemini embeddings or raise clear RuntimeError if key invalid/expired."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing. Set GEMINI_API_KEY in your .env or environment.")
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
        return embeddings
    except Exception as e:
        # Surface clear actionable message
        raise RuntimeError(
            "Failed to initialize Gemini embeddings. The API key may be invalid or expired. "
            "Please renew your GEMINI_API_KEY and ensure it's set in your environment. "
            f"Underlying error: {e}"
        ) from e
