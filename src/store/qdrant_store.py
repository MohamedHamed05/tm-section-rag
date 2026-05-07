from qdrant_client import QdrantClient, models
from uuid import uuid4 

class QdrantStore:
    def __init__(self, url: str = "", port: int = 6333, api_key: str | None = None):
        self.client = QdrantClient(url=url)

    def create_collection(self, collection_name: str, vector_size: int):
        if collection_name not in self.client.get_collections().collections:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
            )

    def upsert_vectors(self, collection_name: str, vectors: list[dict]):
        self.client.upsert(collection_name=collection_name, 
                           points=[models.PointStruct(id=str(uuid4()), vector=vec["embedding"], payload=vec["metadata"]) for vec in vectors])

    def search_vectors(self, collection_name: str, query_vector: list[float], top_k: int = 5):
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )

        return results.points
    
    def delete_collection(self, collection_name: str):
        self.client.delete_collection(collection_name=collection_name)