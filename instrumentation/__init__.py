"""
API Visualizer Instrumentation Module
Provides automatic instrumentation for HTTP clients and web frameworks
"""

from .auto_instrumentor import AutoInstrumentor
from .event_emitter import EventEmitter
from .http_clients import HTTPClientInstrumentor
from .frameworks import WebFrameworkInstrumentor
from .utils import get_service_name, should_instrument_url

# Global instrumentor instance
_instrumentor = None

def instrument_all(service_name=None, config=None):
    """
    Main entry point for instrumentation
    
    Args:
        service_name (str): Name of the service being instrumented
        config (dict): Configuration options
    """
    global _instrumentor
    
    if _instrumentor is None:
        _instrumentor = AutoInstrumentor(service_name=service_name, config=config)
        _instrumentor.instrument()
    
    return _instrumentor

def uninstrument_all():
    """Disable all instrumentation"""
    global _instrumentor
    
    if _instrumentor:
        _instrumentor.uninstrument()
        _instrumentor = None

def get_instrumentor():
    """Get the current instrumentor instance"""
    return _instrumentor

__all__ = [
    'instrument_all',
    'uninstrument_all', 
    'get_instrumentor',
    'AutoInstrumentor',
    'EventEmitter',
    'HTTPClientInstrumentor',
    'WebFrameworkInstrumentor'
]
