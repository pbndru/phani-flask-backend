import yaml
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class ClubLloydsConfig:
    """Configuration class for Club Lloyds RAG system"""

    def __init__(self, config_file: str):
        """
        Initialize configuration from YAML file
        Args:
            config_file: Path to the YAML configuration file
        """
        self.config_file = config_file
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, "r") as f:
                config_data = yaml.safe_load(f)

            # Load configuration values
            self.citation_relevance_threshold = float(
                str(config_data.get("CITATION_RELEVANCE_THRESHOLD", "2.3")).strip()
            )
            self.top_k = int(str(config_data.get("TOP_K", "4")).strip())
            self.topic_class_threshold = float(
                str(config_data.get("TOPIC_CLASS_THRESHOLD", "0.05")).strip()
            )
            self.countries = config_data.get("COUNTRIES", [])
            self.default_response_starters = config_data.get(
                "DEFAULT_RESPONSE_STARTERS", []
            )

            # Load prompts
            self.qa_system_prompt = config_data.get("QA_SYSTEM_PROMPT", "")
            self.format_prompt = config_data.get("FORMAT_PROMPT", "")
            self.contextualize_q_system_prompt = config_data.get(
                "CONTEXTUALIZE_Q_SYSTEM_PROMPT", ""
            )
            self.summarise_prompt_template = config_data.get(
                "SUMMARISE_PROMPT_TEMPLATE", ""
            )
            self.elaborate_prompt_template = config_data.get(
                "ELABORATE_PROMPT_TEMPLATE", ""
            )
            self.follow_up_prompt_template = config_data.get(
                "FOLLOW_UP_PROMPT_TEMPLATE", ""
            )
            self.no_documents_response = config_data.get(
                "NO_DOCUMENTS_IN_CONTEXT_RESPONSE_STRING", ""
            )

            logger.info(f"Configuration loaded successfully from {self.config_file}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_file}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def get_qa_prompt(
        self, context: str, current_date: str, country_prompt: str = ""
    ) -> str:
        """
        Get the formatted QA system prompt
        Args:
            context: The retrieved context documents
            current_date: Current date string
            country_prompt: Optional country-specific prompt
        Returns:
            Formatted QA system prompt
        """
        return self.qa_system_prompt.format(
            context=context,
            current_date=current_date,
            country_prompt=country_prompt,
            format_instructions=self.format_prompt,
        )

    def get_summarise_prompt(self, question: str, answer: str) -> str:
        """Get the formatted summarise prompt"""
        return self.summarise_prompt_template.format(
            question=question, 
            answer=answer
        )

    def get_elaborate_prompt(
        self, question: str, answer: str, context: str
    ) -> str:
        """Get the formatted elaborate prompt"""
        return self.elaborate_prompt_template.format(
            question=question, 
            answer=answer, 
            context=context
        )

    def get_follow_up_prompt(
        self, question: str, answer: str, context: str
    ) -> str:
        """Get the formatted follow-up questions prompt"""
        return self.follow_up_prompt_template.format(
            question=question, 
            answer=answer, 
            context=context
        )
