"""Gemini boundary; workflow tests replace this boundary, never production answers."""
import json
import threading
from typing import Protocol
from google import genai
from google.genai import types
from pydantic import BaseModel


class ProviderError(Exception):
    """Safe actionable message for the API; never include private SDK error text."""


class Provider(Protocol):
    def structured(self, instructions: str, payload: dict, schema: type[BaseModel]) -> BaseModel: ...
    def embed(self, texts: list[str], *, query: bool = False) -> list[list[float]]: ...


class GeminiProvider:
    def __init__(self, settings):
        self.settings = settings
        self._client = None
        self._lock = threading.Lock()

    def client(self):
        if not self.settings.api_key:
            raise ProviderError('Gemini API key is missing. Run SETUP_KEY.cmd, then restart START.cmd.')
        with self._lock:
            if self._client is None:
                self._client = genai.Client(api_key=self.settings.api_key,
                    http_options=types.HttpOptions(timeout=60000))
            return self._client

    def structured(self, instructions, payload, schema):
        client = self.client()
        try:
            response = client.models.generate_content(model=self.settings.model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(system_instruction=instructions,
                    response_mime_type='application/json', response_schema=schema, temperature=0))
        except Exception as exc:
            raise self._error(exc, 'text model') from exc
        try:
            if not response.text:
                raise ValueError('No response text')
            return schema.model_validate_json(response.text)
        except Exception as exc:
            raise ProviderError('Gemini returned an invalid structured response. Try again or check GEMINI_MODEL.') from exc

    def embed(self, texts, *, query=False):
        if not texts:
            return []
        client = self.client()
        try:
            response = client.models.embed_content(model=self.settings.embedding_model, contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=self.settings.dimensions,
                    task_type='RETRIEVAL_QUERY' if query else 'RETRIEVAL_DOCUMENT'))
            vectors = [list(embedding.values) for embedding in (response.embeddings or [])]
            if len(vectors) != len(texts) or any(len(v) != self.settings.dimensions for v in vectors):
                raise ValueError('Embedding shape differs from requested dimensions')
            return vectors
        except Exception as exc:
            raise self._error(exc, 'embedding model') from exc

    @staticmethod
    def _error(exc, operation):
        code = getattr(exc, 'code', None)
        if code in (401, 403):
            return ProviderError('Gemini authentication or access failed. Check your key and model permissions, then restart.')
        if code == 429:
            return ProviderError('Gemini quota or rate limit reached. Wait and check your account quota before retrying.')
        if code == 503:
            return ProviderError('Gemini reports temporary high demand or service unavailability. Try again later or choose another text model in .env and restart.')
        if code == 404:
            return ProviderError(f'Gemini {operation} is unavailable for this account. Check the model name in .env.')
        return ProviderError(f'Gemini {operation} request failed. Check internet, key, model access and quota. No private error details are exposed.')

    def close(self):
        if self._client is not None:
            self._client.close()
