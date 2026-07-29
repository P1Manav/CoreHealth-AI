# Knowledge base ingestion — fetches sources, chunks, embeds, and stores in Chroma.
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.rag.ingestion import ingest_to_chroma

if __name__ == "__main__":
    print("Healthcare AI — Knowledge Base Ingestion\n")
    count = ingest_to_chroma()
    print(f"\n✅ Done! {count} chunks ingested. Start server with: python run.py")
