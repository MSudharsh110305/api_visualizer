from storage import get_database
from datetime import datetime, timedelta

def get_top_endpoints(limit=10, hours=24):
    db = get_database()
    cutoff = (datetime.now() - timedelta(hours=hours)).timestamp()
    query = """
        SELECT endpoint, method, service_name,
               COUNT(*) as count, 
               AVG(latency_ms) as avg_latency,
               SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
        FROM api_events
        WHERE timestamp > ?
        GROUP BY endpoint, method, service_name
        ORDER BY count DESC
        LIMIT ?
    """
    conn = db.get_connection()
    cur = conn.execute(query, (cutoff, limit))
    return cur.fetchall()

def get_latency_trend(hours=6, bucket_minutes=10):
    db = get_database()
    cutoff = (datetime.now() - timedelta(hours=hours)).timestamp()
    bucket_seconds = bucket_minutes * 60
    query = """
        SELECT ROUND(timestamp / ?, 0) * ? as bucket,
               AVG(latency_ms) as avg_latency,
               COUNT(*) as count
        FROM api_events
        WHERE timestamp > ?
        GROUP BY bucket
        ORDER BY bucket
    """
    conn = db.get_connection()
    cur = conn.execute(query, (bucket_seconds, bucket_seconds, cutoff))
    return cur.fetchall()

def get_service_dependencies():
    db = get_database()
    return db.get_service_dependencies()

def get_detailed_endpoint_stats(limit=20):
    """Get detailed endpoint performance metrics"""
    db = get_database()
    cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
    
    query = """
    SELECT endpoint, method, service_name,
           COUNT(*) as request_count,
           AVG(latency_ms) as avg_latency,
           MAX(latency_ms) as max_latency,
           MIN(latency_ms) as min_latency,
           AVG(request_size) as avg_request_size,
           AVG(response_size) as avg_response_size,
           SUM(response_size) as total_response_bytes,
           SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
    FROM api_events
    WHERE timestamp > ?
    GROUP BY endpoint, method, service_name
    ORDER BY request_count DESC
    LIMIT ?
    """
    
    conn = db.get_connection()
    cur = conn.execute(query, (cutoff, limit))
    return cur.fetchall()

def get_data_transfer_stats():
    """Get overall data transfer statistics"""
    db = get_database()
    cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
    
    query = """
    SELECT 
        SUM(request_size) as total_request_bytes,
        SUM(response_size) as total_response_bytes,
        AVG(request_size) as avg_request_bytes,
        AVG(response_size) as avg_response_bytes,
        COUNT(*) as total_requests
    FROM api_events
    WHERE timestamp > ?
    """
    
    conn = db.get_connection()
    cur = conn.execute(query, (cutoff,))
    return cur.fetchone()
