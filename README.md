# About-Me Chatbot

A retrieval-augmented (RAG) chatbot that answers questions about **Mario Christian** - his background, skills, and projects. Built as a FastAPI backend, grounded in a personal knowledge base, and deployed live.

**🔗 Live API:** https://web-production-93348.up.railway.app
**Try it interactively:** https://web-production-93348.up.railway.app/docs

## What it does

- **Grounded answers (RAG):** retrieves the most relevant chunks from a personal knowledge base and answers *only* from them - so it doesn't make things up. Ask about something outside the docs and it replies *"I don't know."*
- **Conversational:** keeps multi-turn history, so follow-ups like *"tell me more about that"* resolve correctly.
- **Observability:** every turn is logged to SQLite with the model, token counts, USD cost, and latency.
- **Typed API:** request and response are validated with Pydantic and documented automatically.

## Tech stack

| Layer | Tool |
|---|---|
| API | FastAPI (Python 3.12) |
| LLM | Anthropic SDK - Claude Haiku 4.5 |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector store | ChromaDB |
| Validation | Pydantic |
| Logging | SQLite |
| Tests | pytest (unit + LLM evals) |
| Deploy | Railway |

## How it works

1. **Index (once):** `ingest.py` splits `data/about_mario.md` into chunks, embeds them with OpenAI, and stores them in ChromaDB.
2. **Per request:** `/chat` retrieves the top-3 relevant chunks, injects them as context into a grounded system prompt, sends it to Claude (with conversation history), returns the reply, and logs the turn to SQLite.

## API

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| GET | `/health` | - | `{"status": "ok"}` |
| POST | `/chat` | `{"message": "..."}` | `{"reply": "..."}` |

## Run locally

```bash
# 1. Clone & enter
git clone https://github.com/mccode86/about-me-chatbot.git
cd about-me-chatbot

# 2. Virtual env + dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. API keys - copy the example and fill in your keys
cp .env.example .env
#   ANTHROPIC_API_KEY=...
#   OPENAI_API_KEY=...

# 4. (Optional) Rebuild the vector store - the repo already ships chroma/,
#    but if you edit data/about_mario.md, rebuild it:
python ingest.py

# 5. Run the server
python -m uvicorn main:app --reload
#   -> http://localhost:8000/docs
```

## Tests

```bash
python -m pytest -v
```

Includes a deterministic unit test (`/health`) plus two **LLM evals** that check answer quality: that the bot retrieves a correct fact, and that it says *"I don't know"* for out-of-context questions.
