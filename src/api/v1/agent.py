import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents import DEFAULT_AGENT
from src.api.deps import verify_token
from src.database import get_session
from src.schema import (
    ChatHistory,
    ChatHistoryInput,
    ChatMessage,
    Feedback,
    FeedbackResponse,
    ServiceMetadata,
    StreamInput,
    UserInput,
)
from src.service import AgentService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/info")
async def info(
    session: AsyncSession = Depends(get_session),
) -> ServiceMetadata:
    """Get agent info."""
    return AgentService(session).get_info()


@router.post("/{agent_id}/invoke")
@router.post("/invoke")
async def invoke(
    user_input: UserInput,
    agent_id: str = DEFAULT_AGENT,
    session: AsyncSession = Depends(get_session),
) -> ChatMessage:
    """Invoke agent."""
    return await AgentService(session).invoke(user_input, agent_id)


@router.post("/{agent_id}/stream")
@router.post("/stream")
async def stream(
    user_input: StreamInput,
    agent_id: str = DEFAULT_AGENT,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Stream agent response."""
    return StreamingResponse(
        AgentService(session).stream(user_input, agent_id),
        media_type="text/event-stream",
    )


@router.post("/feedback")
async def feedback(
    feedback_input: Feedback,
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    """Create feedback."""
    return await AgentService(session).create_feedback(feedback_input)


@router.post("/history")
async def history(
    input: ChatHistoryInput,
    session: AsyncSession = Depends(get_session),
) -> ChatHistory:
    """Get chat history."""
    return await AgentService(session).get_history(input)
