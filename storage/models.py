"""
Data models and schemas for API Visualizer storage
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

@dataclass
class APIEvent:
    """
    Represents a single API request/response event
    """
    event_id: str
    timestamp: float
    event_type: str
    service_name: str
    method: str
    url: str
    endpoint: str
    host: str
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    request_size: int = 0
    response_size: int = 0
    caller_module: Optional[str] = None
    caller_function: Optional[str] = None
    framework: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIEvent':
        """Create from dictionary"""
        return cls(**data)
    
    def is_successful(self) -> bool:
        """Check if request was successful"""
        return self.status_code and 200 <= self.status_code < 400
    
    def is_error(self) -> bool:
        """Check if request had an error"""
        return self.error is not None or (self.status_code and self.status_code >= 400)
    
    def get_response_time_category(self) -> str:
        """Categorize response time"""
        if not self.latency_ms:
            return 'unknown'
        
        if self.latency_ms < 100:
            return 'fast'
        elif self.latency_ms < 500:
            return 'normal'
        elif self.latency_ms < 1000:
            return 'slow'
        else:
            return 'very_slow'

@dataclass
class ServiceDependency:
    """
    Represents a dependency relationship between services
    """
    caller_service: str
    target_service: str
    target_host: str
    call_count: int = 1
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime objects to strings
        if self.first_seen:
            data['first_seen'] = self.first_seen.isoformat()
        if self.last_seen:
            data['last_seen'] = self.last_seen.isoformat()
        return data
    
    def get_health_status(self) -> str:
        """Get health status based on error rate and latency"""
        if self.error_rate > 0.1:  # > 10% error rate
            return 'unhealthy'
        elif self.error_rate > 0.05 or self.avg_latency_ms > 1000:
            return 'warning'
        else:
            return 'healthy'

@dataclass
class EndpointMetrics:
    """
    Aggregated metrics for an endpoint over time
    """
    service_name: str
    endpoint: str
    method: str
    date_hour: str
    request_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    error_count: int = 0
    total_request_size: int = 0
    total_response_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def get_error_rate(self) -> float:
        """Calculate error rate percentage"""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100
    
    def get_avg_request_size(self) -> float:
        """Calculate average request size"""
        if self.request_count == 0:
            return 0.0
        return self.total_request_size / self.request_count
    
    def get_avg_response_size(self) -> float:
        """Calculate average response size"""
        if self.request_count == 0:
            return 0.0
        return self.total_response_size / self.request_count

@dataclass
class SystemMetric:
    """
    System-level metric (CPU, memory, request rate, etc.)
    """
    timestamp: float
    metric_name: str
    metric_value: float
    tags: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        if self.tags:
            data['tags'] = json.dumps(self.tags)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemMetric':
        """Create from dictionary"""
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        return cls(**data)

class EventValidator:
    """
    Validates event data before storage
    """
    
    REQUIRED_FIELDS = {
        'event_id', 'timestamp', 'event_type', 'service_name', 
        'method', 'url', 'endpoint', 'host'
    }
    
    VALID_EVENT_TYPES = {'http_request', 'incoming_request', 'system_metric'}
    VALID_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}
    
    @classmethod
    def validate_event(cls, event: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate event data
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        missing_fields = cls.REQUIRED_FIELDS - set(event.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")
        
        # Validate event type
        if event.get('event_type') not in cls.VALID_EVENT_TYPES:
            errors.append(f"Invalid event_type: {event.get('event_type')}")
        
        # Validate HTTP method
        if event.get('method') and event.get('method').upper() not in cls.VALID_METHODS:
            errors.append(f"Invalid HTTP method: {event.get('method')}")
        
        # Validate timestamp
        if not isinstance(event.get('timestamp'), (int, float)):
            errors.append("Invalid timestamp format")
        
        # Validate status code
        status_code = event.get('status_code')
        if status_code is not None and not (100 <= status_code <= 599):
            errors.append(f"Invalid status code: {status_code}")
        
        # Validate latency
        latency = event.get('latency_ms')
        if latency is not None and (not isinstance(latency, (int, float)) or latency < 0):
            errors.append(f"Invalid latency: {latency}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def sanitize_event(cls, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize event data (trim strings, normalize values, etc.)
        """
        sanitized = event.copy()
        
        # Trim string fields
        string_fields = ['service_name', 'method', 'url', 'endpoint', 'host', 'caller_module', 'caller_function']
        for field in string_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = sanitized[field].strip()[:500]  # Limit length
        
        # Normalize method to uppercase
        if 'method' in sanitized:
            sanitized['method'] = sanitized['method'].upper()
        
        # Ensure numeric fields are proper types
        if 'status_code' in sanitized and sanitized['status_code'] is not None:
            sanitized['status_code'] = int(sanitized['status_code'])
        
        if 'latency_ms' in sanitized and sanitized['latency_ms'] is not None:
            sanitized['latency_ms'] = float(sanitized['latency_ms'])
        
        # Ensure size fields are non-negative integers
        for size_field in ['request_size', 'response_size']:
            if size_field in sanitized:
                sanitized[size_field] = max(0, int(sanitized.get(size_field, 0)))
        
        return sanitized
