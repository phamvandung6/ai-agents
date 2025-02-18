from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.core.settings import settings


class AdmissionVectorStore:
    def __init__(self):
        self.collection_name = "admission_docs"
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.GOOGLE_API_KEY,
        )
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the vector store."""
        self.vector_store.add_documents(documents)

    async def similarity_search(
        self,
        query: str,
        k: int = 4,
    ) -> list[Document]:
        """Search for similar documents."""
        return self.vector_store.similarity_search(query, k=k)

    async def delete_collection(self) -> None:
        """Delete the collection if it exists."""
        collections = self.client.get_collections()
        if self.collection_name in [c.name for c in collections.collections]:
            self.client.delete_collection(self.collection_name)
