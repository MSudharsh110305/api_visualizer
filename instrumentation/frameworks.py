"""
Web framework instrumentation for Flask, FastAPI, Django
Instruments incoming HTTP requests to track API endpoint performance
"""

import time
import functools
import logging
from typing import Dict, Any, List, Optional
from .utils import extract_url_info, should_instrument_url

logger = logging.getLogger(__name__)

class WebFrameworkInstrumentor:
    """
    Instruments web frameworks to capture incoming HTTP requests
    """
    
    def __init__(self, event_emitter, service_name: str, config: Dict[str, Any]):
        self.event_emitter = event_emitter
        self.service_name = service_name
        self.config = config
        self.instrumented_frameworks = []
        self.stats = {
            'incoming_requests': 0,
            'events_emitted': 0,
            'errors': 0
        }
    
    def instrument(self) -> List[str]:
        """Enable web framework instrumentation"""
        frameworks_found = []
        
        # Try instrumenting each framework
        if self._instrument_flask():
            frameworks_found.append('Flask')
        
        if self._instrument_fastapi():
            frameworks_found.append('FastAPI')
        
        if self._instrument_django():
            frameworks_found.append('Django')
        
        self.instrumented_frameworks = frameworks_found
        return frameworks_found
    
    def uninstrument(self):
        """Disable framework instrumentation"""
        # Framework instrumentation cleanup would go here
        # For now, we'll just log it since we're using middleware
        for framework in self.instrumented_frameworks:
            logger.info(f"Uninstrumenting {framework}")
        
        self.instrumented_frameworks = []
    
    def _instrument_flask(self) -> bool:
        """Instrument Flask applications"""
        try:
            import flask
            from flask import Flask, request, g
            
            # Add before/after request handlers
            def before_request():
                g.api_visualizer_start = time.time()
                g.api_visualizer_method = request.method
                g.api_visualizer_url = request.url
                g.api_visualizer_path = request.path
            
            def after_request(response):
                try:
                    if not hasattr(g, 'api_visualizer_start'):
                        return response
                    
                    end_time = time.time()
                    latency = (end_time - g.api_visualizer_start) * 1000
                    
                    # Skip health check endpoints
                    if not should_instrument_url(g.api_visualizer_path, self.config):
                        return response
                    
                    # Get request/response sizes
                    request_size = self._get_flask_request_size(request)
                    response_size = self._get_flask_response_size(response)
                    
                    # Emit event
                    self._emit_framework_event(
                        method=g.api_visualizer_method,
                        url=g.api_visualizer_url,
                        endpoint=g.api_visualizer_path,
                        status_code=response.status_code,
                        latency=latency,
                        request_size=request_size,
                        response_size=response_size,
                        start_time=g.api_visualizer_start,
                        framework='Flask'
                    )
                    
                except Exception as e:
                    logger.error(f"Flask instrumentation error: {e}")
                    self.stats['errors'] += 1
                
                return response
            
            # Try to register with current app
            try:
                from flask import current_app
                current_app.before_request(before_request)
                current_app.after_request(after_request)
                logger.info("Flask instrumentation registered with current_app")
                return True
            except:
                pass
            
            # Fallback: monkey patch Flask.__init__
            original_init = Flask.__init__
            
            def patched_init(self, *args, **kwargs):
                result = original_init(self, *args, **kwargs)
                self.before_request(before_request)
                self.after_request(after_request)
                return result
            
            Flask.__init__ = patched_init
            logger.info("Flask instrumentation registered via monkey patching")
            return True
            
        except ImportError:
            logger.debug("Flask not found, skipping instrumentation")
            return False
        except Exception as e:
            logger.error(f"Failed to instrument Flask: {e}")
            return False
    
    def _instrument_fastapi(self) -> bool:
        """Instrument FastAPI applications"""
        try:
            import fastapi
            from fastapi import FastAPI, Request, Response
            from fastapi.middleware.base import BaseHTTPMiddleware
            
            class APIVisualizerMiddleware(BaseHTTPMiddleware):
                def __init__(self, app, instrumentor):
                    super().__init__(app)
                    self.instrumentor = instrumentor
                
                async def dispatch(self, request: Request, call_next):
                    start_time = time.time()
                    
                    # Skip if URL should not be instrumented
                    if not should_instrument_url(str(request.url.path), self.instrumentor.config):
                        return await call_next(request)
                    
                    try:
                        # Get request size
                        request_size = await self._get_fastapi_request_size(request)
                        
                        # Process request
                        response = await call_next(request)
                        
                        # Calculate metrics
                        end_time = time.time()
                        latency = (end_time - start_time) * 1000
                        
                        # Get response size
                        response_size = self._get_fastapi_response_size(response)
                        
                        # Emit event
                        self.instrumentor._emit_framework_event(
                            method=request.method,
                            url=str(request.url),
                            endpoint=request.url.path,
                            status_code=response.status_code,
                            latency=latency,
                            request_size=request_size,
                            response_size=response_size,
                            start_time=start_time,
                            framework='FastAPI'
                        )
                        
                        return response
                        
                    except Exception as e:
                        end_time = time.time()
                        latency = (end_time - start_time) * 1000
                        
                        self.instrumentor._emit_framework_event(
                            method=request.method,
                            url=str(request.url),
                            endpoint=request.url.path,
                            status_code=500,
                            latency=latency,
                            request_size=0,
                            response_size=0,
                            start_time=start_time,
                            framework='FastAPI',
                            error=str(e)
                        )
                        
                        self.instrumentor.stats['errors'] += 1
                        raise
                
                async def _get_fastapi_request_size(self, request: Request) -> int:
                    try:
                        body = await request.body()
                        return len(body)
                    except:
                        return 0
                
                def _get_fastapi_response_size(self, response: Response) -> int:
                    try:
                        if hasattr(response, 'body') and response.body:
                            return len(response.body)
                        elif hasattr(response, 'headers') and 'content-length' in response.headers:
                            return int(response.headers['content-length'])
                    except:
                        pass
                    return 0
            
            # Monkey patch FastAPI.__init__ to add middleware
            original_init = FastAPI.__init__
            
            def patched_init(self, *args, **kwargs):
                result = original_init(self, *args, **kwargs)
                self.add_middleware(APIVisualizerMiddleware, instrumentor=self)
                return result
            
            FastAPI.__init__ = patched_init
            logger.info("FastAPI instrumentation registered")
            return True
            
        except ImportError:
            logger.debug("FastAPI not found, skipping instrumentation")
            return False
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
            return False
    
    def _instrument_django(self) -> bool:
        """Instrument Django applications"""
        try:
            import django
            from django.conf import settings
            from django.utils.deprecation import MiddlewareMixin
            
            class APIVisualizerMiddleware(MiddlewareMixin):
                def __init__(self, get_response):
                    self.get_response = get_response
                    self.instrumentor = None  # Will be set later
                    super().__init__(get_response)
                
                def process_request(self, request):
                    request.api_visualizer_start = time.time()
                    return None
                
                def process_response(self, request, response):
                    if not hasattr(request, 'api_visualizer_start') or not self.instrumentor:
                        return response
                    
                    try:
                        end_time = time.time()
                        latency = (end_time - request.api_visualizer_start) * 1000
                        
                        # Skip if URL should not be instrumented
                        if not should_instrument_url(request.path, self.instrumentor.config):
                            return response
                        
                        # Get sizes
                        request_size = self._get_django_request_size(request)
                        response_size = self._get_django_response_size(response)
                        
                        # Emit event
                        self.instrumentor._emit_framework_event(
                            method=request.method,
                            url=request.build_absolute_uri(),
                            endpoint=request.path,
                            status_code=response.status_code,
                            latency=latency,
                            request_size=request_size,
                            response_size=response_size,
                            start_time=request.api_visualizer_start,
                            framework='Django'
                        )
                        
                    except Exception as e:
                        logger.error(f"Django instrumentation error: {e}")
                        if self.instrumentor:
                            self.instrumentor.stats['errors'] += 1
                    
                    return response
                
                def _get_django_request_size(self, request) -> int:
                    try:
                        if hasattr(request, 'body'):
                            return len(request.body)
                        elif hasattr(request, 'META') and 'CONTENT_LENGTH' in request.META:
                            return int(request.META['CONTENT_LENGTH'])
                    except:
                        pass
                    return 0
                
                def _get_django_response_size(self, response) -> int:
                    try:
                        if hasattr(response, 'content'):
                            return len(response.content)
                        elif hasattr(response, 'get') and response.get('Content-Length'):
                            return int(response.get('Content-Length'))
                    except:
                        pass
                    return 0
            
            logger.info("Django instrumentation prepared")
            return True
            
        except ImportError:
            logger.debug("Django not found, skipping instrumentation")
            return False
        except Exception as e:
            logger.error(f"Failed to instrument Django: {e}")
            return False
    
    def _get_flask_request_size(self, request) -> int:
        """Calculate Flask request size"""
        try:
            if hasattr(request, 'data') and request.data:
                return len(request.data)
            elif hasattr(request, 'content_length') and request.content_length:
                return request.content_length
        except:
            pass
        return 0
    
    def _get_flask_response_size(self, response) -> int:
        """Calculate Flask response size"""
        try:
            if hasattr(response, 'data') and response.data:
                return len(response.data)
            elif hasattr(response, 'content_length') and response.content_length:
                return response.content_length
        except:
            pass
        return 0
    
    def _emit_framework_event(self, method: str, url: str, endpoint: str,
                            status_code: int, latency: float, request_size: int,
                            response_size: int, start_time: float, framework: str,
                            error: Optional[str] = None):
        """Emit framework event to collector"""
        try:
            url_info = extract_url_info(url)
            
            event = {
                'timestamp': start_time,
                'event_type': 'incoming_request',
                'service_name': self.service_name,
                'method': method.upper(),
                'url': url,
                'endpoint': endpoint,
                'host': url_info['host'],
                'status_code': status_code,
                'latency_ms': latency,
                'request_size': request_size,
                'response_size': response_size,
                'framework': framework,
                'error': error
            }
            
            self.event_emitter.emit(event)
            self.stats['events_emitted'] += 1
            self.stats['incoming_requests'] += 1
            
        except Exception as e:
            logger.error(f"Failed to emit framework event: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get instrumentation statistics"""
        return {
            **self.stats,
            'instrumented_frameworks': self.instrumented_frameworks
        }
