"""
Main auto-instrumentation orchestrator
Coordinates HTTP client and web framework instrumentation
"""

import sys
import logging
from typing import Dict, Any, Optional
from .http_clients import HTTPClientInstrumentor
from .frameworks import WebFrameworkInstrumentor
from .event_emitter import EventEmitter
from .utils import get_service_name

logger = logging.getLogger(__name__)

class AutoInstrumentor:
    """
    Main instrumentation coordinator that manages all instrumentors
    """
    
    def __init__(self, service_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.service_name = service_name or get_service_name()
        self.config = config or {}
        self.is_instrumented = False
        
        # Initialize event emitter
        self.event_emitter = EventEmitter(config=self.config)
        
        # Initialize instrumentors
        self.http_instrumentor = HTTPClientInstrumentor(
            event_emitter=self.event_emitter,
            service_name=self.service_name,
            config=self.config
        )
        
        self.framework_instrumentor = WebFrameworkInstrumentor(
            event_emitter=self.event_emitter,
            service_name=self.service_name,
            config=self.config
        )
        
        logger.info(f"AutoInstrumentor initialized for service: {self.service_name}")
    
    def instrument(self):
        """Enable all instrumentation"""
        if self.is_instrumented:
            logger.warning("Already instrumented, skipping...")
            return
        
        try:
            # Start event emitter
            self.event_emitter.start()
            
            # Instrument HTTP clients
            self.http_instrumentor.instrument()
            logger.info("HTTP client instrumentation enabled")
            
            # Instrument web frameworks
            frameworks_found = self.framework_instrumentor.instrument()
            if frameworks_found:
                logger.info(f"Web framework instrumentation enabled: {frameworks_found}")
            
            self.is_instrumented = True
            logger.info("Auto-instrumentation completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to enable instrumentation: {e}")
            raise
    
    def uninstrument(self):
        """Disable all instrumentation"""
        if not self.is_instrumented:
            return
        
        try:
            # Uninstrument everything
            self.http_instrumentor.uninstrument()
            self.framework_instrumentor.uninstrument()
            self.event_emitter.stop()
            
            self.is_instrumented = False
            logger.info("Auto-instrumentation disabled")
            
        except Exception as e:
            logger.error(f"Failed to disable instrumentation: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get instrumentation statistics"""
        return {
            'service_name': self.service_name,
            'is_instrumented': self.is_instrumented,
            'http_stats': self.http_instrumentor.get_stats(),
            'framework_stats': self.framework_instrumentor.get_stats(),
            'event_stats': self.event_emitter.get_stats()
        }
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.is_instrumented:
            try:
                self.uninstrument()
            except:
                pass  # Ignore errors during cleanup
