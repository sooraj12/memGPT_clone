import uuid

from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlalchemy_utils import ChoiceType
from sqlmodel import SQLModel, Field
from constants import DEFAULT_HUMAN, DEFAULT_PERSONA, DEFAULT_ENDPOINT
from utils import get_human_text, get_persona_text, get_utc_time
from pydantic import ConfigDict


class LLMConfigModel(BaseModel):
    model: Optional[str] = "gpt-4"
    model_endpoint_type: Optional[str] = "openai"
    model_endpoint: Optional[str] = DEFAULT_ENDPOINT
    model_wrapper: Optional[str] = None
    context_window: Optional[int] = None

    # FIXME hack to silence pydantic protected namespace warning
    model_config = ConfigDict(protected_namespaces=())


class EmbeddingConfigModel(BaseModel):
    embedding_endpoint_type: Optional[str] = "openai"
    embedding_endpoint: Optional[str] = "https://api.openai.com/v1"
    embedding_model: Optional[str] = "text-embedding-ada-002"
    embedding_dim: Optional[int] = 1536
    embedding_chunk_size: Optional[int] = 300


class HumanModel(SQLModel, table=True):
    text: str = Field(
        default=get_human_text(DEFAULT_HUMAN), description="The human text."
    )
    name: str = Field(..., description="The name of the human.")
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="The unique identifier of the human.",
        primary_key=True,
    )
    user_id: Optional[uuid.UUID] = Field(
        ..., description="The unique identifier of the user associated with the human."
    )


class PersonaModel(SQLModel, table=True):
    text: str = Field(
        default=get_persona_text(DEFAULT_PERSONA), description="The persona text."
    )
    name: str = Field(..., description="The name of the persona.")
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="The unique identifier of the persona.",
        primary_key=True,
    )
    user_id: Optional[uuid.UUID] = Field(
        ...,
        description="The unique identifier of the user associated with the persona.",
    )


class SourceModel(SQLModel, table=True):
    name: str = Field(..., description="The name of the source.")
    description: Optional[str] = Field(
        None, description="The description of the source."
    )
    user_id: uuid.UUID = Field(
        ..., description="The unique identifier of the user associated with the source."
    )
    created_at: datetime = Field(
        default_factory=get_utc_time,
        description="The unix timestamp of when the source was created.",
    )
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="The unique identifier of the source.",
        primary_key=True,
    )
    description: Optional[str] = Field(
        None, description="The description of the source."
    )
    # embedding info
    # embedding_config: EmbeddingConfigModel = Field(..., description="The embedding configuration used by the source.")
    embedding_config: Optional[EmbeddingConfigModel] = Field(
        None,
        sa_column=Column(JSON),
        description="The embedding configuration used by the passage.",
    )
    # NOTE: .metadata is a reserved attribute on SQLModel
    metadata_: Optional[dict] = Field(
        None, sa_column=Column(JSON), description="Metadata associated with the source."
    )


class ToolModel(SQLModel, table=True):
    # TODO move into database
    name: str = Field(..., description="The name of the function.")
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="The unique identifier of the function.",
        primary_key=True,
    )
    tags: List[str] = Field(sa_column=Column(JSON), description="Metadata tags.")
    source_type: Optional[str] = Field(None, description="The type of the source code.")
    source_code: Optional[str] = Field(
        ..., description="The source code of the function."
    )

    json_schema: Dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="The JSON schema of the function.",
    )

    # Needed for Column(JSON)
    class Config:
        arbitrary_types_allowed = True


class JobStatus(str, Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"


class JobModel(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="The unique identifier of the job.",
        primary_key=True,
    )
    # status: str = Field(default="created", description="The status of the job.")
    status: JobStatus = Field(
        default=JobStatus.created,
        description="The status of the job.",
        sa_column=Column(ChoiceType(JobStatus)),
    )
    created_at: datetime = Field(
        default_factory=get_utc_time,
        description="The unix timestamp of when the job was created.",
    )
    completed_at: Optional[datetime] = Field(
        None, description="The unix timestamp of when the job was completed."
    )
    user_id: uuid.UUID = Field(
        ..., description="The unique identifier of the user associated with the job."
    )
    metadata_: Optional[dict] = Field(
        {}, sa_column=Column(JSON), description="The metadata of the job."
    )
