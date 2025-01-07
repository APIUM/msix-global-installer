import attr
import abc
import asyncio
import enum
import time
import logging
from dataclasses import dataclass
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EventType(str, enum.Enum):
    MSIX_METADATA_RECEIVED = "msix-metadata-received"
    REQUEST_MSIX_METADATA = "request-msix-metadata"


@attr.s(frozen=True)
class Event:
    """Generic event type"""

    name: str = attr.ib()
    data: Dict[str, Any] = attr.ib(kw_only=True, factory=dict)


class EventData(asyncio.Event):
    """Generic event data to be filled by the event recipient."""

    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        super().__init__()

    def set_result(self, result: Any) -> None:
        self.data = result
        self.set()

    async def get_result(self) -> Any:
        await self.wait()
        return self.data


event_queue = asyncio.Queue()  # type: asyncio.Queue[Event]


class EventHandler(abc.ABC):
    """Event handler interface class."""

    @abc.abstractmethod
    async def handle_event(self, event: Event):  # type: ignore
        """Consume an event.

        The event shall be passed down to child EventHandlers for processing.
        """
        pass


async def post_event(event: Event) -> None:
    """Post an event to the queue."""
    logger.debug("Posting event: %s", str(event))
    await event_queue.put(event)


async def wait_for_queue(timeout_s: int) -> None:
    """Wait for the event queue to be empty."""
    initial_time = time.monotonic_ns()
    timeout_ns = timeout_s * int(1e9)
    while True:
        current_time = time.monotonic_ns()
        await asyncio.sleep(0)
        if current_time - initial_time > timeout_ns:
            raise TimeoutError(f"Timed out waiting for event queue to clear. Events: {str(event_queue)}")
        elif event_queue.empty():
            break


async def receive_event() -> Event:
    """Receive an event from the event queue.

    This function will wait indefinitely on an empty queue until an event is available.
    """
    return await event_queue.get()
