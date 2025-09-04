import json
import logging
import redis
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

class RedisCollector(BaseCollector):
    """
    Collector for Redis Stream-based event transport
    """
    def __init__(self, stream_name='api_visualizer_events', redis_host='localhost', redis_port=6379, **kwargs):
        super().__init__(**kwargs)
        self.stream_name = stream_name
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.last_id = '$'  # Start reading new messages only

    def _fetch_events(self):
        events = []
        try:
            messages = self.redis_client.xread({self.stream_name: self.last_id}, block=100, count=self.batch_size)
            for _, entries in messages:
                for entry in entries:
                    self.last_id = entry[0]
                    data = entry[1].get('data')
                    if data:
                        try:
                            events.append(json.loads(data))
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in Redis stream: {data[:50]}...")
        except Exception as e:
            logger.error(f"Error reading from Redis: {e}")
        return events
