import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langsmith import Client as LangsmithClient

from src.agents import DEFAULT_AGENT, get_agent, get_all_agent_info
from src.core import settings
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
from src.service.utils import (
    convert_message_content_to_string,
    langchain_to_chat_message,
    remove_tool_calls,
)

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self, session: Any):
        self.session = session

    def get_info(self) -> ServiceMetadata:
        """Get service metadata including available agents and models."""
        models = list(settings.AVAILABLE_MODELS)
        models.sort()
        return ServiceMetadata(
            agents=get_all_agent_info(),
            models=models,
            default_agent=DEFAULT_AGENT,
            default_model=settings.DEFAULT_MODEL,
        )

    def _parse_input(self, user_input: UserInput) -> tuple[dict[str, Any], UUID]:
        """Parse user input and prepare kwargs for agent invocation."""
        run_id = uuid4()
        thread_id = user_input.thread_id or str(uuid4())

        configurable = {"thread_id": thread_id, "model": user_input.model}

        if user_input.agent_config:
            if overlap := configurable.keys() & user_input.agent_config.keys():
                raise HTTPException(
                    status_code=422,
                    detail=f"agent_config contains reserved keys: {overlap}",
                )
            configurable.update(user_input.agent_config)

        kwargs = {
            "input": {"messages": [HumanMessage(content=user_input.message)]},
            "config": RunnableConfig(
                configurable=configurable,
                run_id=run_id,
            ),
        }
        return kwargs, run_id

    async def invoke(self, user_input: UserInput, agent_id: str = DEFAULT_AGENT) -> ChatMessage:
        """Invoke an agent with user input to retrieve a final response."""
        agent: CompiledStateGraph = get_agent(agent_id)
        kwargs, run_id = self._parse_input(user_input)
        try:
            response = await agent.ainvoke(**kwargs)
            output = langchain_to_chat_message(response["messages"][-1])
            output.run_id = str(run_id)
            return output
        except Exception as e:
            logger.error(f"An exception occurred: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error")

    async def stream(
        self,
        user_input: StreamInput,
        agent_id: str = DEFAULT_AGENT,
    ) -> AsyncGenerator[str, None]:
        """Generate a stream of messages from the agent."""
        agent: CompiledStateGraph = get_agent(agent_id)
        kwargs, run_id = self._parse_input(user_input)

        async for event in agent.astream_events(**kwargs, version="v2"):
            if not event:
                continue

            new_messages = []
            if event["event"] == "on_chain_end" and any(
                t.startswith("graph:step:") for t in event.get("tags", [])
            ):
                if isinstance(event["data"]["output"], Command):
                    new_messages = event["data"]["output"].update.get("messages", [])
                elif "messages" in event["data"]["output"]:
                    new_messages = event["data"]["output"]["messages"]

            if event["event"] == "on_custom_event" and "custom_data_dispatch" in event.get(
                "tags",
                [],
            ):
                new_messages = [event["data"]]

            for message in new_messages:
                try:
                    chat_message = langchain_to_chat_message(message)
                    chat_message.run_id = str(run_id)
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
                    yield f"data: {json.dumps(
                        {
                            "type": "error",
                            "content": "Unexpected error",
                        }
                    )}\n\n"
                    continue

                if chat_message.type == "human" and chat_message.content == user_input.message:
                    continue

                yield f"data: {json.dumps(
                    {
                        "type": "message",
                        "content": chat_message.model_dump(),
                    }
                )}\n\n"

            if (
                event["event"] == "on_chat_model_stream"
                and user_input.stream_tokens
                and "llama_guard" not in event.get("tags", [])
            ):
                content = remove_tool_calls(event["data"]["chunk"].content)
                if content:
                    yield f"data: {json.dumps(
                        {
                            'type': 'token',
                            "content": convert_message_content_to_string(content),
                        }
                    )}\n\n"
                continue

        yield "data: [DONE]\n\n"

    async def create_feedback(self, feedback: Feedback) -> FeedbackResponse:
        """Create feedback in LangSmith."""
        client = LangsmithClient()
        kwargs = feedback.kwargs or {}
        client.create_feedback(
            run_id=feedback.run_id,
            key=feedback.key,
            score=feedback.score,
            **kwargs,
        )
        return FeedbackResponse()

    async def get_history(self, input: ChatHistoryInput) -> ChatHistory:
        """Get chat history."""
        agent: CompiledStateGraph = get_agent(DEFAULT_AGENT)
        try:
            state_snapshot = await agent.aget_state(
                config=RunnableConfig(
                    configurable={
                        "thread_id": input.thread_id,
                    },
                ),
            )
            messages: list[AnyMessage] = state_snapshot.values["messages"]
            chat_messages: list[ChatMessage] = [langchain_to_chat_message(m) for m in messages]
            return ChatHistory(messages=chat_messages)
        except Exception as e:
            logger.error(f"An exception occurred: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error while retrieving chat history",
            )
