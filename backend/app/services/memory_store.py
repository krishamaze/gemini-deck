import chromadb
import uuid
import datetime
import os

class MemoryStore:
    def __init__(self, persistence_path=".gemini_memory"):
        self.client = chromadb.PersistentClient(path=persistence_path)
        self.collection = self.client.get_or_create_collection(name="gemini_interactions")

    def add_interaction(self, user_prompt: str, ai_response: str):
        doc_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # We store the combined text for embedding search
        combined_text = f"User: {user_prompt}\nAI: {ai_response}"
        
        self.collection.add(
            documents=[combined_text],
            metadatas=[{
                "type": "interaction",
                "timestamp": timestamp,
                "user_prompt": user_prompt, # Store separately for retrieval
                "ai_response": ai_response
            }],
            ids=[doc_id]
        )
        return doc_id

    def retrieve_context(self, query: str, n_results: int = 3):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Flatten results
        context_items = []
        if results['metadatas'] and results['metadatas'][0]:
            for meta in results['metadatas'][0]:
                context_items.append(meta)
        
        return context_items

    def get_recent(self, limit: int = 10):
        # Chroma doesn't support 'sort by date' efficiently without ID tricks or fetching all
        # For now, we'll just fetch a batch. In production, use SQLite for the timeline.
        # This is a placeholder for "get recent"
        return self.collection.get(limit=limit)

# Dependency Injection Pattern
_store_instance = None

def get_memory_store():
    global _store_instance
    if _store_instance is None:
        _store_instance = MemoryStore()
    return _store_instance
