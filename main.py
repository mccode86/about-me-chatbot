import os
import chromadb
import sqlite3
import time
from datetime import datetime
from fastapi import FastAPI
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pathlib import Path
from anthropic import Anthropic
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat_logs.db"
chroma_path = BASE_DIR / "chroma"

MODEL = "claude-haiku-4-5-20251001"
HAIKU_INPUT_PER_MTOK = 1
HAIKU_OUTPUT_PER_MTOK = 5

app = FastAPI()

anthropic_client = Anthropic()
chroma_client = chromadb.PersistentClient(path=chroma_path)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
    timestamp TEXT,
    model TEXT,
    user_input TEXT,
    assistant_response TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    latency_ms REAL)
    """)
    conn.commit()
    conn.close()


init_db()


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


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat")
def chat(req: ChatMessage) -> ChatResponse:
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
    start = time.time()
    response = anthropic_client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=history
    )
    latency_ms = (time.time() - start) * 1000
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cost_usd = (input_tokens / 1_000_000 * HAIKU_INPUT_PER_MTOK) + (output_tokens / 1_000_000 * HAIKU_OUTPUT_PER_MTOK)

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    INSERT INTO chat_logs (timestamp, model, user_input, assistant_response, input_tokens, output_tokens, cost_usd, latency_ms)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (datetime.now().isoformat(), MODEL, req.message, reply, input_tokens, output_tokens, cost_usd,
                  latency_ms),
                 )
    conn.commit()
    conn.close()
    return ChatResponse(reply=reply)
