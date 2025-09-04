import sqlite3
import logging
import threading
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages SQLite database operations with thread safety and connection pooling
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or 'api_visualizer.db'
        self.connection_pool = threading.local()
        self._lock = threading.Lock()
        self._initialized = False
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        logger.info(f"DatabaseManager initialized with path: {self.db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self.connection_pool, 'connection'):
            self.connection_pool.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            # Enable foreign keys and WAL mode for better performance
            self.connection_pool.connection.execute("PRAGMA foreign_keys = ON")
            self.connection_pool.connection.execute("PRAGMA journal_mode = WAL")
            self.connection_pool.connection.execute("PRAGMA synchronous = NORMAL")
            
        return self.connection_pool.connection
    
    def initialize(self):
        """Initialize database schema"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            try:
                self._create_tables()
                self._create_indexes()
                self._initialized = True
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise
    
    def _create_tables(self):
        """Create all database tables"""
        conn = self.get_connection()
        
        # API Events table - stores individual HTTP requests
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                service_name TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                host TEXT NOT NULL,
                status_code INTEGER,
                latency_ms REAL,
                request_size INTEGER DEFAULT 0,
                response_size INTEGER DEFAULT 0,
                caller_module TEXT,
                caller_function TEXT,
                framework TEXT,
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Service Dependencies - tracks which services call which
        conn.execute("""
            CREATE TABLE IF NOT EXISTS service_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_service TEXT NOT NULL,
                target_service TEXT NOT NULL,
                target_host TEXT NOT NULL,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                call_count INTEGER DEFAULT 1,
                avg_latency_ms REAL,
                error_rate REAL DEFAULT 0,
                UNIQUE(caller_service, target_service, target_host)
            )
        """)
        
        # Endpoint Metrics - aggregated stats per endpoint
        conn.execute("""
            CREATE TABLE IF NOT EXISTS endpoint_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                date_hour TEXT NOT NULL,  -- YYYY-MM-DD-HH format
                request_count INTEGER DEFAULT 0,
                avg_latency_ms REAL,
                p95_latency_ms REAL,
                p99_latency_ms REAL,
                error_count INTEGER DEFAULT 0,
                total_request_size INTEGER DEFAULT 0,
                total_response_size INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(service_name, endpoint, method, date_hour)
            )
        """)
        
        # System Metrics - overall system health
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                tags TEXT,  -- JSON string of key-value pairs
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("Database tables created successfully")
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        conn = self.get_connection()
        
        indexes = [
            # API Events indexes
            "CREATE INDEX IF NOT EXISTS idx_api_events_timestamp ON api_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_api_events_service ON api_events(service_name)",
            "CREATE INDEX IF NOT EXISTS idx_api_events_endpoint ON api_events(service_name, endpoint)",
            "CREATE INDEX IF NOT EXISTS idx_api_events_status ON api_events(status_code)",
            "CREATE INDEX IF NOT EXISTS idx_api_events_host ON api_events(host)",
            
            # Service Dependencies indexes
            "CREATE INDEX IF NOT EXISTS idx_dependencies_caller ON service_dependencies(caller_service)",
            "CREATE INDEX IF NOT EXISTS idx_dependencies_target ON service_dependencies(target_service)",
            
            # Endpoint Metrics indexes
            "CREATE INDEX IF NOT EXISTS idx_endpoint_metrics_service ON endpoint_metrics(service_name)",
            "CREATE INDEX IF NOT EXISTS idx_endpoint_metrics_date ON endpoint_metrics(date_hour)",
            
            # System Metrics indexes
            "CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        logger.info("Database indexes created successfully")
    
    def store_events(self, events: List[Dict[str, Any]]) -> int:
        """
        Store a batch of API events
        
        Args:
            events: List of event dictionaries
            
        Returns:
            int: Number of events stored
        """
        if not events:
            return 0
        
        conn = self.get_connection()
        stored_count = 0
        
        try:
            with conn:  # Transaction
                for event in events:
                    try:
                        # Store main event
                        self._store_api_event(conn, event)
                        
                        # Update aggregated metrics
                        self._update_endpoint_metrics(conn, event)
                        self._update_service_dependencies(conn, event)
                        
                        stored_count += 1
                        
                    except sqlite3.IntegrityError as e:
                        if "UNIQUE constraint failed" in str(e):
                            logger.debug(f"Duplicate event skipped: {event.get('event_id')}")
                        else:
                            logger.error(f"Integrity error storing event: {e}")
                    except Exception as e:
                        logger.error(f"Error storing event: {e}")
                        logger.debug(f"Problematic event: {event}")
            
            logger.info(f"Stored {stored_count} events successfully")
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to store events batch: {e}")
            raise
    
    def _store_api_event(self, conn: sqlite3.Connection, event: Dict[str, Any]):
        """Store individual API event"""
        conn.execute("""
            INSERT OR IGNORE INTO api_events (
                event_id, timestamp, event_type, service_name, method, url, endpoint,
                host, status_code, latency_ms, request_size, response_size,
                caller_module, caller_function, framework, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get('event_id'),
            event.get('timestamp'),
            event.get('event_type'),
            event.get('service_name'),
            event.get('method'),
            event.get('url'),
            event.get('endpoint'),
            event.get('host'),
            event.get('status_code'),
            event.get('latency_ms'),
            event.get('request_size', 0),
            event.get('response_size', 0),
            event.get('caller_module'),
            event.get('caller_function'),
            event.get('framework'),
            event.get('error')
        ))
    
    def _update_endpoint_metrics(self, conn: sqlite3.Connection, event: Dict[str, Any]):
        """Update hourly endpoint metrics"""
        if not event.get('timestamp'):
            return
        
        # Convert timestamp to hour bucket
        dt = datetime.fromtimestamp(event['timestamp'])
        date_hour = dt.strftime('%Y-%m-%d-%H')
        
        # Insert or update metrics
        conn.execute("""
            INSERT INTO endpoint_metrics (
                service_name, endpoint, method, date_hour, request_count,
                avg_latency_ms, error_count, total_request_size, total_response_size
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(service_name, endpoint, method, date_hour) DO UPDATE SET
                request_count = request_count + 1,
                avg_latency_ms = (avg_latency_ms * (request_count - 1) + ?) / request_count,
                error_count = error_count + ?,
                total_request_size = total_request_size + ?,
                total_response_size = total_response_size + ?
        """, (
            event.get('service_name'),
            event.get('endpoint'),
            event.get('method'),
            date_hour,
            event.get('latency_ms', 0),
            event.get('error') is not None and 1 or 0,
            event.get('request_size', 0),
            event.get('response_size', 0),
            # For UPDATE clause
            event.get('latency_ms', 0),
            event.get('error') is not None and 1 or 0,
            event.get('request_size', 0),
            event.get('response_size', 0)
        ))
    
    def _update_service_dependencies(self, conn: sqlite3.Connection, event: Dict[str, Any]):
        """Update service dependency tracking"""
        caller_service = event.get('service_name')
        target_host = event.get('host')
        
        if not caller_service or not target_host:
            return
        
        # Determine target service from host
        target_service = self._extract_service_name(target_host)
        
        conn.execute("""
            INSERT INTO service_dependencies (
                caller_service, target_service, target_host, call_count,
                avg_latency_ms, error_rate
            ) VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(caller_service, target_service, target_host) DO UPDATE SET
                call_count = call_count + 1,
                avg_latency_ms = (avg_latency_ms * (call_count - 1) + ?) / call_count,
                error_rate = (error_rate * (call_count - 1) + ?) / call_count,
                last_seen = CURRENT_TIMESTAMP
        """, (
            caller_service,
            target_service,
            target_host,
            event.get('latency_ms', 0),
            1 if event.get('error') or (event.get('status_code', 0) >= 400) else 0,
            # For UPDATE clause
            event.get('latency_ms', 0),
            1 if event.get('error') or (event.get('status_code', 0) >= 400) else 0
        ))
    
    def _extract_service_name(self, host: str) -> str:
        """Extract service name from hostname"""
        if not host:
            return 'unknown'
        
        # Common patterns
        if 'api.github.com' in host:
            return 'github-api'
        elif 'newsapi.org' in host:
            return 'newsapi'
        elif 'httpbin.org' in host:
            return 'httpbin'
        elif 'localhost' in host or '127.0.0.1' in host:
            return 'localhost'
        else:
            # Extract first part of domain
            parts = host.split('.')
            return parts[0] if parts else host
    
    def get_events(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Query API events with filters
        
        Args:
            filters: Dictionary of filter conditions
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of event dictionaries
        """
        conn = self.get_connection()
        
        # Build query
        where_clauses = []
        params = []
        
        if filters:
            if 'service_name' in filters:
                where_clauses.append("service_name = ?")
                params.append(filters['service_name'])
            
            if 'method' in filters:
                where_clauses.append("method = ?")
                params.append(filters['method'])
            
            if 'status_code' in filters:
                where_clauses.append("status_code = ?")
                params.append(filters['status_code'])
            
            if 'host' in filters:
                where_clauses.append("host LIKE ?")
                params.append(f"%{filters['host']}%")
            
            if 'time_from' in filters:
                where_clauses.append("timestamp >= ?")
                params.append(filters['time_from'])
            
            if 'time_to' in filters:
                where_clauses.append("timestamp <= ?")
                params.append(filters['time_to'])
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT * FROM api_events 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_service_dependencies(self) -> List[Dict[str, Any]]:
        """Get all service dependencies"""
        conn = self.get_connection()
        
        cursor = conn.execute("""
            SELECT caller_service, target_service, target_host, call_count,
                   avg_latency_ms, error_rate, last_seen
            FROM service_dependencies
            ORDER BY call_count DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove old data beyond retention period"""
        cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).timestamp()
        
        conn = self.get_connection()
        
        with conn:
            # Clean old events
            result = conn.execute("DELETE FROM api_events WHERE timestamp < ?", (cutoff_time,))
            deleted_events = result.rowcount
            
            # Clean old metrics
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            result = conn.execute("DELETE FROM endpoint_metrics WHERE date_hour < ?", (cutoff_date,))
            deleted_metrics = result.rowcount
        
        logger.info(f"Cleaned up {deleted_events} old events and {deleted_metrics} old metrics")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.get_connection()
        
        stats = {}
        
        # Table counts
        for table in ['api_events', 'service_dependencies', 'endpoint_metrics', 'system_metrics']:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Database size
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        
        cursor = conn.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        
        stats['database_size_bytes'] = page_size * page_count
        stats['database_path'] = self.db_path
        
        return stats
    
    def close(self):
        """Close database connections"""
        if hasattr(self.connection_pool, 'connection'):
            self.connection_pool.connection.close()
