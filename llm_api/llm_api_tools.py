import requests
import uuid
import random
import time

from typing import List, Optional, Union
from models.pydantic_models import LLMConfigModel
from models.chat_completion_response import ChatCompletionResponse
from data_types import Message
from streaming_interface import (
    AgentChunkStreamingInterface,
    AgentRefreshStreamingInterface,
)
from local_llm.chat_completion_proxy import get_chat_completion
from constants import CLI_WARNING_PREFIX


def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 20,
    # List of OpenAI error codes: https://github.com/openai/openai-python/blob/17ac6779958b2b74999c634c4ea4c7b74906027a/src/openai/_client.py#L227-L250
    # 429 = rate limit
    error_codes: tuple = (429,),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):
        pass

        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)

            except requests.exceptions.HTTPError as http_err:
                # Retry on specified errors
                if http_err.response.status_code in error_codes:
                    # Increment retries
                    num_retries += 1

                    # Check if max retries has been reached
                    if num_retries > max_retries:
                        raise Exception(
                            f"Maximum number of retries ({max_retries}) exceeded."
                        )

                    # Increment the delay
                    delay *= exponential_base * (1 + jitter * random.random())

                    # Sleep for the delay
                    # printd(f"Got a rate limit error ('{http_err}') on LLM backend request, waiting {int(delay)}s then retrying...")
                    print(
                        f"{CLI_WARNING_PREFIX}Got a rate limit error ('{http_err}') on LLM backend request, waiting {int(delay)}s then retrying..."
                    )
                    time.sleep(delay)
                else:
                    # For other HTTP errors, re-raise the exception
                    raise

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper


@retry_with_exponential_backoff
def create(
    llm_config: LLMConfigModel,
    messages: List[Message],
    user_id: uuid.UUID = None,  # option UUID to associate request with
    functions: list = None,
    functions_python: list = None,
    function_call: str = "auto",
    # hint
    first_message: bool = False,
    # use tool naming?
    # if false, will use deprecated 'functions' style
    use_tool_naming: bool = True,
    # streaming?
    stream: bool = False,
    stream_inferface: Optional[
        Union[AgentRefreshStreamingInterface, AgentChunkStreamingInterface]
    ] = None,
) -> ChatCompletionResponse:
    """Return response to chat completion with backoff"""

    return get_chat_completion(
        model=llm_config.model,
        messages=messages,
        functions=functions,
        functions_python=functions_python,
        function_call=function_call,
        context_window=llm_config.context_window,
        endpoint=llm_config.model_endpoint,
        endpoint_type=llm_config.model_endpoint_type,
        wrapper=llm_config.model_wrapper,
        user=str(user_id),
        # hint
        first_message=first_message,
        # auth-related
    )
