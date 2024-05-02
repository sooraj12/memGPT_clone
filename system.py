import json
import uuid

from utils import get_local_time
from constants import (
    JSON_ENSURE_ASCII,
    INITIAL_BOOT_MESSAGE_SEND_MESSAGE_THOUGHT,
    INITIAL_BOOT_MESSAGE_SEND_MESSAGE_FIRST_MSG,
    INITIAL_BOOT_MESSAGE,
)


def get_login_event(
    last_login="Never (first login)",
    include_location=False,
    location_name="San Francisco, CA, USA",
):
    # Package the message with time and location
    formatted_time = get_local_time()
    packaged_message = {
        "type": "login",
        "last_login": last_login,
        "time": formatted_time,
    }

    if include_location:
        packaged_message["location"] = location_name

    return json.dumps(packaged_message, ensure_ascii=JSON_ENSURE_ASCII)


def package_function_response(was_success, response_string, timestamp=None):
    formatted_time = get_local_time() if timestamp is None else timestamp
    packaged_message = {
        "status": "OK" if was_success else "Failed",
        "message": response_string,
        "time": formatted_time,
    }

    return json.dumps(packaged_message, ensure_ascii=JSON_ENSURE_ASCII)


def get_initial_boot_messages(version="startup"):
    if version == "startup":
        initial_boot_message = INITIAL_BOOT_MESSAGE
        messages = [
            {"role": "assistant", "content": initial_boot_message},
        ]

    elif version == "startup_with_send_message":
        tool_call_id = str(uuid.uuid4())
        messages = [
            # first message includes both inner monologue and function call to send_message
            {
                "role": "assistant",
                "content": INITIAL_BOOT_MESSAGE_SEND_MESSAGE_THOUGHT,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": "send_message",
                            "arguments": '{\n  "message": "'
                            + f"{INITIAL_BOOT_MESSAGE_SEND_MESSAGE_FIRST_MSG}"
                            + '"\n}',
                        },
                    }
                ],
            },
            # obligatory function return message
            {
                "role": "tool",
                "name": "send_message",
                "content": package_function_response(True, None),
                "tool_call_id": tool_call_id,
            },
        ]

    else:
        raise ValueError(version)

    return messages
