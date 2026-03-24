from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    CampusAgent의 LangGraph 전체 상태(State) 정의
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_context: dict
    tool_calls_count: int
