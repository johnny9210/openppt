"""
LLM Configuration - follows aidx patterns
Uses LangChain SDK with AzureChatOpenAI (GPT) and ChatBedrock (Claude)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# AWS Bedrock (Claude)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-west-2"
CLAUDE_MODEL_ID = os.getenv(
    "CLAUDE_MODEL_ID",
    "us.anthropic.claude-sonnet-4-20250514-v1:0",
)

# Azure OpenAI (GPT)
AZURE_OPENAI_ENDPOINT = os.getenv("APIM_AOAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("APIM_AOAI_API_KEY")
GPT_DEPLOYMENT = os.getenv("GPT_DEPLOYMENT", "gpt-4o")
GPT_API_VERSION = os.getenv("GPT_API_VERSION", "2025-01-01-preview")

# Google AI Studio (Nano Banana - Gemini Image Generation)
GOOGLE_AI_STUDIO_KEY = os.getenv(
    "GOOGLE_AI_STUDIO_KEY", ""
)
GEMINI_IMAGE_MODEL = os.getenv(
    "GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview"
)

# Pipeline Settings
DEFAULT_LLM = os.getenv("DEFAULT_LLM", "claude")
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "3"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
MAX_TOKENS = 8192
GEMINI_THINKING_BUDGET = int(os.getenv("GEMINI_THINKING_BUDGET", "1024"))

# Timeouts (seconds) — deep_research pattern
LLM_TIMEOUT = int(os.getenv("PPT_LLM_TIMEOUT", "600"))
TOTAL_TIMEOUT = int(os.getenv("PPT_TOTAL_TIMEOUT", "1800"))

# Tavily Web Search
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Validator Service
VALIDATOR_URL = os.getenv("VALIDATOR_URL", "http://validator:8001")

# --- LLM Factory (singleton pattern from aidx) ---

_llm_instances: dict = {}


def get_llm(model_type: str | None = None):
    """
    Get LangChain LLM instance.

    Args:
        model_type: "claude" | "gpt" (defaults to DEFAULT_LLM)

    Returns:
        ChatBedrock or AzureChatOpenAI instance
    """
    model_type = (model_type or DEFAULT_LLM).lower()

    if model_type in _llm_instances:
        return _llm_instances[model_type]

    if model_type == "gpt":
        from langchain_openai import AzureChatOpenAI

        instance = AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment=GPT_DEPLOYMENT,
            model=GPT_DEPLOYMENT,
            api_version=GPT_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            streaming=True,
        )
    else:
        # Claude via AWS Bedrock (default)
        import boto3
        from botocore.config import Config
        from langchain_aws import ChatBedrock

        bedrock_config = Config(
            max_pool_connections=25,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=bedrock_config,
        )
        instance = ChatBedrock(
            model_id=CLAUDE_MODEL_ID,
            region_name=AWS_REGION,
            client=bedrock_client,
            streaming=True,
            model_kwargs={
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "anthropic_version": "bedrock-2023-05-31",
            },
        )

    _llm_instances[model_type] = instance
    return instance
