from langchain_groq import ChatGroq
from backend.core.config import settings

def get_llm():
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        # Placeholder or missing key handling
        # In a real app we'd want this to fail gracefully or not initialize
        pass
        
    return ChatGroq(
        temperature=0,
        model_name=settings.PRIMARY_MODEL,
        groq_api_key=settings.GROQ_API_KEY
    )
