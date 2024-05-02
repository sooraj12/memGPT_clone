import os
import uuid
import sys

from constants import (
    MEMGPT_DIR,
    LLM_MAX_TOKENS,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    DEFAULT_MODEL_WRAPPER,
)
from config import MemGPTConfig, LLMConfig, EmbeddingConfig
from metadata import MetadataStore
from data_types import User
from presets.presets import add_default_presets


def create_default_user_or_exit(config: MemGPTConfig, ms: MetadataStore):
    user_id = uuid.UUID(config.anon_clientid)
    user = ms.get_user(user_id=user_id)
    if user is None:
        ms.create_user(User(id=user_id))
        user = ms.get_user(user_id=user_id)
        if user is None:
            sys.exit(1)
        else:
            return user
    else:
        return user


def configure():
    MemGPTConfig.create_config_dir()
    config = MemGPTConfig.load()

    model_endpoint = DEFAULT_ENDPOINT
    model = DEFAULT_MODEL
    model_wrapper = DEFAULT_MODEL_WRAPPER
    context_window = int(LLM_MAX_TOKENS[str(model)])

    embedding_endpoint = DEFAULT_ENDPOINT
    embedding_model = "nomic-text-embed"
    embedding_dim = 384

    archival_storage_type = "chroma"
    archival_storage_path = os.path.join(MEMGPT_DIR, "chroma")

    recall_storage_type = "postgres"
    recall_storage_uri = "postgresql://admin:admin@localhost:5432/memgpt"

    config = MemGPTConfig(
        default_llm_config=LLMConfig(
            model=model,
            model_endpoint=model_endpoint,
            model_wrapper=model_wrapper,
            context_window=context_window,
        ),
        default_embedding_config=EmbeddingConfig(
            embedding_endpoint=embedding_endpoint,
            embedding_dim=embedding_dim,
            embedding_model=embedding_model,
        ),
        # storage
        archival_storage_type=archival_storage_type,
        archival_storage_path=archival_storage_path,
        # recall storage
        recall_storage_type=recall_storage_type,
        recall_storage_uri=recall_storage_uri,
        # metadata storage (currently forced to match recall storage)
        metadata_storage_type=recall_storage_type,
        metadata_storage_uri=recall_storage_uri,
    )

    config.save()

    # create user records
    ms = MetadataStore(config)
    user_id = uuid.UUID(config.anon_clientid)
    user = User(
        id=uuid.UUID(config.anon_clientid),
    )

    if ms.get_user(user_id):
        # update user
        ms.update_user(user)
    else:
        ms.create_user(user)

    # create preset records in metadata store
    add_default_presets(user_id, ms)


def run():
    agent = None
    # load config
    if not MemGPTConfig.exists():
        configure()  # configure llm backend
        config = MemGPTConfig.load()
    else:
        config = MemGPTConfig.load()

    # read user id from config
    # ms = MetadataStore(config)
    # user = create_default_user_or_exit(config, ms)
    # human = config.human
    # persona = config.persona

    # # determine agent to use
    # agents = ms.list_agents(user_id=user.id)
    # agents = [a.name for a in agents]
    # if len(agents) > 0:
    #     pass

    # # create agent config
    # agent_state = ms.get_agent(agent_name=agent, user_id=user.id) if agent else None
    # # create agent config

    # # create new agent


if __name__ == "__main__":
    run()
