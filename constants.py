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

CORE_MEMORY_PERSONA_CHAR_LIMIT = 2000
CORE_MEMORY_HUMAN_CHAR_LIMIT = 2000
# embeddings
MAX_EMBEDDING_DIM = 4096  # maximum supported embeding size - do NOT change or else DBs will need to be reset


CLI_WARNING_PREFIX = "Warning: "

FUNCTION_PARAM_NAME_REQ_HEARTBEAT = "request_heartbeat"
FUNCTION_PARAM_TYPE_REQ_HEARTBEAT = "boolean"
FUNCTION_PARAM_DESCRIPTION_REQ_HEARTBEAT = "Request an immediate heartbeat after function execution. Set to 'true' if you want to send a follow-up message or run a follow-up function."

MAX_PAUSE_HEARTBEATS = 360  # in min
JSON_ENSURE_ASCII = False
RETRIEVAL_QUERY_DEFAULT_PAGE_SIZE = 5
JSON_LOADS_STRICT = False

MESSAGE_CHATGPT_FUNCTION_MODEL = "gpt-3.5-turbo"
MESSAGE_CHATGPT_FUNCTION_SYSTEM_MESSAGE = (
    "You are a helpful assistant. Keep your responses short and concise."
)
TOOL_CALL_ID_MAX_LEN = 29
