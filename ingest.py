from pathlib import Path
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import chromadb
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
docs_path = BASE_DIR / "data" / "about_mario.md"
chroma_path = BASE_DIR / "chroma"

text = docs_path.read_text()

chunks = [part.strip() for part in text.split("\n\n") if part.strip()]

ids = [f"mario-{i}" for i in range(len(chunks))]

chroma_client = chromadb.PersistentClient(path=chroma_path)

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ.get("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

collection = chroma_client.get_or_create_collection(
    name="about_mario",
    embedding_function=openai_ef)

collection.add(ids=ids, documents=chunks)

print(f"Added {collection.count()} chunks to the collection")
