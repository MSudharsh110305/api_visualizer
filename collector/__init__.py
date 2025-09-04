"""
API Visualizer Collector Module
Collects events from Instrumentation and stores them in the database
"""

from .memory_collector import MemoryCollector
from .udp_collector import UDPCollector
from .redis_collector import RedisCollector

COLLECTOR_REGISTRY = {
    'memory': MemoryCollector,
    'udp': UDPCollector,
    'redis': RedisCollector
}

def get_collector(transport_type='memory', **kwargs):
    """
    Factory function to get a collector instance
    """
    collector_cls = COLLECTOR_REGISTRY.get(transport_type)
    if not collector_cls:
        raise ValueError(f"Unsupported collector type: {transport_type}")
    
    return collector_cls(**kwargs)
