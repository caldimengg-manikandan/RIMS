import asyncio
import logging
from typing import Callable, Dict, List, Any, Awaitable

logger = logging.getLogger(__name__)

EventHandler = Callable[[Any], Awaitable[None]]

class EventBus:
    """
    A simple asynchronous in-memory Event Bus for decoupled architecture.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to event {event_type}")

    async def publish(self, event_type: str, payload: Any = None):
        if event_type not in self._subscribers:
            logger.debug(f"No subscribers for event {event_type}")
            return
        
        handlers = self._subscribers[event_type]
        logger.info(f"Publishing event {event_type} to {len(handlers)} handlers")
        
        # Fire and forget (in background tasks) to prevent blocking the publisher
        for handler in handlers:
            asyncio.create_task(self._safe_execute(handler, payload))

    async def _safe_execute(self, handler: EventHandler, payload: Any):
        try:
            await handler(payload)
        except Exception as e:
            logger.error(f"Error executing event handler {handler.__name__}: {str(e)}", exc_info=True)


# Global event bus instance
event_bus = EventBus()
