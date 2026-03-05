"""
RAG Service - Integration with A-Cubed Data Science Project
This module handles the Retrieval-Augmented Generation functionality
"""

import os
import logging
from typing import List, Dict, Tuple, Optional

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG Service for document retrieval and answer generation.
    Integrates with the data science project's processed data.
    """

    def __init__(self, vector_store_path: Optional[str] = None):
        self.vector_store_path = vector_store_path or os.getenv("VECTOR_STORE_PATH")
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")
        self.vector_store = None
        self.qa_chain = None

        # Initialize the RAG system
        self._initialize_rag()

    def _initialize_rag(self):
        """Initialize the RAG system with vector store and QA chain"""
        try:
            # Try to load existing vector store
            if self.vector_store_path and os.path.exists(self.vector_store_path):
                logger.info(f"Loading existing vector store from {self.vector_store_path}")
                # Note: allow_dangerous_deserialization=True is required for local FAISS loads
                self.vector_store = FAISS.load_local(
                    self.vector_store_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                logger.info("Creating new vector store from documents")
                self._create_vector_store()

            # Create QA chain
            self._create_qa_chain()
        except Exception as e:
            logger.error(f"Error initializing RAG system: {e}")
            # Fallback: create empty vector store
            self.vector_store = FAISS.from_texts(["Sample document"], self.embeddings)
            self._create_qa_chain()

    def _create_vector_store(self):
        """Create vector store from documents"""
        # Look for documents in the data science project
        data_science_path = "../a-cubed-data-science/data/processed"
        documents = []

        # Try to load documents from various sources
        if os.path.exists(data_science_path):
            try:
                loader = DirectoryLoader(
                    data_science_path, 
                    glob="**/*.txt", 
                    loader_cls=TextLoader
                )
                documents.extend(loader.load())
            except Exception as e:
                logger.warning(f"Could not load documents from {data_science_path}: {e}")

        # If no documents found, create sample documents
        if not documents:
            logger.info("No documents found, creating sample documents")
            sample_docs = [
                "Club Lloyds offers exclusive rewards and benefits for banking customers including cashback, points, and special offers.",
                "Information about current accounts, savings accounts, mortgages, and personal loans available through Lloyds Bank.",
                "Guidelines for online banking, mobile app features, and digital payment services.",
                "Rewards program details including how to earn points, redeem rewards, and access exclusive member benefits."
            ]
            documents = [Document(page_content=doc) for doc in sample_docs]

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200))
        )
        split_docs = text_splitter.split_documents(documents)

        # Create vector store
        self.vector_store = FAISS.from_documents(split_docs, self.embeddings)

        # Save vector store if path is provided
        if self.vector_store_path:
            os.makedirs(os.path.dirname(self.vector_store_path), exist_ok=True)
            self.vector_store.save_local(self.vector_store_path)
            logger.info(f"Vector store saved to {self.vector_store_path}")

    def _create_qa_chain(self):
        """Create the QA chain with custom prompt"""
        prompt_template = """
        You are a helpful assistant for Club Lloyds banking and rewards service. 
        Use the following context to answer questions about banking services, rewards, account management, and financial products. 
        If you don't know the answer, say that you don't have enough information to provide a complete answer.

        Context: {context}
        Question: {question}
        Answer:
        """
        prompt = PromptTemplate(
            template=prompt_template, 
            input_variables=["context", "question"]
        )
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )

    def query(self, question: str, chat_history: List[Dict] = None) -> Tuple[str, List[Dict]]:
        """
        Process a query and return answer with citations
        """
        try:
            context_question = question
            if chat_history:
                recent_context = " ".join([
                    f"Previous: {item.get('question', '')} {item.get('answer', '')}" 
                    for item in chat_history[-2:] # Last 2 exchanges
                ])
                context_question = f"Context: {recent_context}\n\nCurrent question: {question}"

            # Get response from QA chain
            result = self.qa_chain.invoke({"query": context_question})
            answer = result["result"]
            source_docs = result.get("source_documents", [])

            # Format citations
            citations = []
            for i, doc in enumerate(source_docs):
                citations.append({
                    "id": i + 1,
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "source": doc.metadata.get("source", f"Document {i + 1}")
                })

            logger.info(f"Query processed: {question[:50]}...")
            return answer, citations
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "I apologize, but I encountered an error processing your question. Please try again.", []

    def get_similar_documents(self, query: str, k: int = 5) -> List[Dict]:
        """Get similar documents for a query"""
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": 0.8  # Placeholder score
                } for doc in docs
            ]
        except Exception as e:
            logger.error(f"Error retrieving similar documents: {e}")
            return []
