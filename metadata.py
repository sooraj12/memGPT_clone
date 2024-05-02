import uuid

from sqlalchemy import (
    BIGINT,
    CHAR,
    JSON,
    Boolean,
    Column,
    DateTime,
    String,
    TypeDecorator,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker

from config import MemGPTConfig, LLMConfig, EmbeddingConfig
from data_types import (
    AgentState,
    Preset,
    Source,
    Token,
    User,
)
from pydantic_models import (
    HumanModel,
    JobModel,
    PersonaModel,
    ToolModel,
)


Base = declarative_base()


# Custom UUID type
class CommonUUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        else:
            return str(value)  # Convert UUID to string for SQLite

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        else:
            return uuid.UUID(value)


class LLMConfigColumn(TypeDecorator):
    """Custom type for storing LLMConfig as JSON"""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value:
            return vars(value)
        return value

    def process_result_value(self, value, dialect):
        # print("GET VALUE", value)
        if value:
            return LLMConfig(**value)
        return value


class EmbeddingConfigColumn(TypeDecorator):
    """Custom type for storing EmbeddingConfig as JSON"""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value:
            return vars(value)
        return value

    def process_result_value(self, value, dialect):
        if value:
            return EmbeddingConfig(**value)
        return value


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    # name = Column(String, nullable=False)
    default_agent = Column(String)

    policies_accepted = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<User(id='{self.id}')>"

    def to_record(self) -> User:
        return User(
            id=self.id,
            # name=self.name
            default_agent=self.default_agent,
            policies_accepted=self.policies_accepted,
        )


class TokenModel(Base):
    """Data model for authentication tokens. One-to-many relationship with UserModel (1 User - N tokens)."""

    __tablename__ = "tokens"

    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    # each api key is tied to a user account (that it validates access for)
    user_id = Column(CommonUUID, nullable=False)
    # the api key
    token = Column(String, nullable=False)
    # extra (optional) metadata
    name = Column(String)

    def __repr__(self) -> str:
        return f"<Token(id='{self.id}', token='{self.token}', name='{self.name}')>"

    def to_record(self) -> User:
        return Token(
            id=self.id,
            user_id=self.user_id,
            token=self.token,
            name=self.name,
        )


class AgentModel(Base):
    """Defines data model for storing Passages (consisting of text, embedding)"""

    __tablename__ = "agents"
    __table_args__ = {"extend_existing": True}

    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(CommonUUID, nullable=False)
    name = Column(String, nullable=False)
    persona = Column(String)
    human = Column(String)
    preset = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # configs
    llm_config = Column(LLMConfigColumn)
    embedding_config = Column(EmbeddingConfigColumn)

    # state
    state = Column(JSON)

    def __repr__(self) -> str:
        return f"<Agent(id='{self.id}', name='{self.name}')>"

    def to_record(self) -> AgentState:
        return AgentState(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            persona=self.persona,
            human=self.human,
            preset=self.preset,
            created_at=self.created_at,
            llm_config=self.llm_config,
            embedding_config=self.embedding_config,
            state=self.state,
        )


class SourceModel(Base):
    """Defines data model for storing Passages (consisting of text, embedding)"""

    __tablename__ = "sources"
    __table_args__ = {"extend_existing": True}

    # Assuming passage_id is the primary key
    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(CommonUUID, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding_dim = Column(BIGINT)
    embedding_model = Column(String)
    description = Column(String)

    # TODO: add num passages

    def __repr__(self) -> str:
        return f"<Source(passage_id='{self.id}', name='{self.name}')>"

    def to_record(self) -> Source:
        return Source(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            created_at=self.created_at,
            embedding_dim=self.embedding_dim,
            embedding_model=self.embedding_model,
            description=self.description,
        )


class AgentSourceMappingModel(Base):
    """Stores mapping between agent -> source"""

    __tablename__ = "agent_source_mapping"

    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(CommonUUID, nullable=False)
    agent_id = Column(CommonUUID, nullable=False)
    source_id = Column(CommonUUID, nullable=False)

    def __repr__(self) -> str:
        return f"<AgentSourceMapping(user_id='{self.user_id}', agent_id='{self.agent_id}', source_id='{self.source_id}')>"


class PresetSourceMapping(Base):
    __tablename__ = "preset_source_mapping"

    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(CommonUUID, nullable=False)
    preset_id = Column(CommonUUID, nullable=False)
    source_id = Column(CommonUUID, nullable=False)

    def __repr__(self) -> str:
        return f"<PresetSourceMapping(user_id='{self.user_id}', preset_id='{self.preset_id}', source_id='{self.source_id}')>"


class PresetModel(Base):
    """Defines data model for storing Preset objects"""

    __tablename__ = "presets"
    __table_args__ = {"extend_existing": True}

    id = Column(CommonUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(CommonUUID, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    system = Column(String)
    human = Column(String)
    human_name = Column(String, nullable=False)
    persona = Column(String)
    persona_name = Column(String, nullable=False)
    preset = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    functions_schema = Column(JSON)

    def __repr__(self) -> str:
        return f"<Preset(id='{self.id}', name='{self.name}')>"

    def to_record(self) -> Preset:
        return Preset(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            description=self.description,
            system=self.system,
            human=self.human,
            persona=self.persona,
            human_name=self.human_name,
            persona_name=self.persona_name,
            preset=self.preset,
            created_at=self.created_at,
            functions_schema=self.functions_schema,
        )


class MetadataStore:
    def __init__(self, config: MemGPTConfig):
        self.uri = config.metadata_storage_uri
        self.engine = create_engine(self.uri)

        try:
            Base.metadata.create_all(
                self.engine,
                tables=[
                    UserModel.__table__,
                    AgentModel.__table__,
                    SourceModel.__table__,
                    AgentSourceMappingModel.__table__,
                    TokenModel.__table__,
                    PresetModel.__table__,
                    PresetSourceMapping.__table__,
                    HumanModel.__table__,
                    PersonaModel.__table__,
                    ToolModel.__table__,
                    JobModel.__table__,
                ],
            )
        except Exception as e:
            print(e)

        self.session_maker = sessionmaker(bind=self.engine)
