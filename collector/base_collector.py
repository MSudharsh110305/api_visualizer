import abc
import logging
import time
from storage import store_events
from storage.models import EventValidator

logger = logging.getLogger(__name__)

class BaseCollector(abc.ABC):
    """
    Abstract Base Class for all collectors
    """
    def __init__(self, batch_size=50, batch_interval=5, db_path=None):
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.db_path = db_path
        self.running = False
        self._buffer = []

    def start(self):
        """Start the collector loop"""
        logger.info(f"Starting {self.__class__.__name__}...")
        self.running = True
        try:
            self._collect_loop()
        except KeyboardInterrupt:
            logger.info("Collector stopped by user")
            self.running = False
        finally:
            self._flush_buffer()

    def stop(self):
        """Stop the collector"""
        logger.info("Stopping collector...")
        self.running = False
        self._flush_buffer()

    def _add_event_to_buffer(self, event):
        """Validate and add event to buffer"""
        valid, errors = EventValidator.validate_event(event)
        if not valid:
            logger.warning(f"Skipping invalid event: {errors}")
            return
        
        clean_event = EventValidator.sanitize_event(event)
        self._buffer.append(clean_event)

        if len(self._buffer) >= self.batch_size:
            self._flush_buffer()

    def _flush_buffer(self):
        """Write buffered events to the database"""
        if not self._buffer:
            return
        try:
            stored = store_events(self._buffer, db_path=self.db_path)
            logger.info(f"Stored {stored} events from buffer")
        except Exception as e:
            logger.error(f"Failed to store events: {e}")
        finally:
            self._buffer.clear()

    def _collect_loop(self):
        """Main loop fetching events from the source"""
        last_flush = time.time()
        while self.running:
            events = self._fetch_events()
            for event in events:
                self._add_event_to_buffer(event)

            if time.time() - last_flush >= self.batch_interval:
                self._flush_buffer()
                last_flush = time.time()
            time.sleep(0.1)

    @abc.abstractmethod
    def _fetch_events(self):
        """Fetch new events from the configured source"""
        pass
