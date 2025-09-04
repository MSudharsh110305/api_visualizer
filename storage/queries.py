"""
Query builder and analytics for API Visualizer storage
"""

import sqlite3
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)

class QueryBuilder:
    """
    Builds and executes complex queries against the API events database
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_events(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """Get events with advanced filtering"""
        return self.db.get_events(filters=filters, limit=limit, offset=offset)
    
    def get_events_by_time_range(self, start_time: float, end_time: float, 
                                service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events within a specific time range"""
        filters = {
            'time_from': start_time,
            'time_to': end_time
        }
        
        if service_name:
            filters['service_name'] = service_name
        
        return self.get_events(filters=filters, limit=10000)
    
    def get_top_endpoints(self, limit: int = 10, 
                         time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """Get most frequently called endpoints"""
        conn = self.db.get_connection()
        
        cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).timestamp()
        
        cursor = conn.execute("""
            SELECT endpoint, method, service_name, COUNT(*) as request_count,
                   AVG(latency_ms) as avg_latency,
                   AVG(response_size) as avg_response_size
            FROM api_events 
            WHERE timestamp > ?
            GROUP BY endpoint, method, service_name
            ORDER BY request_count DESC
            LIMIT ?
        """, (cutoff_time, limit))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_slowest_endpoints(self, limit: int = 10,
                            time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """Get slowest endpoints by average latency"""
        conn = self.db.get_connection()
        
        cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).timestamp()
        
        cursor = conn.execute("""
            SELECT endpoint, method, service_name, COUNT(*) as request_count,
                   AVG(latency_ms) as avg_latency,
                   MAX(latency_ms) as max_latency,
                   MIN(latency_ms) as min_latency
            FROM api_events 
            WHERE timestamp > ? AND latency_ms IS NOT NULL
            GROUP BY endpoint, method, service_name
            HAVING COUNT(*) >= 5  -- At least 5 requests
            ORDER BY avg_latency DESC
            LIMIT ?
        """, (cutoff_time, limit))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_error_endpoints(self, limit: int = 10,
                           time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """Get endpoints with highest error rates"""
        conn = self.db.get_connection()
        
        cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).timestamp()
        
        cursor = conn.execute("""
            SELECT endpoint, method, service_name,
                   COUNT(*) as total_requests,
                   SUM(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) as error_count,
                   ROUND((SUM(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as error_rate
            FROM api_events 
            WHERE timestamp > ?
            GROUP BY endpoint, method, service_name
            HAVING COUNT(*) >= 5 AND error_rate > 0
            ORDER BY error_rate DESC, error_count DESC
            LIMIT ?
        """, (cutoff_time, limit))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_request_timeline(self, time_window_hours: int = 24, 
                            bucket_minutes: int = 15) -> List[Dict[str, Any]]:
        """Get request count timeline with time buckets"""
        conn = self.db.get_connection()
        
        cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).timestamp()
        bucket_seconds = bucket_minutes * 60
        
        cursor = conn.execute("""
            SELECT 
                CAST((timestamp / ?) AS INTEGER) * ? as time_bucket,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) as error_count
            FROM api_events 
            WHERE timestamp > ?
            GROUP BY time_bucket
            ORDER BY time_bucket
        """, (bucket_seconds, bucket_seconds, cutoff_time))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_service_call_matrix(self) -> List[Dict[str, Any]]:
        """Get service-to-service call matrix"""
        return self.db.get_service_dependencies()
    
    def search_events(self, search_term: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search events by URL, endpoint, or host"""
        conn = self.db.get_connection()
        
        cursor = conn.execute("""
            SELECT * FROM api_events 
            WHERE url LIKE ? OR endpoint LIKE ? OR host LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", limit))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

class MetricsAnalyzer:
    """
    Analyzes stored data to generate insights and metrics
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_overview_metrics(self, time_window: str = '24h') -> Dict[str, Any]:
        """
        Get high-level overview metrics
        
        Args:
            time_window: Time window ('1h', '24h', '7d', '30d')
        """
        hours = self._parse_time_window(time_window)
        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        conn = self.db.get_connection()
        
        # Basic counts
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(DISTINCT service_name) as unique_services,
                COUNT(DISTINCT host) as unique_hosts,
                COUNT(DISTINCT endpoint) as unique_endpoints,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) as error_count
            FROM api_events 
            WHERE timestamp > ?
        """, (cutoff_time,))
        
        result = cursor.fetchone()
        
        metrics = {
            'total_requests': result[0],
            'unique_services': result[1],
            'unique_hosts': result[2],
            'unique_endpoints': result[3],
            'avg_latency_ms': round(result[4] or 0, 2),
            'error_count': result[5],
            'error_rate': round((result[5] / result[0] * 100) if result[0] > 0 else 0, 2),
            'time_window': time_window
        }
        
        # Request rate (requests per minute)
        if hours > 0:
            metrics['requests_per_minute'] = round(result[0] / (hours * 60), 2)
        else:
            metrics['requests_per_minute'] = 0
        
        return metrics
    
    def get_latency_percentiles(self, time_window: str = '24h') -> Dict[str, float]:
        """Calculate latency percentiles"""
        hours = self._parse_time_window(time_window)
        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        conn = self.db.get_connection()
        
        cursor = conn.execute("""
            SELECT latency_ms FROM api_events 
            WHERE timestamp > ? AND latency_ms IS NOT NULL
            ORDER BY latency_ms
        """, (cutoff_time,))
        
        latencies = [row[0] for row in cursor.fetchall()]
        
        if not latencies:
            return {}
        
        try:
            return {
                'p50': round(statistics.median(latencies), 2),
                'p90': round(statistics.quantiles(latencies, n=10)[8], 2),  # 90th percentile
                'p95': round(statistics.quantiles(latencies, n=20)[18], 2),  # 95th percentile
                'p99': round(statistics.quantiles(latencies, n=100)[98], 2),  # 99th percentile
            }
        except statistics.StatisticsError:
            # Fallback for small datasets
            return {
                'p50': round(statistics.median(latencies), 2),
                'p90': round(max(latencies), 2),
                'p95': round(max(latencies), 2),
                'p99': round(max(latencies), 2),
            }
    
    def get_status_code_distribution(self, time_window: str = '24h') -> Dict[str, int]:
        """Get distribution of HTTP status codes"""
        hours = self._parse_time_window(time_window)
        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        conn = self.db.get_connection()
        
        cursor = conn.execute("""
            SELECT 
                CASE 
                    WHEN status_code BETWEEN 200 AND 299 THEN '2xx'
                    WHEN status_code BETWEEN 300 AND 399 THEN '3xx'
                    WHEN status_code BETWEEN 400 AND 499 THEN '4xx'
                    WHEN status_code BETWEEN 500 AND 599 THEN '5xx'
                    ELSE 'other'
                END as status_group,
                COUNT(*) as count
            FROM api_events 
            WHERE timestamp > ? AND status_code IS NOT NULL
            GROUP BY status_group
        """, (cutoff_time,))
        
        return dict(cursor.fetchall())
    
    def get_hourly_trends(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get hourly request trends over multiple days"""
        cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
        
        conn = self.db.get_connection()
        
        cursor = conn.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00:00', datetime(timestamp, 'unixepoch')) as hour_bucket,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) as error_count
            FROM api_events 
            WHERE timestamp > ?
            GROUP BY hour_bucket
            ORDER BY hour_bucket
        """, (cutoff_time,))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_data_transfer_stats(self, time_window: str = '24h') -> Dict[str, Any]:
        """Get data transfer statistics"""
        hours = self._parse_time_window(time_window)
        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        conn = self.db.get_connection()
        
        cursor = conn.execute("""
            SELECT 
                SUM(request_size) as total_request_bytes,
                SUM(response_size) as total_response_bytes,
                AVG(request_size) as avg_request_bytes,
                AVG(response_size) as avg_response_bytes,
                MAX(response_size) as max_response_bytes
            FROM api_events 
            WHERE timestamp > ?
        """, (cutoff_time,))
        
        result = cursor.fetchone()
        
        return {
            'total_request_bytes': result[0] or 0,
            'total_response_bytes': result[1] or 0,
            'avg_request_bytes': round(result[2] or 0, 2),
            'avg_response_bytes': round(result[3] or 0, 2),
            'max_response_bytes': result[4] or 0,
            'total_bytes': (result[0] or 0) + (result[1] or 0)
        }
    
    def _parse_time_window(self, time_window: str) -> int:
        """Parse time window string to hours"""
        if time_window.endswith('h'):
            return int(time_window[:-1])
        elif time_window.endswith('d'):
            return int(time_window[:-1]) * 24
        elif time_window.endswith('m'):
            return int(time_window[:-1]) // 60
        else:
            return 24  # Default to 24 hours
