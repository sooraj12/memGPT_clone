from local_llm.llm_chat_completion_wrappers.chatml import ChatMLInnerMonologueWrapper

INNER_THOUGHTS_KWARG = "inner_thoughts"
INNER_THOUGHTS_KWARG_DESCRIPTION = "Deep inner monologue private to you only."

DEFAULT_WRAPPER = ChatMLInnerMonologueWrapper
DEFAULT_WRAPPER_NAME = "chatml"
