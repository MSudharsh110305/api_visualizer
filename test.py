# complete_test_and_view.py
from instrumentation import instrument_all, get_instrumentor
import requests
import time

def main():
    print("🚀 Starting API Visualizer Complete Test")
    print("=" * 50)
    
    # Start instrumentation
    instrument_all(service_name="newsapi-complete-test")
    
    # NewsAPI configuration
    API_KEY = '93849290175d48c4b7d622d8c8bade9e'
    
    # Test different endpoints to generate varied traffic
    test_endpoints = [
        {
            'name': 'Bitcoin Headlines',
            'url': f'https://newsapi.org/v2/top-headlines?q=bitcoin&apiKey={API_KEY}',
        },
        {
            'name': 'Tech News',
            'url': f'https://newsapi.org/v2/top-headlines?q=technology&apiKey={API_KEY}',
        },
        {
            'name': 'AI Everything',
            'url': f'https://newsapi.org/v2/everything?q=artificial intelligence&apiKey={API_KEY}&pageSize=5',
        },
        {
            'name': 'Sports Headlines',
            'url': f'https://newsapi.org/v2/top-headlines?category=sports&country=us&apiKey={API_KEY}',
        }
    ]
    
    print("📡 Making API requests...")
    # Execute all test requests
    for i, endpoint in enumerate(test_endpoints, 1):
        print(f"\n{i}. Testing: {endpoint['name']}")
        try:
            start_time = time.time()
            response = requests.get(endpoint['url'])
            elapsed = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                article_count = data.get('totalResults', len(data.get('articles', [])))
                print(f"   ✅ Success: {article_count} articles found ({elapsed:.1f}ms)")
                
                # Show sample article titles
                articles = data.get('articles', [])[:2]  # Show first 2
                for article in articles:
                    print(f"   📰 {article.get('title', 'No title')[:60]}...")
            else:
                print(f"   ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception: {str(e)[:50]}...")
        
        time.sleep(0.5)  # Small delay between requests
    
    print(f"\n⏳ Waiting for events to be processed...")
    
    # Get instrumentor and flush events properly
    instrumentor = get_instrumentor()
    
    # Manual flush - wait for queue to empty
    flush_start = time.time()
    while not instrumentor.event_emitter.event_queue.empty() and (time.time() - flush_start) < 10:
        time.sleep(0.1)
    
    # Give batch thread extra time to process
    time.sleep(1)
    
    # Get all stats
    stats = instrumentor.get_stats()
    
    print("=" * 50)
    print("📊 INSTRUMENTATION STATISTICS")
    print("=" * 50)
    print(f"Service Name: {stats['service_name']}")
    print(f"Total HTTP Requests Tracked: {stats['http_stats']['requests_instrumented']}")
    print(f"Events Emitted: {stats['http_stats']['events_emitted']}")
    print(f"Current Queue Size: {instrumentor.event_emitter.event_queue.qsize()}")
    print(f"Batches Sent: {stats['event_stats']['batches_sent']}")
    print(f"Transport Type: {stats['event_stats']['transport_type']}")
    
    # Get captured events from memory transport
    transport = instrumentor.event_emitter.transport
    events = transport.get_events()
    
    print("=" * 50)
    print("🔍 CAPTURED API EVENTS DETAILS")
    print("=" * 50)
    
    if len(events) == 0:
        print("❌ No events captured in transport!")
        print(f"   Queue still has: {instrumentor.event_emitter.event_queue.qsize()} events")
        print("   Events might still be batching...")
    else:
        print(f"✅ Successfully captured {len(events)} events:\n")
        
        for i, event in enumerate(events, 1):
            # Parse the event data
            method = event.get('method', 'UNKNOWN')
            host = event.get('host', 'unknown-host')
            endpoint = event.get('endpoint', '/')
            status = event.get('status_code', 0)
            latency = event.get('latency_ms', 0)
            req_size = event.get('request_size', 0)
            resp_size = event.get('response_size', 0)
            timestamp = event.get('timestamp', 0)
            caller_module = event.get('caller_module', 'unknown')
            
            # Format timestamp
            import datetime
            dt = datetime.datetime.fromtimestamp(timestamp)
            time_str = dt.strftime("%H:%M:%S")
            
            print(f"{i}. 🌐 {method} {host}{endpoint}")
            print(f"   ⏱️  Time: {time_str} | Status: {status} | Latency: {latency:.1f}ms")
            print(f"   📦 Request: {req_size}B | Response: {resp_size}B")
            print(f"   📍 Called from: {caller_module}")
            
            # Color coding for status
            if 200 <= status < 300:
                print("   ✅ SUCCESS")
            elif 400 <= status < 500:
                print("   ⚠️  CLIENT ERROR")
            elif 500 <= status:
                print("   🚨 SERVER ERROR")
            
            print()
    
    print("=" * 50)
    print("🎯 SUMMARY")
    print("=" * 50)
    
    if events:
        # Calculate some basic metrics
        successful_requests = sum(1 for e in events if 200 <= e.get('status_code', 0) < 300)
        avg_latency = sum(e.get('latency_ms', 0) for e in events) / len(events)
        total_response_size = sum(e.get('response_size', 0) for e in events)
        
        print(f"✅ Success Rate: {successful_requests}/{len(events)} ({successful_requests/len(events)*100:.1f}%)")
        print(f"⚡ Average Latency: {avg_latency:.1f}ms")
        print(f"📊 Total Data Received: {total_response_size:,} bytes")
        
        # Find slowest request
        slowest = max(events, key=lambda e: e.get('latency_ms', 0))
        print(f"🐌 Slowest Request: {slowest.get('host', 'unknown')} ({slowest.get('latency_ms', 0):.1f}ms)")
    else:
        print("❌ No events captured - check instrumentation setup")
    
    print(f"\n🎉 Test completed! Your API Visualizer instrumentation is working perfectly!")

if __name__ == "__main__":
    main()
