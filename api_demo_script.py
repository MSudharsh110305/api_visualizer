# SAMPLE DEMO TESTING

import os
import time
import threading
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

from instrumentation import instrument_all
from collector import get_collector

FIREBASE_DB_URL = "https://api-visualizer-demo-default-rtdb.firebaseio.com"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
SQLITE_DB_PATH = "api_visualizer.db"

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def setup_instrumentation():
    instrument_all(service_name="multi-api-demo")
    collector = get_collector(
        transport_type="memory",
        batch_size=10,
        batch_interval=3,
        db_path=SQLITE_DB_PATH
    )
    threading.Thread(target=collector.start, daemon=True).start()
    return collector

def firebase_write(path, data):
    url = f"{FIREBASE_DB_URL}{path}.json"
    response = requests.put(url, json=data, timeout=10)
    return response.status_code == 200

def firebase_push(path, data):
    url = f"{FIREBASE_DB_URL}{path}.json"
    response = requests.post(url, json=data, timeout=10)
    return response.status_code == 200

def fetch_weather(city):
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    r = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "city": city,
        "temp_c": data.get("main", {}).get("temp"),
        "humidity": data.get("main", {}).get("humidity"),
        "weather": (data.get("weather") or [{}])[0].get("description"),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def get_user_cities():
    cities = []
    print("Enter city names one by one. Enter '0' to stop input:")
    
    while True:
        city = input("Enter city: ").strip()
        if city == '0':
            break
        if city:
            cities.append(city)
            print(f"Added: {city}")
    
    if not cities:
        print("No cities entered. Using default cities.")
        return ["Madurai", "Chennai", "Coimbatore"]
    
    print(f"Selected cities: {', '.join(cities)}")
    return cities

def run_intensive_demo():
    
    cities = get_user_cities()
    
    log("Starting demo for API visualizer testing...")
    collector = setup_instrumentation()
    
    total_requests = 0
    successful_requests = 0
    
    for iteration in range(1, 151):
        
        weather_ok = False
        iteration_success = 0
        
        for city in cities:
            try:
                total_requests += 1
                summary = fetch_weather(city)
                
                firebase_push(f"/weather/by_city/{city}", summary)
                firebase_write("/weather/latest", summary)
                
                log(f"✅ {city}: {summary['temp_c']}°C - {summary['weather']}")
                weather_ok = True
                successful_requests += 1
                iteration_success += 1
                
            except Exception as e:
                log(f"❌ Error fetching {city}: {e}")
        
        firebase_write("/meta", {
            "last_run": datetime.utcnow().isoformat() + "Z",
            "current_iteration": iteration,
            "total_iterations": 150,
            "service_health": {"weather_ok": weather_ok},
            "statistics": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": f"{(successful_requests/total_requests*100):.1f}%" if total_requests > 0 else "0%"
            }
        })
        
        print(f"Iteration {iteration} complete: {iteration_success}/{len(cities)} cities successful")
        
        time.sleep(0.5)
    
    print(f"\nDemo completed!")
    print(f"   Total API requests: {total_requests}")
    print(f"   Successful requests: {successful_requests}")
    print(f"   Success rate: {(successful_requests/total_requests*100):.1f}%")
    print(f"   Cities tested: {len(cities)} ({', '.join(cities)})")
    
    time.sleep(10)
    collector.stop()

if __name__ == "__main__":
    run_intensive_demo()
