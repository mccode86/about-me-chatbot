import os
import chromadb
from fastapi import FastAPI
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pathlib import Path
from anthropic import Anthropic
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
chroma_path = BASE_DIR / "chroma"
app = FastAPI()

anthropic_client = Anthropic()
chroma_client = chromadb.PersistentClient(path=chroma_path)


@app.get("/health")
def health():
    return {"status": "ok"}


openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ.get("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

collection = chroma_client.get_collection(
    name="about_mario",
    embedding_function=openai_ef
)

history = []

class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatMessage):
    history.append({"role": "user", "content": req.message})
    results = collection.query(query_texts=[req.message], n_results=3)
    context = "\n\n".join(results["documents"][0])
    system_prompt = (
        "You are Mario's support assistant. "
        "Answer using ONLY the context below. "
        "Be concise; elaborate only when the question requires it. "
        "If it's not in the context, say you don't know.\n\n"
        f"Context:\n{context}"
    )
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=system_prompt,
        messages=history
    )
    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    return {"reply": reply}

