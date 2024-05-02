import os

from datetime import timezone, datetime
from constants import (
    CORE_MEMORY_PERSONA_CHAR_LIMIT,
    CORE_MEMORY_HUMAN_CHAR_LIMIT,
    MEMGPT_DIR,
)


def list_human_files():
    """List all humans files"""
    defaults_dir = os.path.join(MEMGPT_DIR, "humans", "examples")
    user_dir = os.path.join(MEMGPT_DIR, "humans")

    memgpt_defaults = os.listdir(defaults_dir)
    memgpt_defaults = [
        os.path.join(defaults_dir, f) for f in memgpt_defaults if f.endswith(".txt")
    ]

    if os.path.exists(user_dir):
        user_added = os.listdir(user_dir)
        user_added = [os.path.join(user_dir, f) for f in user_added]
    else:
        user_added = []
    return memgpt_defaults + user_added


def list_persona_files():
    """List all personas files"""
    defaults_dir = os.path.join(MEMGPT_DIR, "personas", "examples")
    user_dir = os.path.join(MEMGPT_DIR, "personas")

    memgpt_defaults = os.listdir(defaults_dir)
    memgpt_defaults = [
        os.path.join(defaults_dir, f) for f in memgpt_defaults if f.endswith(".txt")
    ]

    if os.path.exists(user_dir):
        user_added = os.listdir(user_dir)
        user_added = [os.path.join(user_dir, f) for f in user_added]
    else:
        user_added = []
    return memgpt_defaults + user_added


def get_human_text(name: str, enforce_limit=True):
    for file_path in list_human_files():
        file = os.path.basename(file_path)
        if f"{name}.txt" == file or name == file:
            human_text = open(file_path, "r").read().strip()
            if enforce_limit and len(human_text) > CORE_MEMORY_HUMAN_CHAR_LIMIT:
                raise ValueError(
                    f"Contents of {name}.txt is over the character limit ({len(human_text)} > {CORE_MEMORY_HUMAN_CHAR_LIMIT})"
                )
            return human_text

    raise ValueError(f"Human {name}.txt not found")


def get_persona_text(name: str, enforce_limit=True):
    for file_path in list_persona_files():
        file = os.path.basename(file_path)
        if f"{name}.txt" == file or name == file:
            persona_text = open(file_path, "r").read().strip()
            if enforce_limit and len(persona_text) > CORE_MEMORY_PERSONA_CHAR_LIMIT:
                raise ValueError(
                    f"Contents of {name}.txt is over the character limit ({len(persona_text)} > {CORE_MEMORY_PERSONA_CHAR_LIMIT})"
                )
            return persona_text

    raise ValueError(f"Persona {name}.txt not found")


def get_utc_time() -> datetime:
    """Get the current UTC time"""
    # return datetime.now(pytz.utc)
    return datetime.now(timezone.utc)


def create_default_user_or_exit():
    pass
