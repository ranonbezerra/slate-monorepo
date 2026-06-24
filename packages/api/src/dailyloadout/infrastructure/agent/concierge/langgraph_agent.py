"""LangGraph + ChatOllama implementation of the Concierge agent.

Uses ``ChatOllama.bind_tools`` (via ``create_react_agent``) for the tool-calling
loop. The tool-using model defaults to ``qwen3:8b`` — Gemma is weak at
function-calling. A shared in-memory checkpointer persists conversation threads
across turns (upgrade to a Postgres saver in Epic 15).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from .base import AbstractConciergeAgent, ConciergeReply, ConciergeRequest

if TYPE_CHECKING:
    from dailyloadout.config import Settings


class LangGraphConciergeAgent(AbstractConciergeAgent):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        # Shared across turns/threads so multi-turn conversations accumulate.
        self._checkpointer = MemorySaver()

    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        model = ChatOllama(
            base_url=self._settings.ollama_base_url,
            model=self._settings.ollama_agent_model,
        )
        tools = [
            StructuredTool.from_function(
                coroutine=t.coroutine,
                name=t.name,
                description=t.description,
                args_schema=t.args_schema,
            )
            for t in req.tools
        ]
        graph = create_react_agent(
            model,
            tools,
            prompt=req.system,
            checkpointer=self._checkpointer,
        )
        config: RunnableConfig = {
            "configurable": {"thread_id": req.thread_id},
            "recursion_limit": max(4, self._settings.concierge_max_tool_loops * 2),
        }
        inputs: dict[str, Any] = {"messages": [HumanMessage(content=req.message)]}
        result: Any = await graph.ainvoke(inputs, config=config)
        final = result["messages"][-1].content
        return ConciergeReply(text=final if isinstance(final, str) else str(final))
