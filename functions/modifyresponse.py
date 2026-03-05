import logging
import os
from typing import List
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def _get_llm():
    """Get Azure OpenAI LLM instance"""
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_CHAT_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_CHAT_API_KEY"),
        api_version="2024-02-15-preview",
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o-mini"),
        temperature=0.0,
    )

def summarise_response(question: str, answer: str, config) -> str:
    """
    Generate a summarised version of the answer
    Args:
        question: Original question
        answer: Original answer
        config: ClubLloydsConfig instance
    Returns:
        Summarised answer
    """
    try:
        logger.info("Generating summarised response")
        llm = _get_llm()
        prompt_text = config.get_summarise_prompt(question, answer)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that summarises information concisely."),
            ("human", prompt_text),
        ])
        
        chain = prompt | llm
        result = chain.invoke({})
        summarised = result.content
        
        logger.info("Summarised response generated successfully")
        return summarised
    except Exception as e:
        logger.error(f"Error generating summarised response: {e}")
        return "I apologize, but I couldn't generate a summary. Please try again."

def elaborate_response(question: str, answer: str, context: List[dict], config) -> str:
    """
    Generate an elaborated version of the answer
    Args:
        question: Original question
        answer: Original answer
        context: Context documents/citations
        config: ClubLloydsConfig instance
    Returns:
        Elaborated answer
    """
    try:
        logger.info("Generating elaborated response")
        llm = _get_llm()
        
        # Format context
        context_str = "\n\n".join([
            f"Document {i+1}:\n{doc.get('content', '')}" 
            for i, doc in enumerate(context)
        ])
        
        prompt_text = config.get_elaborate_prompt(question, answer, context_str)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that provides detailed explanations."),
            ("human", prompt_text),
        ])
        
        chain = prompt | llm
        result = chain.invoke({})
        elaborated = result.content
        
        logger.info("Elaborated response generated successfully")
        return elaborated
    except Exception as e:
        logger.error(f"Error generating elaborated response: {e}")
        return "I apologize, but I couldn't generate an elaborated response. Please try again."

def generate_follow_up_qs(question: str, answer: str, context: List[dict], config) -> List[str]:
    """
    Generate follow-up questions based on the answer
    Args:
        question: Original question
        answer: Original answer
        context: Context documents/citations
        config: ClubLloydsConfig instance
    Returns:
        List of follow-up questions
    """
    try:
        logger.info("Generating follow-up questions")
        llm = _get_llm()
        
        # Format context
        context_str = "\n\n".join([
            f"Document {i+1}:\n{doc.get('content', '')}" 
            for i, doc in enumerate(context)
        ])
        
        prompt_text = config.get_follow_up_prompt(question, answer, context_str)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that generates relevant follow-up questions."),
            ("human", prompt_text),
        ])
        
        chain = prompt | llm
        result = chain.invoke({})
        
        # Parse the response to extract questions
        response_text = result.content.strip()
        
        # Try to parse as a Python list
        try:
            import ast
            follow_up_questions = ast.literal_eval(response_text)
            if isinstance(follow_up_questions, list):
                logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
                return follow_up_questions[:3]
        except (ValueError, SyntaxError):
            # If parsing fails, split by newlines and clean up
            lines = response_text.split("\n")
            follow_up_questions = [
                line.strip().lstrip("-*").strip() 
                for line in lines 
                if line.strip() and not line.strip().startswith("[")
            ]
            follow_up_questions = [q for q in follow_up_questions if q][:3]
            
        logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
        return follow_up_questions
        
    except Exception as e:
        logger.error(f"Error generating follow-up questions: {e}")
        return [
            "What other Club Lloyds benefits are available?",
            "How do I become a Club Lloyds member?",
            "What are the membership requirements?",
        ]
