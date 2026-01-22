import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from PyPDF2 import PdfReader
from models.embeddings import get_gemini_embeddings
from models.llm import get_gemini_llm

VECTOR_STORE_PATH = "faiss_index"

def ingest_pdfs(uploaded_files):
    texts = []
    for file in uploaded_files:
        reader = PdfReader(file)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        texts.append(text)
    all_text = "\n".join(texts)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = splitter.create_documents([all_text])
    embeddings = get_gemini_embeddings()
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(VECTOR_STORE_PATH)

def _extract_text_from_response(response):
    """Robustly extract plain text from various Gemini/LC response shapes."""
    if response is None:
        return ""
    # Already a string
    if isinstance(response, str):
        return response
    # List of parts/messages
    if isinstance(response, list):
        return "\n".join(_extract_text_from_response(r) for r in response)
    # Dict with common keys
    if isinstance(response, dict):
        if "text" in response:
            return str(response["text"])
        if "content" in response:
            return _extract_text_from_response(response["content"])
        return str(response)
    # Objects with .content / .text
    if hasattr(response, "content"):
        return _extract_text_from_response(response.content)
    if hasattr(response, "text"):
        return str(response.text)
    # Fallback
    return str(response)

def answer_query_with_rag(query):
    # Return synthesized answer using LLM; handle missing index gracefully
    try:
        embeddings = get_gemini_embeddings()
        db = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
    except FileNotFoundError:
        return "No documents indexed yet. Please upload PDFs on the 'Upload PDFs' page."
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Failed to load vector store or embeddings: {e}"

    docs = db.similarity_search(query, k=3)
    context = "\n".join([doc.page_content for doc in docs])

    llm = get_gemini_llm()
    prompt = (
        f"Use the following context from documents to answer the question concisely.\n\nContext:\n{context}\n\n"
        f"Question: {query}\nAnswer briefly and only using the context. If not found, reply: 'Not found in documents.'"
    )
    response = llm.invoke(prompt)
    answer = _extract_text_from_response(response)
    # Ensure final return is a string and safe for .strip()
    return answer.strip() if isinstance(answer, str) else str(answer)

def find_doctor_suggestions(query):
    """
    Given symptom / intent text, retrieve context and ask Gemini to extract structured doctor suggestions:
    returns list of dicts with keys: name, specialization, experience_years, fee, available_times (list)
    """
    embeddings = get_gemini_embeddings()
    db = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
    docs = db.similarity_search(query, k=4)
    context = "\n".join([doc.page_content for doc in docs])

    llm = get_gemini_llm()
    prompt = (
        "You are given medical directory content. Extract up to 3 matching doctors for the user's symptom.\n"
        "For each doctor provide JSON object with fields: name, specialization, experience_years (int), "
        "fee (string), available_times (list of HH:MM strings). "
        "If a value is not available, use empty string or empty list. Respond only with a JSON array.\n\n"
        f"Context:\n{context}\n\n"
        f"User symptom/query: {query}\n\n"
        "Return JSON array."
    )
    response = llm.invoke(prompt)
    raw = _extract_text_from_response(response)

    import json, re
    # Ensure we always pass a string into re.search
    raw_str = str(raw)
    m = re.search(r'(\[.*\])', raw_str, re.S)
    try:
        json_text = m.group(1) if m else raw_str
        doctors = json.loads(json_text)
        # sanitize: ensure times are strings like "09:00"
        for d in doctors:
            d["available_times"] = [str(t).strip().zfill(5) for t in d.get("available_times", [])]
    except Exception:
        doctors = []
    return doctors
