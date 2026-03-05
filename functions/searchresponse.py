import logging
import os
from datetime import datetime
from typing import List, Tuple, Optional

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def generate_response(
    question: str, 
    chat_history: List[dict], 
    config, 
    location: Optional[str] = None,
) -> Tuple[str, List[dict], bool]:
    """
    Generate a response to a user question using RAG
    
    Args:
        question: User's question
        chat_history: Previous chat messages
        config: ClubLloydsConfig instance
        location: Optional location parameter (not used for Club Lloyds)
        
    Returns:
        Tuple of (answer, citations, default_response_flag)
    """
    try:
        logger.info(f"Processing question: {question}")

        # Initialize Azure OpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_CHAT_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_CHAT_API_KEY"),
            api_version="2024-02-15-preview",
            deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o-mini"),
            temperature=0.0,
        )

        # Initialize embeddings
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"),
        )

        # Initialize Azure Search vector store
        vector_store = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT"),
            azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "rag-index"),
            embedding_function=embeddings.embed_query,
        )

        # Create retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": config.top_k},
        )

        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Create prompt template
        system_prompt = config.get_qa_prompt(
            context="{context}",
            current_date=current_date,
            country_prompt="",
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        # Create the RAG chain
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        # Execute the chain
        result = rag_chain.invoke({"input": question})
        answer = result.get("answer", "")
        context_docs = result.get("context", [])

        # Extract citations
        citations = []
        for doc in context_docs:
            citation = {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "title": doc.metadata.get("title", "Club Lloyds Document"),
            }
            citations.append(citation)

        # Check if default response
        default_response = any(
            answer.lower().startswith(starter) 
            for starter in config.default_response_starters
        )

        logger.info(f"Generated answer with {len(citations)} citations")
        return answer, citations, default_response

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return (
            "I apologize, but I encountered an error processing your question. Please try again.",
            [],
            True,
        )
