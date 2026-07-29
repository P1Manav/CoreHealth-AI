# RAG ingestion — fetch, clean, chunk, embed, and store medical content in Chroma.
import os
import re
import json
import hashlib
from datetime import date
import requests
from app.config import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL_NAME,
)


# Fetch health topics from MedlinePlus API.
def fetch_medlineplus_topics():
    topics = []
    topic_list = [
        "Headache", "Fever", "Diabetes", "Asthma", "Heart Disease",
        "Flu", "Common Cold", "Back Pain", "Allergies", "High Blood Pressure",
        "Arthritis", "Depression", "Anxiety", "Obesity", "Stroke",
        "Pneumonia", "Bronchitis", "Anemia", "Insomnia", "Dehydration",
        "Burns", "Fractures", "Food Poisoning", "Skin Cancer", "Migraine",
    ]
    for topic in topic_list:
        try:
            url = f"https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={topic}&retmax=1"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                content = _extract_text_from_xml(resp.text)
                if content and len(content) > 100:
                    topics.append({
                        "title": topic,
                        "content": content,
                        "source_name": "MedlinePlus (NIH/NLM)",
                        "source_url": f"https://medlineplus.gov/ency/article/{topic.lower().replace(' ', '')}.htm",
                        "retrieved_date": str(date.today()),
                        "license_note": "U.S. government work — public domain",
                    })
        except Exception as e:
            print(f"  ⚠ Failed to fetch {topic}: {e}")
    return topics


# Extract text content from XML response.
def _extract_text_from_xml(xml_text):
    text = re.sub(r'<[^>]+>', ' ', xml_text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    return re.sub(r'\s+', ' ', text).strip()


# Get curated fallback medical documents.
def get_curated_health_content():
    return [
        {
            "title": "Common Cold",
            "content": "The common cold is a viral infection of the upper respiratory tract. Symptoms include runny nose, sore throat, cough, congestion, body aches, sneezing, low-grade fever, and malaise. Treatment focuses on rest, fluids, and symptom relief. Antibiotics are not effective against cold viruses.",
            "source_name": "MedlinePlus (NIH/NLM)",
            "source_url": "https://medlineplus.gov/commoncold.html",
            "retrieved_date": str(date.today()),
            "license_note": "U.S. government work — public domain",
        },
        {
            "title": "Headache Types and Management",
            "content": "Headaches include tension, migraine, and cluster types. Management involves identifying triggers, hydration, sleep, stress reduction, and OTC pain relievers. Seek immediate medical attention for sudden severe headaches or those following head injury.",
            "source_name": "MedlinePlus (NIH/NLM)",
            "source_url": "https://medlineplus.gov/headache.html",
            "retrieved_date": str(date.today()),
            "license_note": "U.S. government work — public domain",
        },
        {
            "title": "Diabetes Overview",
            "content": "Diabetes is a chronic condition affecting blood sugar regulation (Type 1, Type 2, and Gestational). Symptoms include increased thirst, frequent urination, blurred vision, and fatigue. Management includes blood glucose monitoring, healthy diet, exercise, and medication.",
            "source_name": "CDC",
            "source_url": "https://www.cdc.gov/diabetes/about/index.html",
            "retrieved_date": str(date.today()),
            "license_note": "U.S. government work — public domain",
        },
        {
            "title": "Heart Disease Prevention",
            "content": "Coronary artery disease is the most common heart disease. Prevention includes 150 minutes of weekly exercise, heart-healthy diet, weight management, avoiding smoking, limiting alcohol, and regular blood pressure/cholesterol checks.",
            "source_name": "CDC",
            "source_url": "https://www.cdc.gov/heart-disease/about/index.html",
            "retrieved_date": str(date.today()),
            "license_note": "U.S. government work — public domain",
        },
        {
            "title": "Flu (Influenza)",
            "content": "Flu is a contagious respiratory illness caused by influenza viruses. Symptoms include fever, cough, sore throat, muscle aches, and fatigue. Prevention includes annual vaccination, handwashing, and avoiding contact with sick individuals.",
            "source_name": "CDC",
            "source_url": "https://www.cdc.gov/flu/about/index.html",
            "retrieved_date": str(date.today()),
            "license_note": "U.S. government work — public domain",
        },
    ]


# Split text into overlapping token chunks.
def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    words_per_chunk = int(chunk_size * 0.75)
    words_overlap = int(overlap * 0.75)
    chunks = []
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunks.append(' '.join(words[start:end]))
        start = end - words_overlap
        if start <= 0 and end >= len(words):
            break
    return chunks


# Ingest medical documents into Chroma vector storage.
def ingest_to_chroma(embedding_model=None):
    import chromadb
    print("📚 Starting knowledge base ingestion...")
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    documents = get_curated_health_content()
    try:
        api_docs = fetch_medlineplus_topics()
        if api_docs:
            documents.extend(api_docs)
    except Exception as e:
        print(f"  ⚠ API fetch failed: {e}")

    if embedding_model is None:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    all_chunks, all_ids, all_metadatas = [], [], []
    for doc in documents:
        chunks = chunk_text(doc["content"])
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{doc['title']}_{i}_{chunk[:50]}".encode()).hexdigest()
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({
                "source_name": doc["source_name"],
                "source_url": doc["source_url"],
                "retrieved_date": doc["retrieved_date"],
                "license_note": doc["license_note"],
                "title": doc["title"],
                "chunk_index": i,
            })

    all_embeddings = embedding_model.encode(all_chunks).tolist()
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        end = min(i + batch_size, len(all_chunks))
        collection.add(
            ids=all_ids[i:end],
            documents=all_chunks[i:end],
            embeddings=all_embeddings[i:end],
            metadatas=all_metadatas[i:end],
        )
    print(f"✅ Ingested {len(all_chunks)} chunks.")
    return len(all_chunks)
