import uuid
import os

from metadata import MetadataStore
from models.pydantic_models import PersonaModel, HumanModel
from utils import (
    list_human_files,
    list_persona_files,
    get_persona_text,
    get_human_text,
)
from constants import DEFAULT_HUMAN, DEFAULT_PERSONA
from data_types import Preset
from prompts import gpt_system
from typing import List
from functions.functions import load_all_function_sets
from presets.utils import load_all_presets

available_presets = load_all_presets()
preset_options = list(available_presets.keys())


def add_default_humans_and_personas(user_id: uuid.UUID, ms: MetadataStore):
    for persona_file in list_persona_files():
        text = open(persona_file, "r").read()
        name = os.path.basename(persona_file).replace(".txt", "")
        if ms.get_persona(user_id=user_id, name=name) is not None:
            continue
        persona = PersonaModel(name=name, text=text, user_id=user_id)
        ms.add_persona(persona)
    for human_file in list_human_files():
        text = open(human_file, "r").read()
        name = os.path.basename(human_file).replace(".txt", "")
        if ms.get_human(user_id=user_id, name=name) is not None:
            continue
        human = HumanModel(name=name, text=text, user_id=user_id)
        ms.add_human(human)


def generate_functions_json(preset_functions: List[str]):
    """
    Generate JSON schema for the functions based on what is locally available.

    TODO: store function definitions in the DB, instead of locally
    """
    # Available functions is a mapping from:
    # function_name -> {
    #   json_schema: schema
    #   python_function: function
    # }
    available_functions = load_all_function_sets()
    # Filter down the function set based on what the preset requested
    preset_function_set = {}
    for f_name in preset_functions:
        if f_name not in available_functions:
            raise ValueError(
                f"Function '{f_name}' was specified in preset, but is not in function library:\n{available_functions.keys()}"
            )
        preset_function_set[f_name] = available_functions[f_name]
    assert len(preset_functions) == len(preset_function_set)
    preset_function_set_schemas = [
        f_dict["json_schema"] for _, f_dict in preset_function_set.items()
    ]
    return preset_function_set_schemas


def load_preset(preset_name: str, user_id: uuid.UUID):
    preset_config = available_presets[preset_name]
    preset_system_prompt = preset_config["system_prompt"]
    preset_function_set_names = preset_config["functions"]
    functions_schema = generate_functions_json(preset_function_set_names)

    preset = Preset(
        user_id=user_id,
        name=preset_name,
        system=gpt_system.get_system_text(preset_system_prompt),
        persona=get_persona_text(DEFAULT_PERSONA),
        persona_name=DEFAULT_PERSONA,
        human=get_human_text(DEFAULT_HUMAN),
        human_name=DEFAULT_HUMAN,
        functions_schema=functions_schema,
    )
    return preset


def add_default_presets(user_id: uuid.UUID, ms: MetadataStore):
    """Add the default presets to the metadata store"""
    # make sure humans/personas added
    add_default_humans_and_personas(user_id=user_id, ms=ms)

    # add default presets
    for preset_name in preset_options:
        if ms.get_preset(user_id=user_id, name=preset_name) is not None:
            continue

        preset = load_preset(preset_name, user_id)
        ms.create_preset(preset)
