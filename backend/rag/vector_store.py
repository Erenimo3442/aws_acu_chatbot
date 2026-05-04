import os
from typing import List

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever

from logging import getLogger

logger = getLogger(__name__)

VECTOR_STORE_PERSIST_DIR = os.getenv("VECTOR_STORE_PERSIST_DIR", "/var/lib/chromadb")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_EMBEDDING_MODEL_ID = os.getenv(
    "OLLAMA_EMBEDDING_MODEL_ID", "nomic-embed-text-v2-moe"
)


class VectorStoreManager:
    """Manages ChromaDB vector store using Ollama for embeddings.

    Embedding inference runs on the Ollama service (GPU-accelerated if available).
    No model downloads — Ollama handles everything via its HTTP API.
    """

    def __init__(
        self,
        persist_directory: str = VECTOR_STORE_PERSIST_DIR,
        embedding_model_id: str = OLLAMA_EMBEDDING_MODEL_ID,
        base_url: str = OLLAMA_BASE_URL,
    ):
        self.persist_directory = persist_directory
        self.embeddings = OllamaEmbeddings(
            model=embedding_model_id,
            base_url=base_url,
        )
        self.vectorstore = self.get_vector_store()

    def load_vectorstore(self) -> Chroma | None:
        """Load existing vector store from persist directory."""
        try:
            if os.path.exists(self.persist_directory):
                logger.info(
                    "Loading existing Chroma database from %s...",
                    self.persist_directory,
                )
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                )
                logger.info("Existing vector store loaded")
                return self.vectorstore
            else:
                logger.info("No existing vector store found at %s", self.persist_directory)
                return None
        except Exception as e:
            logger.error("Failed to load vector store: %s (%s)", type(e).__name__, e)
            return None

    def create_vectorstore(self, chunks: List[Document] | None = None) -> Chroma:
        """Create a new vector store from chunks.

        If no chunks are provided, demo seed documents are used as fallback.
        """
        if not chunks or len(chunks) == 0:
            from .web_scrape_processor import WebScrapeProcessor
            processor = WebScrapeProcessor()
            chunks, doc_count = processor.process_all_documents()
            logger.info(
                "Creating new vector store from %d demo documents (%d chunks)",
                doc_count, len(chunks),
            )
        else:
            logger.info(
                "Creating new vector store at %s with %d chunks",
                self.persist_directory, len(chunks),
            )

        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
        )
        logger.info("New vector store created")
        return self.vectorstore

    def get_vector_store(self) -> Chroma:
        """Get vector store, loading existing or creating new if needed."""
        vectorstore = self.load_vectorstore()
        if vectorstore:
            return vectorstore
        else:
            return self.create_vectorstore()

    def add_chunks(self, chunks: List[Document]) -> bool:
        """
        Add new chunks to the existing vector store (incremental).

        Args:
            chunks: List of chunk objects to add.
        Returns:
            True if successful, False otherwise.
        """
        if not chunks:
            logger.warning("No chunks to add to vector store")
            return False

        try:
            logger.info("Adding %d new chunks to existing vector store...", len(chunks))
            self.vectorstore.add_documents(chunks)
            logger.info("%d chunks added to vector store", len(chunks))
            return True
        except Exception as e:
            logger.error("Failed to add documents to vector store: %s (%s)",
                         type(e).__name__, e)
            return False
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Perform a similarity search on the vector store."""
        return self.vectorstore.similarity_search(query, k=k)

    def get_retriever(self, k: int = 4) -> VectorStoreRetriever:
        """Return a retriever configured for similarity search."""
        return self.vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": k}
        )


def init_vector_store_manager():
    """Initialize the vector store manager and return it with a retriever."""
    vsm = VectorStoreManager(
        persist_directory=VECTOR_STORE_PERSIST_DIR,
        embedding_model_id=OLLAMA_EMBEDDING_MODEL_ID,
        base_url=OLLAMA_BASE_URL,
    )
    return vsm, vsm.get_retriever(k=3)
