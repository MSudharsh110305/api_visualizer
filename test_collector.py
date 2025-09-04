import time
import requests
import threading
from instrumentation import instrument_all
from collector import get_collector
from storage import get_database

def run_collector():
    """
    Run the memory-based collector in the same process so we don't
    need 2 terminals.
    """
    collector = get_collector(
        transport_type='memory',
        batch_size=5,
        batch_interval=2,
        db_path='api_visualizer.db'
    )

    # Run collector loop in a thread
    t = threading.Thread(target=collector.start, daemon=True)
    t.start()
    return collector

def main():
    print("🚀 Starting Collector Module Test")
    print("="*60)

    # 1️⃣ Start instrumentation (MemoryTransport by default)
    instrument_all(service_name="collector-test")

    # 2️⃣ Start the collector
    collector = run_collector()

    # 3️⃣ Make some API calls to generate events
    api_key = "93849290175d48c4b7d622d8c8bade9e"  # NewsAPI key
    urls = [
        f"https://newsapi.org/v2/top-headlines?q=bitcoin&apiKey={api_key}",
        f"https://newsapi.org/v2/top-headlines?q=tech&apiKey={api_key}",
        f"https://newsapi.org/v2/everything?q=AI&apiKey={api_key}"
    ]

    print("📡 Making API calls...")
    for url in urls:
        try:
            r = requests.get(url)
            print(f"   {url} -> {r.status_code}")
        except Exception as e:
            print(f"   ❌ Error calling {url}: {e}")

    # Wait for batching to happen
    print("⏳ Waiting for collector to flush events...")
    time.sleep(5)

    # 4️⃣ Query the database to check stored events
    db = get_database('api_visualizer.db')
    events = db.get_events(limit=5)
    stats = db.get_database_stats()

    print("\n📊 DATABASE STATS")
    print("-"*60)
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n🔍 SAMPLE EVENTS")
    print("-"*60)
    for e in events:
        print(f"{e['method']} {e['host']}{e['endpoint']} -> {e['status_code']} ({e['latency_ms']:.1f}ms)")

    print("\n✅ Test completed")

if __name__ == "__main__":
    main()
