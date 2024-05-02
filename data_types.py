import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from config import LLMConfig, EmbeddingConfig
from constants import (
    DEFAULT_HUMAN,
    DEFAULT_PERSONA,
)
from utils import get_utc_time, get_human_text, get_persona_text


class User:
    """Defines user and default configurations"""

    # TODO: make sure to encrypt/decrypt keys before storing in DB

    def __init__(
        self,
        # name: str,
        id: Optional[uuid.UUID] = None,
        default_agent=None,
        # other
        policies_accepted=False,
    ):
        if id is None:
            self.id = uuid.uuid4()
        else:
            self.id = id
        assert isinstance(self.id, uuid.UUID), f"UUID {self.id} must be a UUID type"

        self.default_agent = default_agent

        # misc
        self.policies_accepted = policies_accepted


class AgentState:
    def __init__(
        self,
        name: str,
        user_id: uuid.UUID,
        persona: str,  # the filename where the persona was originally sourced from
        human: str,  # the filename where the human was originally sourced from
        llm_config: LLMConfig,
        embedding_config: EmbeddingConfig,
        preset: str,
        # (in-context) state contains:
        # persona: str  # the current persona text
        # human: str  # the current human text
        # system: str,  # system prompt (not required if initializing with a preset)
        # functions: dict,  # schema definitions ONLY (function code linked at runtime)
        # messages: List[dict],  # in-context messages
        id: Optional[uuid.UUID] = None,
        state: Optional[dict] = None,
        created_at: Optional[datetime] = None,
    ):
        if id is None:
            self.id = uuid.uuid4()
        else:
            self.id = id
        assert isinstance(self.id, uuid.UUID), f"UUID {self.id} must be a UUID type"
        assert isinstance(user_id, uuid.UUID), f"UUID {user_id} must be a UUID type"

        # TODO(swooders) we need to handle the case where name is None here
        # in AgentConfig we autogenerate a name, not sure what the correct thing w/ DBs is, what about NounAdjective combos? Like giphy does? BoredGiraffe etc
        self.name = name
        self.user_id = user_id
        self.preset = preset
        # The INITIAL values of the persona and human
        # The values inside self.state['persona'], self.state['human'] are the CURRENT values
        self.persona = persona
        self.human = human

        self.llm_config = llm_config
        self.embedding_config = embedding_config

        self.created_at = created_at if created_at is not None else get_utc_time()

        # state
        self.state = {} if not state else state


class Source:
    def __init__(
        self,
        user_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        id: Optional[uuid.UUID] = None,
        # embedding info
        embedding_model: Optional[str] = None,
        embedding_dim: Optional[int] = None,
    ):
        if id is None:
            self.id = uuid.uuid4()
        else:
            self.id = id
        assert isinstance(self.id, uuid.UUID), f"UUID {self.id} must be a UUID type"
        assert isinstance(user_id, uuid.UUID), f"UUID {user_id} must be a UUID type"

        self.name = name
        self.user_id = user_id
        self.description = description
        self.created_at = created_at if created_at is not None else get_utc_time()

        # embedding info (optional)
        self.embedding_dim = embedding_dim
        self.embedding_model = embedding_model


class Token:
    def __init__(
        self,
        user_id: uuid.UUID,
        token: str,
        name: Optional[str] = None,
        id: Optional[uuid.UUID] = None,
    ):
        if id is None:
            self.id = uuid.uuid4()
        else:
            self.id = id
        assert isinstance(self.id, uuid.UUID), f"UUID {self.id} must be a UUID type"
        assert isinstance(user_id, uuid.UUID), f"UUID {user_id} must be a UUID type"

        self.token = token
        self.user_id = user_id
        self.name = name


class Preset(BaseModel):
    name: str = Field(..., description="The name of the preset.")
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="The unique identifier of the preset."
    )
    user_id: Optional[uuid.UUID] = Field(
        None, description="The unique identifier of the user who created the preset."
    )
    description: Optional[str] = Field(
        None, description="The description of the preset."
    )
    created_at: datetime = Field(
        default_factory=get_utc_time,
        description="The unix timestamp of when the preset was created.",
    )
    system: str = Field(..., description="The system prompt of the preset.")
    persona: str = Field(
        default=get_persona_text(DEFAULT_PERSONA),
        description="The persona of the preset.",
    )
    persona_name: Optional[str] = Field(
        None, description="The name of the persona of the preset."
    )
    human: str = Field(
        default=get_human_text(DEFAULT_HUMAN), description="The human of the preset."
    )
    human_name: Optional[str] = Field(
        None, description="The name of the human of the preset."
    )
    functions_schema: List[Dict] = Field(
        ..., description="The functions schema of the preset."
    )
    # functions: List[str] = Field(..., description="The functions of the preset.") # TODO: convert to ID
    # sources: List[str] = Field(..., description="The sources of the preset.") # TODO: convert to ID

    @staticmethod
    def clone(preset_obj: "Preset", new_name_suffix: str = None) -> "Preset":
        """
        Takes a Preset object and an optional new name suffix as input,
        creates a clone of the given Preset object with a new ID and an optional new name,
        and returns the new Preset object.
        """
        new_preset = preset_obj.model_copy()
        new_preset.id = uuid.uuid4()
        if new_name_suffix:
            new_preset.name = f"{preset_obj.name}_{new_name_suffix}"
        else:
            new_preset.name = f"{preset_obj.name}_{str(uuid.uuid4())[:8]}"
        return new_preset
