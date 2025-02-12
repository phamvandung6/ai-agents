from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from src.agents.tools import calculator
from src.core import get_model, settings


@tool
def get_weather(city: str) -> str:
    """Use this to get weather information."""
    return f"Weather in {city}: Sunny"


# Define tools
tools = [calculator, get_weather]


def create_agent(model: BaseChatModel = None):
    """Create a prebuilt ReAct agent."""
    if model is None:
        model = get_model(settings.DEFAULT_MODEL)

    # Create the agent graph
    return create_react_agent(model, tools)


# Create the agent instance
react_agent = create_agent()
