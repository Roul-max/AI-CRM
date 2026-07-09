import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from backend.agents.graph import graph
from backend.core.logging import stream_logger, error_logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatInput(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    current_interaction_json: Optional[str] = None


async def agent_event_stream(input_message: str, history: List[ChatMessage], current_interaction_json: Optional[str]):
    """Streams events from the LangGraph agent."""
    messages = []
    for msg in (history or []):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    # Inject current interaction JSON as a system message so the LLM
    # can reliably pass it as current_data_json to edit_interaction.
    if current_interaction_json:
        messages.append(SystemMessage(
            content=f"CURRENT INTERACTION DATA (use this as current_data_json for edit_interaction):\n{current_interaction_json}"
        ))

    messages.append(HumanMessage(content=input_message))

    input_data = {"messages": messages}
    stream_logger.info(f"stream: starting for message='{input_message[:60]}...'")

    async for event in graph.astream_events(input_data, version="v2"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        elif kind == "on_tool_start":
            stream_logger.info(f"stream: tool_start name={event['name']}")
            yield f"data: {json.dumps({'type': 'tool_start', 'name': event['name'], 'input': event['data'].get('input', {})})}\n\n"
        elif kind == "on_tool_end":
            stream_logger.info(f"stream: tool_end name={event['name']}")
            raw = event["data"].get("output")
            if hasattr(raw, "content"):
                output = raw.content
            elif raw is not None:
                output = raw
            else:
                output = None
            if output is not None:
                try:
                    json.dumps(output)
                except (TypeError, OverflowError):
                    output = str(output)
            yield f"data: {json.dumps({'type': 'tool_end', 'name': event['name'], 'output': output})}\n\n"

    stream_logger.info("stream: complete")


@router.post("/stream")
async def stream_chat(request: ChatInput):
    return StreamingResponse(
        agent_event_stream(request.message, request.history or [], request.current_interaction_json),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
