from abc import ABC, abstractmethod
from typing import Optional

from data_types import Message
from models.chat_completion_response import (
    ChatCompletionResponse,
    ChatCompletionChunkResponse,
)


class AgentChunkStreamingInterface(ABC):
    """Interfaces handle MemGPT-related events (observer pattern)

    The 'msg' args provides the scoped message, and the optional Message arg can provide additional metadata.
    """

    @abstractmethod
    def user_message(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT receives a user message"""
        raise NotImplementedError

    @abstractmethod
    def internal_monologue(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT generates some internal monologue"""
        raise NotImplementedError

    @abstractmethod
    def assistant_message(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT uses send_message"""
        raise NotImplementedError

    @abstractmethod
    def function_message(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT calls a function"""
        raise NotImplementedError

    @abstractmethod
    def process_chunk(self, chunk: ChatCompletionChunkResponse):
        """Process a streaming chunk from an OpenAI-compatible server"""
        raise NotImplementedError

    @abstractmethod
    def stream_start(self):
        """Any setup required before streaming begins"""
        raise NotImplementedError

    @abstractmethod
    def stream_end(self):
        """Any cleanup required after streaming ends"""
        raise NotImplementedError


class AgentRefreshStreamingInterface(ABC):
    """Same as the ChunkStreamingInterface, but

    The 'msg' args provides the scoped message, and the optional Message arg can provide additional metadata.
    """

    @abstractmethod
    def user_message(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT receives a user message"""
        raise NotImplementedError

    @abstractmethod
    def internal_monologue(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT generates some internal monologue"""
        raise NotImplementedError

    @abstractmethod
    def assistant_message(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT uses send_message"""
        raise NotImplementedError

    @abstractmethod
    def function_message(self, msg: str, msg_obj: Optional[Message] = None):
        """MemGPT calls a function"""
        raise NotImplementedError

    @abstractmethod
    def process_refresh(self, response: ChatCompletionResponse):
        """Process a streaming chunk from an OpenAI-compatible server"""
        raise NotImplementedError

    @abstractmethod
    def stream_start(self):
        """Any setup required before streaming begins"""
        raise NotImplementedError

    @abstractmethod
    def stream_end(self):
        """Any cleanup required after streaming ends"""
        raise NotImplementedError

    @abstractmethod
    def toggle_streaming(self, on: bool):
        """Toggle streaming on/off (off = regular CLI interface)"""
        raise NotImplementedError
