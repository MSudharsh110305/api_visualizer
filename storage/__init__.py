"""
API Visualizer Storage Module
Provides SQLite-based persistence for API events and metrics
"""

from .database import DatabaseManager
from .models import APIEvent, ServiceDependency, EndpointMetrics
from .queries import QueryBuilder, MetricsAnalyzer

# Global database instance
_db_manager = None

def get_database(db_path=None):
    """
    Get or create the global database manager instance
    
    Args:
        db_path (str): Path to SQLite database file
    
    Returns:
        DatabaseManager: Database manager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path=db_path)
        _db_manager.initialize()
    
    return _db_manager

def store_events(events, db_path=None):
    """
    Store a batch of events in the database
    
    Args:
        events (list): List of event dictionaries
        db_path (str): Optional database path
    """
    db = get_database(db_path)
    return db.store_events(events)

def query_events(filters=None, limit=1000, db_path=None):
    """
    Query events from database
    
    Args:
        filters (dict): Query filters
        limit (int): Maximum results to return
        db_path (str): Optional database path
    
    Returns:
        list: Matching events
    """
    db = get_database(db_path)
    query_builder = QueryBuilder(db)
    return query_builder.get_events(filters=filters, limit=limit)

def get_metrics(time_window='1h', db_path=None):
    """
    Get aggregated metrics
    
    Args:
        time_window (str): Time window (e.g., '1h', '24h', '7d')
        db_path (str): Optional database path
    
    Returns:
        dict: Aggregated metrics
    """
    db = get_database(db_path)
    analyzer = MetricsAnalyzer(db)
    return analyzer.get_overview_metrics(time_window)

__all__ = [
    'DatabaseManager',
    'APIEvent', 
    'ServiceDependency',
    'EndpointMetrics',
    'QueryBuilder',
    'MetricsAnalyzer',
    'get_database',
    'store_events',
    'query_events',
    'get_metrics'
]
