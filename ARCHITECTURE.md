# 🗺️ Architecture - About-Me / Docs Chatbot

> A reference for myself. This is the **sketch made before writing any code**,
> plus one level of extra detail. Every box has a **"Under the hood"** note, so
> that when I hit the same step again in another project I already have a picture
> of *what it actually does*. Deliberately **no code** - this is about the way of
> thinking, not syntax.

**Goal:** a user asks a question in plain language -> the bot answers from the
contents of a document (instead of making things up).
**Pattern:** RAG - *Retrieval-Augmented Generation* (Stage 9).

---

## Two separate phases

```
[ INGEST ]  offline, runs ONCE      -> fills the warehouse (vector store)
[ SERVE  ]  online, runs PER question -> uses the warehouse to answer
```

Why split them: SERVE can't run unless the warehouse is already filled -> so
**INGEST goes first**. (In code this becomes two files: `ingest.py` and `main.py`.)

---

## PHASE 1 - INGEST (separate script, runs once whenever the document changes)

```
document (.md)
   -> read its contents
   -> split into chunks
   -> give each chunk an id
   -> [set up the embedding function]
   -> store in the vector store      ← embedding happens AUTOMATICALLY here
```

**1. Read the document**
Open the file, pull all of its text into one long string in memory.

**2. Split into chunks**
Cut the long text into small, self-standing pieces (e.g. one per paragraph).
*Under the hood:* the point is that later, when searching, we grab the **small
relevant pieces** rather than the whole document (too expensive + blows past the
context window). Each chunk should ideally be **self-contained** (one topic, not
starting with a dangling "He...").

**3. Give each chunk an id**
Assign a unique label to each piece (e.g. `chunk-0`, `chunk-1`, ...).
*Under the hood:* the id lets the vector store save and tell pieces apart. Bonus:
if the ids are stable, **re-running won't create duplicates** (idempotent) - a
chunk whose id already exists gets skipped/updated instead of added again.

**4. Set up the embedding function**
Choose and configure the "translator" that will turn text into a vector (a list
of numbers).
*Under the hood:* **nothing is translated yet here** - you're only preparing the
tool (which embedding model, which API key). Like hiring a translator and naming
the target language.

**5. Store in the vector store** *(embedding happens automatically in this step)*
Hand the chunks to the vector DB (e.g. ChromaDB).
*Under the hood:* for each chunk -> the embedding function calls the API -> the
text is turned into a **vector** (~1536 numbers capturing its **meaning**) -> the
vector + text + id are stored together. So "embed" and "store", which look like
two boxes in the sketch, **collapse into a single step in code** because the DB
calls the embedding function for you. After this, the warehouse is ready to be
searched.

---

## PHASE 2 - SERVE (API, runs on every question)

```
user question comes in
   -> save to history
   -> find relevant chunks in the vector store    (RETRIEVE)
   -> assemble the prompt: system + context + history    (AUGMENT)
   -> call the LLM                                (GENERATE)
   -> take the answer text
   -> save the answer to history
   -> return the answer to the user
        ↳ (side) record the turn to the log
```

**1. Question comes in**
The endpoint receives the user's question (text) over HTTP.

**2. Save to history**
Append the question to the conversation list.
*Under the hood:* the LLM is **stateless** (it remembers nothing between calls -
Stage 7.6). So that follow-ups like *"tell me more"* stay coherent, we send the
**entire** history every time, and turns must alternate user↔assistant.

**3. Find relevant chunks in the vector store (RETRIEVE)** ← *the heart of RAG*
Fetch the document pieces that best match the question.
*Under the hood (4 small steps):*
  1. The user's question is **embedded first** into a vector - using the **SAME**
     embedding function as ingest (must match so they're comparable).
  2. The vector store **compares** that question-vector against all stored
     chunk-vectors, scoring "closeness in meaning" (**cosine similarity** -
     Stage 9.3).
  3. Take the **top-N** chunks whose vectors are closest (e.g. `n_results=5`).
  4. Return the text of those chunks.
  -> The key: it searches by **MEANING, not exact words**. A question about
    "salary" can find a chunk that says "compensation" because the meanings are
    close. And the one doing the searching is the **vector store (Chroma), not
    the LLM**.

**4. Assemble the prompt (AUGMENT)**
Combine everything into one package for the LLM:
  - **System prompt** = behavior instructions ("answer ONLY from the context; if
    it's not there, say you don't know").
  - **Context** = the chunks just retrieved in step 3.
  - **History** = the prior conversation.
  - The user's **question**.
*Under the hood:* this is where "retrieval" connects to "generation" - the search
results are injected as the raw material for the answer. The bot is **only as
honest as the context it's given**.

**5. Call the LLM (GENERATE)**
Send that package to Claude (with config: `model`, `max_tokens`).
*Under the hood:* Claude reads the context + question -> composes a natural-language
answer that **leans on** the context. It isn't recalling facts from its "memory";
it's stitching together what you handed it.

**6. Take the answer text**
From the LLM response, pull out the text part (a response can contain several
"blocks"; for plain chat, take the first text block).

**7. Save the answer to history**
Append the assistant's answer to the conversation list.
*Under the hood:* without this, the next turn breaks - "it"/"that" has no
referent, and the user↔assistant alternation is broken (can error).

**8. Return the answer to the user**
Send the answer text back as the API response (wrapped in a typed shape -
Pydantic).

**9. (side) Record the turn to the log**
Save metrics: tokens used, cost, latency, question + answer.
*Under the hood:* for cost monitoring & debugging. It **doesn't change the
answer** to the user - purely internal.

---

## Config / decisions (decided once, not steps in the flow)

`model` · `max_tokens` · `n_results` (how many chunks to fetch) · embedding model ·
chunking strategy (size/overlap).

> Note from experience: if the document set grows but `n_results` is too small,
> the bot can say "I don't know" even though the info IS there. Raise `n_results`.
> (This is a "knob" you turn while tuning, not while planning.)

---

## Components - the technology that fills each box

| Box | Technology |
|---|---|
| Serve / endpoint | FastAPI |
| Vector store | ChromaDB |
| Embed text | OpenAI embeddings |
| LLM (answering) | Anthropic (Claude) |
| Log | SQLite |
| Request/response types | Pydantic |
| Tests | pytest |

---

## ❌ Deliberately NOT decided at the sketch stage

Syntax, function names, exact arguments. That's handled **while coding** -> docs /
AI / autocomplete. (This is the "high-pass at 100hz" - decided on the fly, not
during planning.)

---

## 🧩 This is a TEMPLATE

Swap "documents about Mario" for "company documents" and the skeleton is
**exactly the same**. This RAG pattern is reused for any "chatbot that answers
from documents". Keep it in your head as one entry in your "pattern library".

**Coding order = follow the sketch top to bottom** - the dependencies are already
resolved, so there's no more "getting confused at the end".
