"""
Utility functions for instrumentation
Includes URL filtering, service detection, and helper functions
"""

import os
import sys
import inspect
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_service_name() -> str:
    """
    Auto-detect service name from various sources
    """
    # Try environment variable first
    service_name = os.environ.get('API_VISUALIZER_SERVICE_NAME')
    if service_name:
        return service_name
    
    # Try to get from main module
    try:
        main_module = sys.modules['__main__']
        if hasattr(main_module, '__file__') and main_module.__file__:
            return os.path.splitext(os.path.basename(main_module.__file__))[0]
    except:
        pass
    
    # Try to detect from common frameworks
    if 'flask' in sys.modules:
        try:
            import flask
            if hasattr(flask, 'current_app') and flask.current_app:
                return getattr(flask.current_app, 'name', 'flask-app')
        except:
            pass
        return 'flask-app'
    
    if 'fastapi' in sys.modules:
        return 'fastapi-app'
    
    if 'django' in sys.modules:
        try:
            from django.conf import settings
            return getattr(settings, 'API_VISUALIZER_SERVICE_NAME', 'django-app')
        except:
            pass
        return 'django-app'
    
    # Fallback
    return 'unknown-service'

def should_instrument_url(url: str, config: Dict[str, Any]) -> bool:
    """
    Determine if a URL should be instrumented based on configuration
    
    Args:
        url: URL to check
        config: Configuration with include/exclude patterns
    
    Returns:
        True if URL should be instrumented
    """
    if not url:
        return False
    
    instrumentation_config = config.get('instrumentation', {})
    
    # Check exclude patterns
    exclude_patterns = instrumentation_config.get('exclude_urls', [
        '/health',
        '/ping',
        '/metrics',
        '/favicon.ico',
        '/static/',
        '/__pycache__'
    ])
    
    for pattern in exclude_patterns:
        if pattern in url.lower():
            return False
    
    # Check include patterns (if specified)
    include_patterns = instrumentation_config.get('include_urls', [])
    if include_patterns:
        for pattern in include_patterns:
            if pattern in url.lower():
                return True
        return False  # If include patterns specified but none match
    
    # Check sampling rate
    sample_rate = instrumentation_config.get('sample_rate', 1.0)
    if sample_rate < 1.0:
        import random
        if random.random() > sample_rate:
            return False
    
    return True

def extract_url_info(url: str) -> Dict[str, str]:
    """
    Extract structured information from URL
    
    Args:
        url: Full URL or path
    
    Returns:
        Dictionary with host, path, scheme, etc.
    """
    try:
        # Handle relative URLs
        if url.startswith('/'):
            return {
                'scheme': '',
                'host': 'localhost',
                'port': None,
                'path': url,
                'query': '',
                'fragment': ''
            }
        
        parsed = urlparse(url)
        return {
            'scheme': parsed.scheme or 'http',
            'host': parsed.hostname or 'localhost',
            'port': parsed.port,
            'path': parsed.path or '/',
            'query': parsed.query,
            'fragment': parsed.fragment
        }
    
    except Exception as e:
        logger.debug(f"Failed to parse URL {url}: {e}")
        return {
            'scheme': '',
            'host': 'unknown',
            'port': None,
            'path': url,
            'query': '',
            'fragment': ''
        }

def get_caller_info() -> Dict[str, str]:
    """
    Get information about the calling code
    
    Returns:
        Dictionary with module and function information
    """
    try:
        # Walk up the stack to find the first non-instrumentation frame
        for frame_info in inspect.stack()[1:]:
            filename = frame_info.filename
            
            # Skip instrumentation frames
            if 'instrumentation' in filename or 'api_visualizer' in filename:
                continue
            
            # Skip standard library frames
            if 'site-packages' in filename or filename.startswith('<'):
                continue
            
            module_name = _get_module_name_from_file(filename)
            function_name = frame_info.function
            
            return {
                'module': module_name,
                'function': function_name,
                'filename': filename,
                'lineno': frame_info.lineno
            }
    
    except Exception as e:
        logger.debug(f"Failed to get caller info: {e}")
    
    return {
        'module': 'unknown',
        'function': 'unknown',
        'filename': 'unknown',
        'lineno': 0
    }

def _get_module_name_from_file(filename: str) -> str:
    """Extract module name from file path"""
    try:
        # Get relative path from current working directory
        import os
        rel_path = os.path.relpath(filename)
        
        # Remove .py extension and convert path separators to dots
        if rel_path.endswith('.py'):
            rel_path = rel_path[:-3]
        
        module_name = rel_path.replace(os.path.sep, '.')
        
        # Clean up module name
        if module_name.startswith('./'):
            module_name = module_name[2:]
        
        return module_name
    
    except:
        return os.path.basename(filename)

def detect_frameworks() -> Dict[str, bool]:
    """
    Detect which web frameworks are available/loaded
    
    Returns:
        Dictionary mapping framework names to availability
    """
    frameworks = {}
    
    # Check Flask
    try:
        import flask
        frameworks['Flask'] = True
    except ImportError:
        frameworks['Flask'] = False
    
    # Check FastAPI
    try:
        import fastapi
        frameworks['FastAPI'] = True
    except ImportError:
        frameworks['FastAPI'] = False
    
    # Check Django
    try:
        import django
        frameworks['Django'] = True
    except ImportError:
        frameworks['Django'] = False
    
    return frameworks

def get_http_libraries() -> Dict[str, bool]:
    """
    Detect which HTTP client libraries are available
    
    Returns:
        Dictionary mapping library names to availability
    """
    libraries = {}
    
    # Check requests
    try:
        import requests
        libraries['requests'] = True
    except ImportError:
        libraries['requests'] = False
    
    # Check httpx
    try:
        import httpx
        libraries['httpx'] = True
    except ImportError:
        libraries['httpx'] = False
    
    # Check aiohttp
    try:
        import aiohttp
        libraries['aiohttp'] = True
    except ImportError:
        libraries['aiohttp'] = False
    
    return libraries

def format_bytes(bytes_count: int) -> str:
    """Format byte count as human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"

def format_duration(milliseconds: float) -> str:
    """Format duration as human-readable string"""
    if milliseconds < 1000:
        return f"{milliseconds:.1f}ms"
    
    seconds = milliseconds / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    
    hours = minutes / 60
    return f"{hours:.1f}h"

def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging"""
    import platform
    
    try:
        # Try to import psutil, but don't fail if not available
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            memory_gb = round(psutil.virtual_memory().total / (1024**3), 2)
        except ImportError:
            cpu_count = os.cpu_count()
            memory_gb = 'unknown'
        
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': cpu_count,
            'memory_gb': memory_gb,
            'frameworks': detect_frameworks(),
            'http_libraries': get_http_libraries()
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {'error': str(e)}
