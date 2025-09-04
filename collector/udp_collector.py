import socket
import json
import logging
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

class UDPCollector(BaseCollector):
    """
    Collector for UDP-based event transport
    """
    def __init__(self, host='0.0.0.0', port=9999, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.sock = None

    def start(self):
        """Start UDP socket server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        logger.info(f"UDPCollector listening on {self.host}:{self.port}")
        super().start()

    def stop(self):
        """Stop UDP collector"""
        super().stop()
        if self.sock:
            self.sock.close()

    def _fetch_events(self):
        self.sock.settimeout(0.1)
        events = []
        try:
            while True:
                data, _ = self.sock.recvfrom(65507)
                try:
                    event = json.loads(data.decode('utf-8'))
                    events.append(event)
                except Exception as e:
                    logger.error(f"Failed to parse UDP data: {e}")
        except socket.timeout:
            pass
        return events
