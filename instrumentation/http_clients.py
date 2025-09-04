"""
HTTP client instrumentation for requests, httpx, aiohttp
Uses monkey patching to wrap HTTP methods - CORRECTED VERSION
"""

import time
import functools
import logging
import sys
from typing import Dict, Any, Optional, Callable
from .utils import should_instrument_url, extract_url_info, get_caller_info

logger = logging.getLogger(__name__)

class HTTPClientInstrumentor:
    """
    Instruments popular HTTP client libraries using monkey patching
    """
    
    def __init__(self, event_emitter, service_name: str, config: Dict[str, Any]):
        self.event_emitter = event_emitter
        self.service_name = service_name
        self.config = config
        self.original_methods = {}
        self.stats = {
            'requests_instrumented': 0,
            'events_emitted': 0,
            'errors': 0
        }
    
    def instrument(self):
        """Enable HTTP client instrumentation"""
        self._instrument_requests()
        self._instrument_httpx()
        self._instrument_aiohttp()
    
    def uninstrument(self):
        """Restore original HTTP client methods"""
        # Check if Python is shutting down
        if sys.meta_path is None:
            return
            
        for module_method, original in self.original_methods.items():
            module, method = module_method.rsplit('.', 1)
            try:
                import importlib
                mod = importlib.import_module(module)
                setattr(mod, method, original)
                logger.debug(f"Restored {module_method}")
            except Exception as e:
                logger.debug(f"Failed to restore {module_method}: {e}")
    
    def _instrument_requests(self):
        """Instrument requests library"""
        try:
            import requests
            
            # Store originals
            self.original_methods['requests.request'] = requests.request
            self.original_methods['requests.Session.request'] = requests.Session.request
            
            # Patch requests.request
            requests.request = self._wrap_requests_function(requests.request)
            
            # Patch Session.request - CORRECTED VERSION
            original_session_request = requests.Session.request
            def wrapped_session_request(session_self, method, url, **kwargs):
                return self._wrap_session_request(original_session_request)(session_self, method, url, **kwargs)
            requests.Session.request = wrapped_session_request
            
            logger.info("requests library instrumented successfully")
            
        except ImportError:
            logger.debug("requests library not found, skipping instrumentation")
        except Exception as e:
            logger.error(f"Failed to instrument requests: {e}")
    
    def _instrument_httpx(self):
        """Instrument httpx library"""
        try:
            import httpx
            
            # Store originals
            self.original_methods['httpx.Client.request'] = httpx.Client.request
            if hasattr(httpx, 'AsyncClient'):
                self.original_methods['httpx.AsyncClient.request'] = httpx.AsyncClient.request
            
            # Patch sync client
            original_sync_request = httpx.Client.request
            def wrapped_sync_request(client_self, method, url, **kwargs):
                return self._wrap_httpx_sync_method(original_sync_request)(client_self, method, url, **kwargs)
            httpx.Client.request = wrapped_sync_request
            
            # Patch async client
            if hasattr(httpx, 'AsyncClient'):
                original_async_request = httpx.AsyncClient.request
                def wrapped_async_request(client_self, method, url, **kwargs):
                    return self._wrap_httpx_async_method(original_async_request)(client_self, method, url, **kwargs)
                httpx.AsyncClient.request = wrapped_async_request
            
            logger.info("httpx library instrumented successfully")
            
        except ImportError:
            logger.debug("httpx library not found, skipping instrumentation")
        except Exception as e:
            logger.error(f"Failed to instrument httpx: {e}")
    
    def _instrument_aiohttp(self):
        """Instrument aiohttp library"""
        try:
            import aiohttp
            
            # Store original
            self.original_methods['aiohttp.ClientSession._request'] = aiohttp.ClientSession._request
            
            # Patch aiohttp
            original_request = aiohttp.ClientSession._request
            aiohttp.ClientSession._request = self._wrap_aiohttp_method(original_request)
            
            logger.info("aiohttp library instrumented successfully")
            
        except ImportError:
            logger.debug("aiohttp library not found, skipping instrumentation")
        except Exception as e:
            logger.error(f"Failed to instrument aiohttp: {e}")
    
    def _wrap_requests_function(self, original_function: Callable) -> Callable:
        """Wrap requests.request() function"""
        @functools.wraps(original_function)
        def wrapped(method, url, **kwargs):
            # Validate inputs
            method = str(method).upper() if method else 'GET'
            url = str(url) if url else ''
            
            # Check if we should instrument this URL
            if not should_instrument_url(url, self.config):
                return original_function(method, url, **kwargs)
            
            return self._execute_instrumented_request(
                original_function, method, url, kwargs
            )
        
        return wrapped
    
    def _wrap_session_request(self, original_method: Callable) -> Callable:
        """Wrap requests.Session.request() method"""
        @functools.wraps(original_method)
        def wrapped(session_self, method, url, **kwargs):
            # Validate inputs
            method = str(method).upper() if method else 'GET'
            url = str(url) if url else ''
            
            # Check if we should instrument this URL
            if not should_instrument_url(url, self.config):
                return original_method(session_self, method, url, **kwargs)
            
            return self._execute_instrumented_request(
                lambda m, u, **kw: original_method(session_self, m, u, **kw),
                method, url, kwargs
            )
        
        return wrapped
    
    def _wrap_httpx_sync_method(self, original_method: Callable) -> Callable:
        """Wrap httpx sync method with instrumentation"""
        @functools.wraps(original_method)
        def wrapped(client_self, method, url, **kwargs):
            method = str(method).upper() if method else 'GET'
            url = str(url) if url else ''
            
            if not should_instrument_url(url, self.config):
                return original_method(client_self, method, url, **kwargs)
            
            return self._execute_instrumented_request(
                lambda m, u, **kw: original_method(client_self, m, u, **kw),
                method, url, kwargs
            )
        
        return wrapped
    
    def _wrap_httpx_async_method(self, original_method: Callable) -> Callable:
        """Wrap httpx async method with instrumentation"""
        @functools.wraps(original_method)
        async def wrapped(client_self, method, url, **kwargs):
            method = str(method).upper() if method else 'GET'
            url = str(url) if url else ''
            
            if not should_instrument_url(url, self.config):
                return await original_method(client_self, method, url, **kwargs)
            
            return await self._execute_instrumented_async_request(
                lambda m, u, **kw: original_method(client_self, m, u, **kw),
                method, url, kwargs
            )
        
        return wrapped
    
    def _wrap_aiohttp_method(self, original_method: Callable) -> Callable:
        """Wrap aiohttp method with instrumentation"""
        @functools.wraps(original_method)
        async def wrapped(session_self, method, url, **kwargs):
            method = str(method).upper() if method else 'GET'
            url = str(url) if url else ''
            
            if not should_instrument_url(url, self.config):
                return await original_method(session_self, method, url, **kwargs)
            
            return await self._execute_instrumented_aiohttp_request(
                lambda m, u, **kw: original_method(session_self, m, u, **kw),
                method, url, kwargs
            )
        
        return wrapped
    
    def _execute_instrumented_request(self, request_func, method: str, url: str, kwargs: dict):
        """Execute an instrumented HTTP request (sync version)"""
        start_time = time.time()
        request_size = self._get_request_size(kwargs)
        
        try:
            # Make the actual request
            response = request_func(method, url, **kwargs)
            
            # Calculate metrics
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to ms
            
            # Extract response info
            status_code = getattr(response, 'status_code', 0)
            response_size = self._get_response_size(response)
            
            # Emit event
            self._emit_http_event(
                method=method,
                url=url,
                status_code=status_code,
                latency=latency,
                request_size=request_size,
                response_size=response_size,
                start_time=start_time
            )
            
            return response
            
        except Exception as e:
            # Handle errors
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            self._emit_http_event(
                method=method,
                url=url,
                status_code=0,
                latency=latency,
                request_size=request_size,
                response_size=0,
                start_time=start_time,
                error=str(e)
            )
            
            self.stats['errors'] += 1
            raise
    
    async def _execute_instrumented_async_request(self, request_func, method: str, url: str, kwargs: dict):
        """Execute an instrumented HTTP request (async version)"""
        start_time = time.time()
        request_size = self._get_request_size(kwargs)
        
        try:
            response = await request_func(method, url, **kwargs)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            status_code = getattr(response, 'status_code', 0)
            response_size = self._get_response_size(response)
            
            self._emit_http_event(
                method=method,
                url=url,
                status_code=status_code,
                latency=latency,
                request_size=request_size,
                response_size=response_size,
                start_time=start_time
            )
            
            return response
            
        except Exception as e:
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            self._emit_http_event(
                method=method,
                url=url,
                status_code=0,
                latency=latency,
                request_size=request_size,
                response_size=0,
                start_time=start_time,
                error=str(e)
            )
            
            self.stats['errors'] += 1
            raise
    
    async def _execute_instrumented_aiohttp_request(self, request_func, method: str, url: str, kwargs: dict):
        """Execute an instrumented aiohttp request"""
        start_time = time.time()
        request_size = self._get_request_size(kwargs)
        
        try:
            response = await request_func(method, url, **kwargs)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            # For aiohttp, status is different
            status_code = getattr(response, 'status', 0)
            
            # Get response size from headers
            response_size = 0
            if hasattr(response, 'headers') and 'content-length' in response.headers:
                try:
                    response_size = int(response.headers['content-length'])
                except:
                    pass
            
            self._emit_http_event(
                method=method,
                url=url,
                status_code=status_code,
                latency=latency,
                request_size=request_size,
                response_size=response_size,
                start_time=start_time
            )
            
            return response
            
        except Exception as e:
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            self._emit_http_event(
                method=method,
                url=url,
                status_code=0,
                latency=latency,
                request_size=request_size,
                response_size=0,
                start_time=start_time,
                error=str(e)
            )
            
            self.stats['errors'] += 1
            raise
    
    def _get_request_size(self, kwargs: Dict) -> int:
        """Calculate request payload size"""
        size = 0
        
        # Check for data
        if 'data' in kwargs and kwargs['data']:
            if isinstance(kwargs['data'], (str, bytes)):
                size += len(kwargs['data'])
            elif hasattr(kwargs['data'], '__len__'):
                try:
                    size += len(str(kwargs['data']))
                except:
                    pass
        
        # Check for json
        if 'json' in kwargs and kwargs['json']:
            try:
                import json
                size += len(json.dumps(kwargs['json']))
            except:
                pass
        
        return size
    
    def _get_response_size(self, response) -> int:
        """Calculate response payload size"""
        try:
            if hasattr(response, 'content'):
                return len(response.content)
            elif hasattr(response, 'text'):
                return len(response.text.encode('utf-8'))
            elif hasattr(response, 'headers') and 'content-length' in response.headers:
                return int(response.headers['content-length'])
        except:
            pass
        
        return 0
    
    def _emit_http_event(self, method: str, url: str, status_code: int, 
                        latency: float, request_size: int, response_size: int,
                        start_time: float, error: Optional[str] = None):
        """Emit HTTP event to collector"""
        try:
            url_info = extract_url_info(url)
            caller_info = get_caller_info()
            
            event = {
                'timestamp': start_time,
                'event_type': 'http_request',
                'service_name': self.service_name,
                'method': method,
                'url': url,
                'endpoint': url_info['path'],
                'host': url_info['host'],
                'status_code': status_code,
                'latency_ms': latency,
                'request_size': request_size,
                'response_size': response_size,
                'caller_module': caller_info['module'],
                'caller_function': caller_info['function'],
                'error': error
            }
            
            self.event_emitter.emit(event)
            self.stats['events_emitted'] += 1
            self.stats['requests_instrumented'] += 1
            
        except Exception as e:
            logger.error(f"Failed to emit HTTP event: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get instrumentation statistics"""
        return self.stats.copy()
