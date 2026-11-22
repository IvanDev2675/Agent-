from dataclasses import dataclass, field

from openai import AzureOpenAI, OpenAI

from .config import Settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON crudo tal como lo devuelve el modelo


@dataclass
class ChatReply:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient:
    """Envoltorio sobre Azure OpenAI (chat y embeddings)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        endpoint = settings.aoai_endpoint.rstrip("/")
        if "services.ai.azure.com" in endpoint:
            if not settings.aoai_api_key:
                raise ValueError("Azure AI Foundry requiere una API key para este endpoint")
            base_url = endpoint if endpoint.endswith("/openai/v1") else f"{endpoint}/openai/v1"
            self._client = OpenAI(base_url=f"{base_url}/", api_key=settings.aoai_api_key)
            return

        kwargs = {"azure_endpoint": endpoint, "api_version": settings.aoai_api_version}
        if settings.aoai_api_key:
            kwargs["api_key"] = settings.aoai_api_key
        else:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
        self._client = AzureOpenAI(**kwargs)

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self.settings.embedding_deployment, input=texts)
        return [d.embedding for d in resp.data]

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatReply:
        kwargs = {"model": self.settings.chat_deployment, "messages": messages, "temperature": 0.1}
        if tools:
            kwargs["tools"] = tools
        msg = self._client.chat.completions.create(**kwargs).choices[0].message
        calls = [ToolCall(c.id, c.function.name, c.function.arguments) for c in (msg.tool_calls or [])]
        return ChatReply(content=msg.content, tool_calls=calls)
