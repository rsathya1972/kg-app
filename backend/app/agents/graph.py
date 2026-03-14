"""
Lightweight LangGraph-compatible StateGraph implementation.

API mirrors langgraph.graph.StateGraph so the real langgraph package can be
swapped in later with no changes to pipeline.py:

    from app.agents.graph import StateGraph   →   from langgraph.graph import StateGraph
"""
from typing import Any, Awaitable, Callable


class CompiledGraph:
    """Compiled, executable pipeline graph."""

    def __init__(
        self,
        nodes: dict[str, Callable],
        edges: dict[str, str],
        entry: str,
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._entry = entry

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute nodes in order, threading state through each."""
        current = self._entry
        while current and current != "__end__":
            fn = self._nodes.get(current)
            if fn is None:
                break
            state = await fn(state)
            current = self._edges.get(current, "__end__")
        return state


class StateGraph:
    """
    LangGraph-compatible directed state graph builder.

    Usage:
        g = StateGraph(MyState)
        g.add_node("step_a", step_a_fn)
        g.add_node("step_b", step_b_fn)
        g.add_edge("step_a", "step_b")
        g.set_entry_point("step_a")
        graph = g.compile()
        result = await graph.ainvoke(initial_state)
    """

    def __init__(self, state_schema: Any) -> None:  # noqa: ANN401
        self._schema = state_schema
        self._nodes: dict[str, Callable[..., Awaitable]] = {}
        self._edges: dict[str, str] = {}
        self._entry: str | None = None

    def add_node(self, name: str, fn: Callable[..., Awaitable]) -> None:
        self._nodes[name] = fn

    def add_edge(self, from_node: str, to_node: str) -> None:
        self._edges[from_node] = to_node

    def set_entry_point(self, name: str) -> None:
        self._entry = name

    def compile(self) -> CompiledGraph:
        if self._entry is None:
            raise ValueError("Entry point not set — call set_entry_point() first.")
        return CompiledGraph(
            nodes=dict(self._nodes),
            edges=dict(self._edges),
            entry=self._entry,
        )
