
from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from typing import List

class ExtendedMessagesState(TypedDict):
    messages: Annotated[list, add_messages]
    news_title:str
    latest_news_url: str
    topic: str
    language:str
    duration: str
    style: str
    format: str
    bgm: bool
    speakers: List[str]
    system_prompt: str
    ai_response: str
    news_summary:str
    location:str
    podcast_duration: str
    parsed_ai_response: dict
    result_url: str
    request_to_make:str