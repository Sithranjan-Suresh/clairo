import chromadb
import os

DB_PATH = os.environ.get("CHROMA_PATH", "chroma_db")

client = chromadb.PersistentClient(path=DB_PATH)

collection = client.get_or_create_collection(
    name="payer_policies"
)