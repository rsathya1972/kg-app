"""
In-memory SSE event queue per run_id.
Each pipeline run gets its own asyncio.Queue; the SSE endpoint drains it.
"""
import asyncio
from typing import Any

_queues: dict[str, asyncio.Queue] = {}


def create(run_id: str) -> asyncio.Queue:
    """Create and register a new queue for a run."""
    q: asyncio.Queue = asyncio.Queue()
    _queues[run_id] = q
    return q


async def push(run_id: str, event: dict[str, Any]) -> None:
    """Push an event to the run's queue (no-op if queue doesn't exist)."""
    if q := _queues.get(run_id):
        await q.put(event)


def get(run_id: str) -> asyncio.Queue | None:
    """Return the queue for a run, or None if not active."""
    return _queues.get(run_id)


def close(run_id: str) -> None:
    """Remove the queue for a completed/failed run."""
    _queues.pop(run_id, None)
