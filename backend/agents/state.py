import operator
from typing import Annotated, Sequence, TypedDict, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: Optional[str]
    extracted_data: Optional[dict]
    summary: Optional[str]
    error: Optional[str]
