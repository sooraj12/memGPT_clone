import uuid
import json
import datetime

from metadata import MetadataStore
from typing import Optional, Union, List, cast
from data_types import AgentState, Preset, LLMConfig, EmbeddingConfig, Message
from interface import AgentInterface
from functions.functions import load_all_function_sets
from constants import JSON_ENSURE_ASCII
from utils import get_schema_diff, is_utc_datetime, get_local_time
from constants import CORE_MEMORY_HUMAN_CHAR_LIMIT, CORE_MEMORY_PERSONA_CHAR_LIMIT
from memory import CoreMemory, ArchivalMemory, RecallMemory
from persistence_manager import LocalStateManager
from system import get_login_event, get_initial_boot_messages


def link_functions(function_schemas: list):
    """Link function definitions to list of function schemas"""

    # need to dynamically link the functions
    # the saved agent.functions will just have the schemas, but we need to
    # go through the functions library and pull the respective python functions

    # Available functions is a mapping from:
    # function_name -> {
    #   json_schema: schema
    #   python_function: function
    # }
    # agent.functions is a list of schemas (OpenAI kwarg functions style, see: https://platform.openai.com/docs/api-reference/chat/create)
    # [{'name': ..., 'description': ...}, {...}]
    available_functions = load_all_function_sets()
    linked_function_set = {}
    for f_schema in function_schemas:
        # Attempt to find the function in the existing function library
        f_name = f_schema.get("name")
        if f_name is None:
            raise ValueError(
                f"While loading agent.state.functions encountered a bad function schema object with no name:\n{f_schema}"
            )
        linked_function = available_functions.get(f_name)
        if linked_function is None:
            raise ValueError(
                f"Function '{f_name}' was specified in agent.state.functions, but is not in function library:\n{available_functions.keys()}"
            )
        # Once we find a matching function, make sure the schema is identical
        if json.dumps(f_schema, ensure_ascii=JSON_ENSURE_ASCII) != json.dumps(
            linked_function["json_schema"], ensure_ascii=JSON_ENSURE_ASCII
        ):
            # error_message = (
            #     f"Found matching function '{f_name}' from agent.state.functions inside function library, but schemas are different."
            #     + f"\n>>>agent.state.functions\n{json.dumps(f_schema, indent=2, ensure_ascii=JSON_ENSURE_ASCII)}"
            #     + f"\n>>>function library\n{json.dumps(linked_function['json_schema'], indent=2, ensure_ascii=JSON_ENSURE_ASCII)}"
            # )
            schema_diff = get_schema_diff(f_schema, linked_function["json_schema"])
            error_message = (
                f"Found matching function '{f_name}' from agent.state.functions inside function library, but schemas are different.\n"
                + "".join(schema_diff)
            )

            # NOTE to handle old configs, instead of erroring here let's just warn
            # raise ValueError(error_message)
            print(error_message)
        linked_function_set[f_name] = linked_function
    return linked_function_set


def initialize_memory(ai_notes: Union[str, None], human_notes: Union[str, None]):
    memory = CoreMemory(
        human_char_limit=CORE_MEMORY_HUMAN_CHAR_LIMIT,
        persona_char_limit=CORE_MEMORY_PERSONA_CHAR_LIMIT,
    )

    memory.edit_persona(ai_notes)
    memory.edit_human(human_notes)
    return memory


def construct_system_with_memory(
    system: str,
    memory: CoreMemory,
    memory_edit_timestamp: str,
    archival_memory: Optional[ArchivalMemory] = None,
    recall_memory: Optional[RecallMemory] = None,
    include_char_count: bool = True,
):
    full_system_message = "\n".join(
        [
            system,
            "\n",
            f"### Memory [last modified: {memory_edit_timestamp.strip()}]",
            f"{len(recall_memory) if recall_memory else 0} previous messages between you and the user are stored in recall memory (use functions to access them)",
            f"{len(archival_memory) if archival_memory else 0} total memories you created are stored in archival memory (use functions to access them)",
            "\nCore memory shown below (limited in size, additional information stored in archival / recall memory):",
            f'<persona characters="{len(memory.persona)}/{memory.persona_char_limit}">'
            if include_char_count
            else "<persona>",
            memory.persona,
            "</persona>",
            f'<human characters="{len(memory.human)}/{memory.human_char_limit}">'
            if include_char_count
            else "<human>",
            memory.human,
            "</human>",
        ]
    )
    return full_system_message


def initialize_message_sequence(
    model: str,
    system: str,
    memory: CoreMemory,
    archival_memory: Optional[ArchivalMemory] = None,
    recall_memory: Optional[RecallMemory] = None,
    memory_edit_timestamp: Optional[str] = None,
    include_initial_boot_message: bool = True,
) -> List[dict]:
    if memory_edit_timestamp is None:
        memory_edit_timestamp = get_local_time()

    full_system_message = construct_system_with_memory(
        system,
        memory,
        memory_edit_timestamp,
        archival_memory=archival_memory,
        recall_memory=recall_memory,
    )
    first_user_message = (
        get_login_event()
    )  # event letting MemGPT know the user just logged in

    if include_initial_boot_message:
        initial_boot_messages = get_initial_boot_messages("startup_with_send_message")

        messages = (
            [
                {"role": "system", "content": full_system_message},
            ]
            + initial_boot_messages
            + [
                {"role": "user", "content": first_user_message},
            ]
        )

    else:
        messages = [
            {"role": "system", "content": full_system_message},
            {"role": "user", "content": first_user_message},
        ]

    return messages


class Agent:
    def __init__(
        self,
        interface: AgentInterface,
        # agents can be created from providing agent_state
        agent_state: Optional[AgentState] = None,
        # or from providing a preset (requires preset + extra fields)
        preset: Optional[Preset] = None,
        created_by: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        llm_config: Optional[LLMConfig] = None,
        embedding_config: Optional[EmbeddingConfig] = None,
        # extras
        messages_total: Optional[int] = None,
        first_message_verify_mono: bool = True,
    ):
        if preset is not None:
            pass

        elif agent_state is not None:
            init_agent_state = agent_state

        else:
            raise ValueError(
                "Both Preset and AgentState were null (must provide one or the other)"
            )

        self.agent_state = init_agent_state
        self.model = self.agent_state.llm_config.model
        self.system = self.agent_state.state["system"]
        self.functions = self.agent_state.state["functions"]
        self.functions_python = {
            k: v["python_function"]
            for k, v in link_functions(function_schemas=self.functions).items()
        }
        self.memory = initialize_memory(
            ai_notes=self.agent_state.state["persona"],
            human_notes=self.agent_state.state["human"],
        )
        self.interface = interface

        self.persistence_manager = LocalStateManager(agent_state=self.agent_state)

        self.pause_heartbeats_start = None
        self.pause_heartbeats_minutes = 0

        self.first_message_verify_mono = first_message_verify_mono

        self.agent_alerted_about_memory_pressure = False

        self._messages: List[Message] = []

        if (
            "messages" in self.agent_state.state
            and self.agent_state.state["messages"] is not None
        ):
            # Convert to IDs, and pull from the database
            raw_messages = [
                self.persistence_manager.recall_memory.storage.get(id=uuid.UUID(msg_id))
                for msg_id in self.agent_state.state["messages"]
            ]
            self._messages.extend(
                [cast(Message, msg) for msg in raw_messages if msg is not None]
            )

            for m in self._messages:
                # assert is_utc_datetime(m.created_at), f"created_at on message for agent {self.agent_state.name} isn't UTC:\n{vars(m)}"
                # TODO eventually do casting via an edit_message function
                if not is_utc_datetime(m.created_at):
                    print(
                        f"Warning - created_at on message for agent {self.agent_state.name} isn't UTC (text='{m.text}')"
                    )
                    m.created_at = m.created_at.replace(tzinfo=datetime.timezone.utc)

        else:
            init_messages = initialize_message_sequence(
                self.model,
                self.system,
                self.memory,
            )
            init_messages_objs = []
            for msg in init_messages:
                init_messages_objs.append(
                    Message.dict_to_message(
                        agent_id=self.agent_state.id,
                        user_id=self.agent_state.user_id,
                        model=self.model,
                        openai_message_dict=msg,
                    )
                )
            self.messages_total = 0
            self._append_to_messages(
                added_messages=[
                    cast(Message, msg) for msg in init_messages_objs if msg is not None
                ]
            )

            for m in self._messages:
                if not is_utc_datetime(m.created_at):
                    print(
                        f"Warning - created_at on message for agent {self.agent_state.name} isn't UTC (text='{m.text}')"
                    )
                    m.created_at = m.created_at.replace(tzinfo=datetime.timezone.utc)

        self.messages_total = (
            messages_total if messages_total is not None else (len(self._messages) - 1)
        )
        # self.messages_total_init = self.messages_total
        self.messages_total_init = len(self._messages) - 1

        print(f"Agent initialized, self.messages_total={self.messages_total}")

        self.update_state()

    def update_state(self) -> AgentState:
        updated_state = {
            "persona": self.memory.persona,
            "human": self.memory.human,
            "system": self.system,
            "functions": self.functions,
            "messages": [str(msg.id) for msg in self._messages],
        }

        self.agent_state = AgentState(
            name=self.agent_state.name,
            user_id=self.agent_state.user_id,
            persona=self.agent_state.persona,
            human=self.agent_state.human,
            llm_config=self.agent_state.llm_config,
            embedding_config=self.agent_state.embedding_config,
            preset=self.agent_state.preset,
            id=self.agent_state.id,
            created_at=self.agent_state.created_at,
            state=updated_state,
        )
        return self.agent_state


def save_agent(agent: Agent, ms: MetadataStore):
    """Save agent to metadata store"""

    agent.update_state()
    agent_state = agent.agent_state

    if ms.get_agent(agent_name=agent_state.name, user_id=agent_state.user_id):
        ms.update_agent(agent_state)
    else:
        ms.create_agent(agent_state)
