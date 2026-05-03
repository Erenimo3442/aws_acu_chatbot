# import asyncio

# from langchain_core.documents import Document
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_chroma import Chroma
# from langchain_core.vectorstores import VectorStoreRetriever
# from typing import List
# import os

# from .. import printmeup as pm
# from .web_scrape_processor import WebScrapeProcessor 

# VECTOR_STORE_PERSIST_DIR = os.getenv("VECTOR_STORE_PERSIST_DIR", "chromadb-data")
# HGF_EMBEDDING_MODEL_ID = os.getenv("HGF_EMBEDDING_MODEL_ID", "BAAI/bge-small-en-v1.5")

# class VectorStoreManager:
#     def __init__(
#         self,
#         persist_directory: str = VECTOR_STORE_PERSIST_DIR,
#         hgf_embedding_model_id: str = HGF_EMBEDDING_MODEL_ID,
#     ):
#         self.persist_directory = persist_directory
#         self.embeddings = HuggingFaceEmbeddings(
#             model_name=hgf_embedding_model_id, model_kwargs={"trust_remote_code": True}
#         )
#         self.web_scrape_processor = WebScrapeProcessor()
#         self.vectorstore = self.get_vector_store()

#     def load_vectorstore(self) -> Chroma | None:
#         """Load existing vector store from persist directory."""
#         try:
#             if os.path.exists(self.persist_directory):
#                 pm.deb(
#                     f"Loading existing Chroma database from {self.persist_directory}..."
#                 )
#                 self.vectorstore = Chroma(
#                     persist_directory=self.persist_directory,
#                     embedding_function=self.embeddings,
#                 )
#                 pm.inf("Existing vector store loaded")
#                 return self.vectorstore
#             else:
#                 pm.deb(f"No existing vector store found at {self.persist_directory}")
#                 return None
#         except Exception as e:
#             pm.err(e)
#             return None

#     def create_vectorstore(self, chunks: List[Document] | None = None) -> Chroma:
#         """Create vector store from chunks."""
#         doc_count = None
#         if not chunks or len(chunks) == 0:
#             chunks, doc_count = self.web_scrape_processor.process_all_documents()

#         pm.inf(
#             f"Creating new vector store at {self.persist_directory}, with {len(chunks)} chunks"
#             + f" from {doc_count} documents."
#             if doc_count
#             else ""
#         )
#         self.vectorstore = Chroma.from_documents(
#             documents=chunks,
#             embedding=self.embeddings,
#             persist_directory=self.persist_directory,
#         )
#         pm.suc("New vector store created")
#         return self.vectorstore

#     def get_vector_store(self) -> Chroma:
#         """Get vector store, loading existing or creating new if needed."""
#         vectorstore = self.load_vectorstore()
#         if vectorstore:
#             return vectorstore
#         else:
#             return self.create_vectorstore()

#     def add_chunks(self, chunks: List[Document]) -> bool:
#         """Add new chunks to the existing vector store (incremental).

#         Args:
#             chunks: List of chunk objects to add.
#         Returns:
#             True if successful, False otherwise.
#         """
#         if not chunks:
#             pm.war("No chunks to add to vector store")
#             return False

#         try:
#             pm.deb(f"Adding {len(chunks)} new chunks to existing vector store...")
#             self.vectorstore.add_documents(chunks)
#             pm.deb(f"{len(chunks)} chunks added to vector store")
#             return True
#         except Exception as e:
#             pm.err(e=e, m="Failed to add documents to vector store")
#             return False

#     def add_documents(self, documents: List[Document]) -> bool:
#         pm.deb(f"Adding {len(documents)} new documents to vector store...")
#         return self.add_chunks(self.web_scrape_processor.split_documents_into_chunks(documents))

#     def similarity_search(self, query: str, k: int = 4) -> List[Document] | None:
#         """Perform a similarity search on the vector store.

#         Args:
#             query (str): The query string to search for.
#             k (int, optional): The number of similar documents to return. Defaults to 4.
#         Returns:
#             List[Document] | None: List of similar documents or None if vector store is not loaded.
#         """

#         return self.vectorstore.similarity_search(query, k=k)

#     def get_retriever(self, k: int = 4) -> VectorStoreRetriever:
#         return self.vectorstore.as_retriever(
#             search_type="similarity", search_kwargs={"k": k}
#         )

# # * Django way
# def init_vector_store_manager():
#     vsm = VectorStoreManager(
#         persist_directory=VECTOR_STORE_PERSIST_DIR,
#         hgf_embedding_model_id=HGF_EMBEDDING_MODEL_ID,
#     )
#     return vsm, vsm.get_retriever(k=3)

# # * FastAPI way
# # async def init_vector_store_manager(app):
# #     loop = asyncio.get_event_loop()
# #     vsm = await loop.run_in_executor(
# #         None,
# #         VectorStoreManager,
# #         VECTOR_STORE_PERSIST_DIR,
# #         HGF_EMBEDDING_MODEL_ID,
# #     )
# #     app.state.vsm = vsm
# #     app.state.retriever = vsm.get_retriever(k=3)
# #     pm.suc("Vector store initialized")

import heapq
from collections import defaultdict, Counter

# Node class for Huffman tree
class HuffmanNode:
    def __init__(self, char=None, freq=0):
        self.char = char
        self.freq = freq
        self.left: HuffmanNode | None = None
        self.right: HuffmanNode | None = None

    # To make nodes comparable in the priority queue
    def __lt__(self, other):
        return self.freq < other.freq

# Function to build Huffman tree
def build_huffman_tree(text):
    if not text:
        return None

    frequency = Counter(text)
    priority_queue = [HuffmanNode(char, freq) for char, freq in frequency.items()]
    heapq.heapify(priority_queue)

    while len(priority_queue) > 1:
        node1 = heapq.heappop(priority_queue)
        node2 = heapq.heappop(priority_queue)
        
        merged = HuffmanNode(freq=node1.freq + node2.freq)
        merged.left = node1
        merged.right = node2
        
        heapq.heappush(priority_queue, merged)

    return priority_queue[0]  # Root node

# Function to generate Huffman codes from tree
def generate_codes(node, prefix="", codebook=None):
    if codebook is None:
        codebook = {}
    
    if node is not None:
        if node.char is not None:
            codebook[node.char] = prefix
        
        generate_codes(node.left, prefix + "0", codebook)
        generate_codes(node.right, prefix + "1", codebook)
    
    return codebook

# Function to encode a string using Huffman coding
def huffman_encode(text):
    root = build_huffman_tree(text)
    codes = generate_codes(root)
    encoded_text = ''.join(codes[char] for char in text)
    return encoded_text, codes

# Function to decode a Huffman encoded string
def huffman_decode(encoded_text, codes):
    reverse_codes = {v: k for k, v in codes.items()}
    current_code = ""
    decoded_text = ""
    
    for bit in encoded_text:
        current_code += bit
        if current_code in reverse_codes:
            decoded_text += reverse_codes[current_code]
            current_code = ""
            
    return decoded_text

# Example usage
if __name__ == "__main__":
    text = "this is an example for huffman encoding"
    encoded, codebook = huffman_encode(text)
    
    print("Huffman Codes:", codebook)
    print("Encoded Text:", encoded)
    
    decoded = huffman_decode(encoded, codebook)
    print("Decoded Text:", decoded)

