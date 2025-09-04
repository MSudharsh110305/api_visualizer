import logging
from .base_collector import BaseCollector
from instrumentation import get_instrumentor

logger = logging.getLogger(__name__)

class MemoryCollector(BaseCollector):
    """
    Collector for in-process MemoryTransport events
    """
    def _fetch_events(self):
        instrumentor = get_instrumentor()
        if not instrumentor:
            return []
        
        transport = instrumentor.event_emitter.transport
        if not hasattr(transport, 'get_events'):
            return []
        
        # Get and clear the events from memory
        events = transport.get_events()
        if events:
            logger.debug(f"Fetched {len(events)} events from memory transport")
            transport.clear()
        return events
