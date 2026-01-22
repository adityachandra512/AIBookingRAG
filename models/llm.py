import os
import sys
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def get_chatgroq_model():
    """Initialize and return the Groq chat model"""
    try:
        # Initialize the Groq chat model with the API key
        groq_model = ChatGroq(
            api_key="",
            model="",
        )
        return groq_model
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Groq model: {str(e)}")


def get_gemini_llm():
    """Initialize and return the Gemini LLM for chat and RAG"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        google_api_key=api_key
    )