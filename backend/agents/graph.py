import operator
from typing import Annotated, List

from groq import RateLimitError
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.core.config import settings
from backend.core.logging import llm_logger, tool_logger, stream_logger, error_logger
from backend.tools.crm_tools import all_tools

SYSTEM_PROMPT = """You are an AI assistant for pharmaceutical sales representatives using an HCP CRM system.

You have access to these tools:
- log_interaction: Use when the user describes a new meeting/visit with a Healthcare Professional.
  Pass the user's FULL, VERBATIM message as `notes`. The extraction AI will handle all parsing.
  This tool extracts: HCP name, specialty, hospital, interaction type, date, time, duration,
  products discussed, competitors, materials shared, samples distributed, sentiment, outcomes,
  follow-up date, follow-up actions, and attendees.
- edit_interaction: Use when the user wants to correct or update previously extracted data.
  Pass the full current JSON as `current_data_json` — extract it from the most recent
  assistant message that contains a JSON object (starts with '{').
  If no JSON is found in history, pass an empty JSON object '{}'.
  Pass the user's correction text as `correction`.
- search_hcp: Use when the user wants to find or look up a Healthcare Professional by name or specialty.
- meeting_summary: Use when the user asks for a summary of a meeting.
- follow_up_recommendation: Use when the user asks for follow-up recommendations or next steps.

IMPORTANT RULES:
1. Always call the most appropriate tool. Do NOT respond with plain text when a tool should be used.
2. For log_interaction, pass the user's complete, unmodified message — do not paraphrase or truncate.
3. For edit_interaction, always include the full current_data_json from the previous extraction.
4. Never ask clarifying questions — extract what you can from the user's message.
5. If the user's message describes a meeting (visited, met, called, spoke with a doctor/HCP),
   always call log_interaction regardless of how brief the notes are.
"""


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]


model = ChatGroq(
    model=settings.PRIMARY_MODEL,
    temperature=0,
    groq_api_key=settings.GROQ_API_KEY,
).bind_tools(all_tools)

fallback_model = ChatGroq(
    model=settings.SECONDARY_MODEL,
    temperature=0,
    groq_api_key=settings.GROQ_API_KEY,
).bind_tools(all_tools)

standard_tool_node = ToolNode(all_tools)

DATA_EXTRACTION_TOOLS = {
    "log_interaction",
    "edit_interaction",
    "search_hcp",
    "meeting_summary",
    "follow_up_recommendation",
}


def intent_node(state: AgentState):
    """Calls the LLM with the system prompt prepended. Falls back to secondary model on rate limit."""
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
    try:
        llm_logger.info(f"intent_node: invoking {settings.PRIMARY_MODEL} with {len(messages)} messages")
        response = model.invoke(messages)
    except RateLimitError:
        llm_logger.warning(f"intent_node: {settings.PRIMARY_MODEL} rate limited — falling back to {settings.SECONDARY_MODEL}")
        response = fallback_model.invoke(messages)
    llm_logger.info(f"intent_node: response tool_calls={bool(getattr(response, 'tool_calls', None))}")
    return {"messages": [response]}


def tool_node(state: AgentState):
    """Executes tools. For data extraction tools, returns result directly."""
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return state

    first_tool_name = last_message.tool_calls[0]["name"]
    tool_logger.info(f"tool_node: executing tool={first_tool_name}")
    tool_output_state = standard_tool_node.invoke(state)
    tool_logger.info(f"tool_node: {first_tool_name} complete")

    if first_tool_name in DATA_EXTRACTION_TOOLS:
        tool_response_content = tool_output_state["messages"][-1].content
        return {"messages": [AIMessage(content=str(tool_response_content))]}

    return tool_output_state


def router_node(state: AgentState) -> str:
    """Routes to tool_node if there are tool calls, otherwise ends."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    return "end"


def after_tool_router(state: AgentState) -> str:
    """After tool_node: if the last message is a plain AIMessage (data extraction
    tools wrap their result this way), go straight to END.  Otherwise loop back
    to intent so the LLM can process non-extraction tool results."""
    last = state["messages"][-1]
    # A plain AIMessage with no tool_calls means tool_node already produced the
    # final answer — no need to call the LLM again.
    if isinstance(last, AIMessage) and not getattr(last, "tool_calls", None):
        return "end"
    return "intent"


workflow = StateGraph(AgentState)
workflow.set_entry_point("intent")
workflow.add_node("intent", intent_node)
workflow.add_node("tool_node", tool_node)

workflow.add_conditional_edges(
    "intent",
    router_node,
    {"tool_node": "tool_node", "end": END},
)
# After tool execution: data-extraction tools → END, others → intent
workflow.add_conditional_edges(
    "tool_node",
    after_tool_router,
    {"end": END, "intent": "intent"},
)

graph = workflow.compile()
