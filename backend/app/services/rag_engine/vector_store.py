import os
import chromadb
from chromadb.utils import embedding_functions

# Initialize the Chroma client, storing data in the local filesystem
CHROMA_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "infrastructure", "cache", "chroma_db")
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# Use a fast local sentence-transformer model by default
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

class VectorStore:
    def __init__(self, collection_name: str):
        self.collection = chroma_client.get_or_create_collection(
            name=collection_name, 
            embedding_function=sentence_transformer_ef
        )
        
    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """Indexes a document segment into the vector store."""
        # Simple splitting can be done by the caller; here we assume text is a chunk
        self.collection.upsert(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
        
    def query_context(self, query_text: str, n_results: int = 3) -> list[str]:
        """Retrieves the top N most relevant context fragments for a query."""
        if self.collection.count() == 0:
            return []
            
        # Ensure we don't request more results than documents available
        n_results = min(n_results, self.collection.count())
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return []
            
        return results['documents'][0]
