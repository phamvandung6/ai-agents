from dataclasses import dataclass

from langgraph.graph.state import CompiledStateGraph

from src.agents.bg_task_agent.bg_task_agent import bg_task_agent
from src.agents.chatbot import chatbot
from src.agents.command_agent import command_agent
from src.agents.react_agent import react_agent
from src.agents.research_assistant import research_assistant
from src.schema import AgentInfo

DEFAULT_AGENT = "research-assistant"


@dataclass
class Agent:
    description: str
    graph: CompiledStateGraph


agents: dict[str, Agent] = {
    "chatbot": Agent(description="A simple chatbot.", graph=chatbot),
    "research-assistant": Agent(
        description="A research assistant with web search and calculator.",
        graph=research_assistant,
    ),
    "command-agent": Agent(description="A command agent.", graph=command_agent),
    "bg-task-agent": Agent(description="A background task agent.", graph=bg_task_agent),
    "react-agent": Agent(
        description="A ReAct framework agent with step-by-step reasoning.",
        graph=react_agent,
    ),
}


def get_agent(agent_id: str) -> CompiledStateGraph:
    return agents[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    return [AgentInfo(key=agent_id, description=agent.description) for agent_id, agent in agents.items()]
