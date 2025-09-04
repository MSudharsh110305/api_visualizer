"""
Event emission system for sending captured API events to collectors
Supports multiple transport mechanisms: memory queue, Redis, UDP
"""

import time
import json
import queue
import threading
import logging
import socket
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class EventEmitter:
    """
    Handles emission of instrumentation events to various transports
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.transport_type = self.config.get('transport', {}).get('type', 'memory')
        self.batch_size = self.config.get('transport', {}).get('batch_size', 100)
        self.batch_timeout = self.config.get('transport', {}).get('batch_timeout', 5.0)
        
        # Stats
        self.stats = {
            'events_emitted': 0,
            'batches_sent': 0,
            'errors': 0,
            'dropped_events': 0
        }
        
        # Internal state
        self.is_running = False
        self.event_queue = queue.Queue(maxsize=10000)
        self.batch_thread = None
        self.transport = None
        
        # Initialize transport
        self._initialize_transport()
    
    def start(self):
        """Start event emission"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start batching thread
        self.batch_thread = threading.Thread(target=self._batch_worker, daemon=True)
        self.batch_thread.start()
        
        logger.info(f"Event emitter started with {self.transport_type} transport")
    
    def stop(self):
        """Stop event emission and cleanup"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for batch thread to finish
        if self.batch_thread and self.batch_thread.is_alive():
            self.batch_thread.join(timeout=2.0)
        
        # Cleanup transport
        if self.transport and hasattr(self.transport, 'close'):
            try:
                self.transport.close()
            except Exception as e:
                logger.error(f"Error closing transport: {e}")
        
        logger.info("Event emitter stopped")
    
    def emit(self, event: Dict[str, Any]):
        """Emit a single event"""
        if not self.is_running:
            return
        
        try:
            # Add metadata
            event['emitted_at'] = time.time()
            event['event_id'] = self._generate_event_id()
            
            # Queue the event
            self.event_queue.put_nowait(event)
            self.stats['events_emitted'] += 1
            
        except queue.Full:
            self.stats['dropped_events'] += 1
            logger.warning("Event queue full, dropping event")
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to emit event: {e}")
    
    def _initialize_transport(self):
        """Initialize the configured transport"""
        if self.transport_type == 'memory':
            self.transport = MemoryTransport(self.config.get('transport', {}))
        elif self.transport_type == 'redis':
            self.transport = RedisTransport(self.config.get('transport', {}))
        elif self.transport_type == 'udp':
            self.transport = UDPTransport(self.config.get('transport', {}))
        else:
            logger.warning(f"Unknown transport type: {self.transport_type}, using memory")
            self.transport = MemoryTransport({})
    
    def _batch_worker(self):
        """Background thread that batches and sends events"""
        batch = []
        last_send_time = time.time()
        
        while self.is_running:
            try:
                # Try to get an event with timeout
                try:
                    event = self.event_queue.get(timeout=1.0)
                    batch.append(event)
                except queue.Empty:
                    # Timeout reached, send batch if not empty
                    if batch and (time.time() - last_send_time) >= self.batch_timeout:
                        self._send_batch(batch)
                        batch = []
                        last_send_time = time.time()
                    continue
                
                # Send batch if it's full or timeout reached
                if (len(batch) >= self.batch_size or 
                    (time.time() - last_send_time) >= self.batch_timeout):
                    self._send_batch(batch)
                    batch = []
                    last_send_time = time.time()
                
            except Exception as e:
                logger.error(f"Error in batch worker: {e}")
                self.stats['errors'] += 1
        
        # Send remaining events
        if batch:
            self._send_batch(batch)
    
    def _send_batch(self, batch: List[Dict[str, Any]]):
        """Send a batch of events via the configured transport"""
        if not batch:
            return
        
        try:
            self.transport.send(batch)
            self.stats['batches_sent'] += 1
            logger.debug(f"Sent batch of {len(batch)} events")
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to send batch: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return f"{int(time.time() * 1000000)}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get emission statistics"""
        return {
            **self.stats,
            'transport_type': self.transport_type,
            'queue_size': self.event_queue.qsize(),
            'is_running': self.is_running
        }

class MemoryTransport:
    """In-memory transport for testing and single-process deployment"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.events = []
        self.max_events = config.get('max_events', 10000)
    
    def send(self, batch: List[Dict[str, Any]]):
        """Store events in memory"""
        self.events.extend(batch)
        
        # Rotate if too many events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all stored events"""
        return self.events.copy()
    
    def clear(self):
        """Clear all stored events"""
        self.events.clear()

class RedisTransport:
    """Redis transport using streams"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = None
        self.stream_name = config.get('stream_name', 'api_visualizer_events')
        self.max_length = config.get('max_length', 10000)
        
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            import redis
            
            redis_config = self.config.get('redis', {})
            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                decode_responses=False
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for event transport")
            
        except ImportError:
            raise Exception("redis package not installed")
        except Exception as e:
            raise Exception(f"Failed to connect to Redis: {e}")
    
    def send(self, batch: List[Dict[str, Any]]):
        """Send events to Redis stream"""
        if not self.redis_client:
            raise Exception("Redis client not connected")
        
        try:
            pipe = self.redis_client.pipeline()
            
            for event in batch:
                # Convert to JSON string
                event_data = {'data': json.dumps(event)}
                
                # Add to stream
                pipe.xadd(
                    self.stream_name, 
                    event_data,
                    maxlen=self.max_length,
                    approximate=True
                )
            
            pipe.execute()
            
        except Exception as e:
            raise Exception(f"Failed to send events to Redis: {e}")
    
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()

class UDPTransport:
    """UDP transport for high-performance, fire-and-forget event emission"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 9999)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send(self, batch: List[Dict[str, Any]]):
        """Send events via UDP"""
        try:
            # Send each event as separate UDP packet
            for event in batch:
                data = json.dumps(event).encode('utf-8')
                
                # Split large events if needed
                if len(data) > 65507:  # Max UDP payload
                    logger.warning(f"Event too large for UDP ({len(data)} bytes), skipping")
                    continue
                
                self.socket.sendto(data, (self.host, self.port))
                
        except Exception as e:
            raise Exception(f"Failed to send events via UDP: {e}")
    
    def close(self):
        """Close UDP socket"""
        if self.socket:
            self.socket.close()
