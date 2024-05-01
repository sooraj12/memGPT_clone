import os

MEMGPT_DIR = os.path.join(".", ".memgpt")
LLM_MAX_TOKENS = {
    "llama3:70b": 8192,
}
DEFAULT_ENDPOINT = "http://localhost:11434"
DEFAULT_MODEL = "llama3:70b"
DEFAULT_MODEL_WRAPPER = "chatml"


DEFAULT_PERSONA = "sam_pov"
DEFAULT_HUMAN = "basic"
DEFAULT_PRESET = "memgpt_chat"
