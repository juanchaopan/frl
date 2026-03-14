from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str


class Request(TypedDict):
    content: str
    image_urls: list[str]
    image_descriptions: list[str]


class ConversationState(TypedDict):
    conversation_id: str
    long_term_memory: str
    message_history: list[Message]
    request: Request
    response: str
