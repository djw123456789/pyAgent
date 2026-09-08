from agents import OpenAIResponsesModel, set_tracing_disabled
from openai import AsyncOpenAI

from app.core.config import settings

set_tracing_disabled(True)

deepseek_client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
)

deepseek_model = OpenAIResponsesModel(
    model=settings.DEEPSEEK_MODEL,
    openai_client=deepseek_client,
)