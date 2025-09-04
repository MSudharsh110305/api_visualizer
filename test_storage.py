# test_storage.py
from storage import get_database, store_events, query_events, get_metrics
import time
import random

# Test data
test_events = [
    {
        'event_id': f'test-{i}',
        'timestamp': time.time() - (i * 60),  # Events spaced 1 minute apart
        'event_type': 'http_request',
        'service_name': 'test-service',
        'method': 'GET',
        'url': f'https://api.example.com/users/{i}',
        'endpoint': f'/users/{i}',
        'host': 'api.example.com',
        'status_code': random.choice([200, 200, 200, 404, 500]),  # Mostly 200s
        'latency_ms': random.uniform(50, 500),
        'request_size': random.randint(0, 1000),
        'response_size': random.randint(500, 5000)
    }
    for i in range(20)
]

# Test storage
print("🔧 Testing storage module...")
stored_count = store_events(test_events)
print(f"✅ Stored {stored_count} events")

# Test queries
events = query_events(filters={'service_name': 'test-service'}, limit=5)
print(f"📊 Retrieved {len(events)} events")

# Test metrics
metrics = get_metrics('1h')
print(f"📈 Metrics: {metrics}")

# Database stats
db = get_database()
stats = db.get_database_stats()
print(f"💾 Database stats: {stats}")

print("🎉 Storage module working perfectly!")
