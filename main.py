import os
import uuid
import sys
import questionary
import requests
import typer
import json

from constants import (
    MEMGPT_DIR,
    LLM_MAX_TOKENS,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    DEFAULT_MODEL_WRAPPER,
    FUNC_FAILED_HEARTBEAT_MESSAGE,
    REQ_HEARTBEAT_MESSAGE,
    JSON_ENSURE_ASCII,
    JSON_LOADS_STRICT,
)
from config import MemGPTConfig, LLMConfig, EmbeddingConfig
from metadata import MetadataStore
from data_types import User
from presets.presets import add_default_presets
from agent import Agent, save_agent
from streaming_interface import (
    StreamingRefreshCLIInterface as interface,  # for printing to terminal
    AgentRefreshStreamingInterface,
)

from rich.console import Console
from errors import LLMError
from system import get_heartbeat, get_token_limit_warning, package_user_message


USER_COMMANDS = [
    ("//", "toggle multiline input mode"),
    ("/exit", "exit the CLI"),
    ("/save", "save a checkpoint of the current agent/conversation state"),
    ("/dump <count>", "view the last <count> messages (all if <count> is omitted)"),
    ("/memory", "print the current contents of agent memory"),
    ("/pop <count>", "undo <count> messages in the conversation (default is 3)"),
    ("/retry", "pops the last answer and tries to get another one"),
    ("/rethink <text>", "changes the inner thoughts of the last agent message"),
    ("/rewrite <text>", "changes the reply of the last agent message"),
    ("/heartbeat", "send a heartbeat system message to the agent"),
    ("/memorywarning", "send a memory warning system message to the agent"),
]


def clear_line(console, strip_ui=False):
    if strip_ui:
        return
    if os.name == "nt":  # for windows
        console.print("\033[A\033[K", end="")
    else:  # for linux
        sys.stdout.write("\033[2K\033[G")
        sys.stdout.flush()


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
    recall_storage_uri = "postgresql+pg8000://admin:admin@localhost:5432/memgpt"

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


def run_agent_loop(
    memgpt_agent: Agent,
    config: MemGPTConfig,
    first,
    ms: MetadataStore,
    no_verify=False,
    strip_ui=False,
    stream=False,
):
    if isinstance(memgpt_agent.interface, AgentRefreshStreamingInterface):
        # memgpt_agent.interface.toggle_streaming(on=stream)
        if not stream:
            memgpt_agent.interface = memgpt_agent.interface.nonstreaming_interface

    if hasattr(memgpt_agent.interface, "console"):
        console = memgpt_agent.interface.console
    else:
        console = Console()

    counter = 0
    user_input = None
    skip_next_user_input = False
    user_message = None
    USER_GOES_FIRST = first

    if not USER_GOES_FIRST:
        console.input(
            "[bold cyan]Hit enter to begin (will request first MemGPT message)[/bold cyan]\n"
        )
        clear_line(console, strip_ui=strip_ui)
        print()

    multiline_input = False
    ms = MetadataStore(config)
    while True:
        if not skip_next_user_input and (counter > 0 or USER_GOES_FIRST):
            # Ask for user input
            if not stream:
                print()
            user_input = questionary.text(
                "Enter your message:",
                multiline=multiline_input,
                qmark=">",
            ).ask()
            clear_line(console, strip_ui=strip_ui)
            if not stream:
                print()

            # Gracefully exit on Ctrl-C/D
            if user_input is None:
                user_input = "/exit"

            user_input = user_input.rstrip()

            if user_input.startswith("!"):
                print("Commands for CLI begin with '/' not '!'")
                continue

            if user_input == "":
                # no empty messages allowed
                print("Empty input received. Try again!")
                continue

            # Handle CLI commands
            # Commands to not get passed as input to MemGPT
            if user_input.startswith("/"):
                # updated agent save functions
                if user_input.lower() == "/exit":
                    save_agent(memgpt_agent, ms)
                    break
                elif user_input.lower() == "/save" or user_input.lower() == "/savechat":
                    save_agent(memgpt_agent, ms)
                    continue
                elif user_input.lower() == "/dump" or user_input.lower().startswith(
                    "/dump "
                ):
                    # Check if there's an additional argument that's an integer
                    command = user_input.strip().split()
                    amount = (
                        int(command[1])
                        if len(command) > 1 and command[1].isdigit()
                        else 0
                    )
                    if amount == 0:
                        memgpt_agent.interface.print_messages(
                            memgpt_agent._messages, dump=True
                        )
                    else:
                        memgpt_agent.interface.print_messages(
                            memgpt_agent._messages[
                                -min(amount, len(memgpt_agent.messages)) :
                            ],
                            dump=True,
                        )
                    continue

                elif user_input.lower() == "/memory":
                    print("\nDumping memory contents:\n")
                    print(f"{str(memgpt_agent.memory)}")
                    print(f"{str(memgpt_agent.persistence_manager.archival_memory)}")
                    print(f"{str(memgpt_agent.persistence_manager.recall_memory)}")
                    continue

                elif user_input.lower() == "/pop" or user_input.lower().startswith(
                    "/pop "
                ):
                    # Check if there's an additional argument that's an integer
                    command = user_input.strip().split()
                    pop_amount = (
                        int(command[1])
                        if len(command) > 1 and command[1].isdigit()
                        else 3
                    )
                    n_messages = len(memgpt_agent.messages)
                    MIN_MESSAGES = 2
                    if n_messages <= MIN_MESSAGES:
                        print(
                            f"Agent only has {n_messages} messages in stack, none left to pop"
                        )
                    elif n_messages - pop_amount < MIN_MESSAGES:
                        print(
                            f"Agent only has {n_messages} messages in stack, cannot pop more than {n_messages - MIN_MESSAGES}"
                        )
                    else:
                        print(f"Popping last {pop_amount} messages from stack")
                        for _ in range(min(pop_amount, len(memgpt_agent.messages))):
                            memgpt_agent.messages.pop()
                    continue

                elif user_input.lower() == "/retry":
                    print("Retrying for another answer")
                    while len(memgpt_agent.messages) > 0:
                        if memgpt_agent.messages[-1].get("role") == "user":
                            user_message = memgpt_agent.messages[-1].get("content")
                            memgpt_agent.messages.pop()
                            break
                        memgpt_agent.messages.pop()

                elif user_input.lower() == "/rethink" or user_input.lower().startswith(
                    "/rethink "
                ):
                    # TODO this needs to also modify the persistence manager
                    if len(user_input) < len("/rethink "):
                        print("Missing text after the command")
                        continue
                    for x in range(len(memgpt_agent.messages) - 1, 0, -1):
                        if memgpt_agent.messages[x].get("role") == "assistant":
                            text = user_input[len("/rethink ") :].strip()
                            memgpt_agent.messages[x].update({"content": text})
                            break
                    continue

                elif user_input.lower() == "/rewrite" or user_input.lower().startswith(
                    "/rewrite "
                ):
                    # TODO this needs to also modify the persistence manager
                    if len(user_input) < len("/rewrite "):
                        print("Missing text after the command")
                        continue
                    for x in range(len(memgpt_agent.messages) - 1, 0, -1):
                        if memgpt_agent.messages[x].get("role") == "assistant":
                            text = user_input[len("/rewrite ") :].strip()
                            # Get the current message content
                            # The rewrite target is the output of send_message
                            message_obj = memgpt_agent._messages[x]
                            if (
                                message_obj.tool_calls is not None
                                and len(message_obj.tool_calls) > 0
                            ):
                                # Check that we hit an assistant send_message call
                                name_string = message_obj.tool_calls[0].function.get(
                                    "name"
                                )
                                if name_string is None or name_string != "send_message":
                                    print(
                                        "Assistant missing send_message function call"
                                    )
                                    break  # cancel op
                                args_string = message_obj.tool_calls[0].function.get(
                                    "arguments"
                                )
                                if args_string is None:
                                    print(
                                        "Assistant missing send_message function arguments"
                                    )
                                    break  # cancel op
                                args_json = json.loads(
                                    args_string, strict=JSON_LOADS_STRICT
                                )
                                if "message" not in args_json:
                                    print(
                                        "Assistant missing send_message message argument"
                                    )
                                    break  # cancel op

                                # Once we found our target, rewrite it
                                args_json["message"] = text
                                new_args_string = json.dumps(
                                    args_json, ensure_ascii=JSON_ENSURE_ASCII
                                )
                                message_obj.tool_calls[0].function["arguments"] = (
                                    new_args_string
                                )

                                # To persist to the database, all we need to do is "re-insert" into recall memory
                                memgpt_agent.persistence_manager.recall_memory.storage.update(
                                    record=message_obj
                                )
                                break
                    continue

                elif user_input.lower() == "/summarize":
                    try:
                        memgpt_agent.summarize_messages_inplace()
                        typer.secho(
                            "/summarize succeeded",
                            fg=typer.colors.GREEN,
                            bold=True,
                        )
                    except (LLMError, requests.exceptions.HTTPError) as e:
                        typer.secho(
                            f"/summarize failed:\n{e}",
                            fg=typer.colors.RED,
                            bold=True,
                        )
                    continue

                elif user_input.lower() == "/heartbeat":
                    user_message = get_heartbeat()

                elif user_input.lower() == "/memorywarning":
                    user_message = get_token_limit_warning()

                elif user_input.lower() == "//":
                    multiline_input = not multiline_input
                    continue

                elif user_input.lower() == "/" or user_input.lower() == "/help":
                    questionary.print("CLI commands", "bold")
                    for cmd, desc in USER_COMMANDS:
                        questionary.print(cmd, "bold")
                        questionary.print(f" {desc}")
                    continue

                else:
                    print(f"Unrecognized command: {user_input}")
                    continue

            else:
                # If message did not begin with command prefix, pass inputs to MemGPT
                # Handle user message and append to messages
                user_message = package_user_message(user_input)

        skip_next_user_input = False

        def process_agent_step(user_message, no_verify):
            (
                new_messages,
                heartbeat_request,
                function_failed,
                token_warning,
            ) = memgpt_agent.step(
                user_message,
                first_message=False,
                skip_verify=no_verify,
                stream=stream,
            )

            skip_next_user_input = False
            if token_warning:
                user_message = get_token_limit_warning()
                skip_next_user_input = True
            elif function_failed:
                user_message = get_heartbeat(FUNC_FAILED_HEARTBEAT_MESSAGE)
                skip_next_user_input = True
            elif heartbeat_request:
                user_message = get_heartbeat(REQ_HEARTBEAT_MESSAGE)
                skip_next_user_input = True

            return new_messages, user_message, skip_next_user_input

        while True:
            try:
                if strip_ui:
                    new_messages, user_message, skip_next_user_input = (
                        process_agent_step(user_message, no_verify)
                    )
                    break
                else:
                    if stream:
                        # Don't display the "Thinking..." if streaming
                        new_messages, user_message, skip_next_user_input = (
                            process_agent_step(user_message, no_verify)
                        )
                    break
            except KeyboardInterrupt:
                print("User interrupt occurred.")
                retry = questionary.confirm("Retry agent.step()?").ask()
                if not retry:
                    break
            except Exception as e:
                print("An exception occurred when running agent.step(): ")
                retry = questionary.confirm("Retry agent.step()?").ask()
                if not retry:
                    break

        counter += 1

    print("Finished.")


def run():
    agent = "Memgpt_agent"
    # load config
    if not MemGPTConfig.exists():
        configure()  # configure llm backend
        config = MemGPTConfig.load()
    else:
        config = MemGPTConfig.load()

    # read user id from config
    ms = MetadataStore(config)
    user = create_default_user_or_exit(config, ms)

    # determine agent to use
    agents = ms.list_agents(user_id=user.id)
    agents = [a.name for a in agents]
    if len(agents) > 0:
        pass

    agent_state = ms.get_agent(agent_name=agent, user_id=user.id) if agent else None
    if agent and agent_state:  # use existing agent
        pass

    else:  # create new agent
        agent_name = agent
        llm_config = config.default_llm_config
        embedding_config = config.default_embedding_config
        preset_obj = ms.get_preset(name=config.preset, user_id=user.id)

        memgpt_agent = Agent(
            interface=interface(),
            name=agent_name,
            created_by=user.id,
            preset=preset_obj,
            llm_config=llm_config,
            embedding_config=embedding_config,
            first_message_verify_mono=False,
        )

        save_agent(agent=memgpt_agent, ms=ms)

    print()  # extra space

    # run agent loop
    run_agent_loop(
        memgpt_agent=memgpt_agent,
        config=config,
        first=False,
        ms=ms,
        no_verify=False,
        stream=True,
    )


if __name__ == "__main__":
    run()
