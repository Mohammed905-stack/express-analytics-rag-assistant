from typing import Literal
from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator('question')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Question cannot be blank')
        return value.strip()


class Source(BaseModel):
    citation: int
    chunk_id: str
    document_id: str
    title: str
    source: str
    excerpt: str


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    status: Literal['answered', 'insufficient_context']
    sources: list[Source]
    retries: int
    query_type: str
    trace: list[dict]


class FeedbackRequest(BaseModel):
    query_id: str = Field(min_length=1, max_length=100)
    rating: Literal['up', 'down']
    comment: str | None = Field(default=None, max_length=2000)


class Analysis(BaseModel):
    search_query: str = Field(min_length=1, max_length=2000)
    query_type: Literal['conceptual', 'how-to', 'troubleshooting', 'API reference']


class Grade(BaseModel):
    relevant: bool
    reason: str = Field(max_length=1000)


class Draft(BaseModel):
    answer: str = Field(min_length=1)
    citation_ids: list[str] = Field(description='Unique supplied IDs such as S1, S2 without brackets; exactly match inline [[S1]] labels in answer.')
    sufficient_context: bool


class Grounding(BaseModel):
    supported: bool
    reason: str = Field(max_length=1000)
