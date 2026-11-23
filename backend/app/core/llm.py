import os
from pathlib import Path

from langchain_ollama import ChatOllama
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
    num_predict=int(os.getenv("OLLAMA_NUM_PREDICT", "4000")),
)

def get_ai_response(message: str) -> str:
    response = llm.invoke(message)
    return response.content
