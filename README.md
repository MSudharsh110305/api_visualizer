# API Visualizer

A lightweight Python library for instrumenting HTTP requests, collecting API performance metrics, and visualizing service interactions through an integrated dashboard.

<br>

## 📌 Overview

API Visualizer provides **non-intrusive monitoring** for Python applications that make HTTP requests.  
It captures request/response metadata, performance statistics, and service dependencies **without requiring changes** to your existing API calls.

<br>

## ⚙️ Core Components

The library consists of four main modules:

- **Instrumentation** → Automatic HTTP request interception and metadata extraction  
- **Collector** → Configurable data collection with batching and persistence  
- **Storage** → SQLite-based data persistence with query optimization  
- **Dashboard** → Streamlit-based visualization interface  

<br>

## 🚀 Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
````

Clone the repository:

```bash
git clone https://github.com/MSudharsh110305/api_visualizer.git
cd api_visualizer
```

<br>

## ⚡ Quick Integration

### Basic Setup

Add API monitoring to your existing Python application:

```python
from instrumentation import instrument_all
from collector import get_collector
import requests

# Enable automatic HTTP request tracking
instrument_all(service_name="your-application")

# Configure data collector
collector = get_collector(
    transport_type="memory",
    batch_size=10,
    batch_interval=3,
    db_path="api_metrics.db"
)

collector.start()

# Your existing code continues to work unchanged
response = requests.get("https://api.example.com/users")
```

### Advanced Configuration

Customize instrumentation behavior:

```python
from instrumentation import instrument_all

instrument_all(
    service_name="user-service",
    ignore_patterns=["/health", "/metrics"],
    capture_headers=True,
    capture_body=False
)
```

Configure collector settings:

```python
from collector import get_collector

collector = get_collector(
    transport_type="memory",      
    batch_size=50,                
    batch_interval=5,             
    db_path="custom_path.db",     
    max_queue_size=1000           
)
```

<br>

## 🧩 Integration Patterns

### Web Applications (Flask)

```python
from flask import Flask
from instrumentation import instrument_all
from collector import get_collector
import requests

app = Flask(__name__)

# Initialize monitoring
instrument_all(service_name="flask-api")
collector = get_collector(transport_type="memory", db_path="flask_api.db")
collector.start()

@app.route('/users')
def get_users():
    response = requests.get("https://api.external.com/users")
    return response.json()
```

### Microservices

```python
import requests
from instrumentation import instrument_all
from collector import get_collector

class UserService:
    def __init__(self):
        instrument_all(service_name="user-service")
        self.collector = get_collector(db_path="user_service_metrics.db")
        self.collector.start()
    
    def get_user_profile(self, user_id):
        profile = requests.get(f"https://profile-service/users/{user_id}")
        preferences = requests.get(f"https://pref-service/users/{user_id}/prefs")
        return {"profile": profile.json(), "preferences": preferences.json()}
```

### Batch Processing

```python
from instrumentation import instrument_all
from collector import get_collector
import requests, time

def process_data_batch(data_items):
    instrument_all(service_name="data-processor")
    collector = get_collector(db_path="batch_job_metrics.db")
    collector.start()
    
    try:
        for item in data_items:
            requests.post("https://api.processor.com/process", json=item)
    finally:
        time.sleep(5)  # Ensure metrics flush
        collector.stop()
```

<br>

## 📊 Dashboard Usage

### Starting the Dashboard

```bash
streamlit run dashboard/app.py
```

### Custom Database Path

Modify in `dashboard/queries.py`:

```python
DATABASE_PATH = "/path/to/your/application/metrics.db"
```

### Dashboard Features

* **Endpoint Performance** → Request counts, response times, error rates
* **Service Topology** → Visual representation of service interactions
* **Latency Analysis** → Time-series response time analysis
* **Data Transfer Metrics** → Request/response payload statistics

<br>

## ⚙️ Configuration Options

### Instrumentation Settings

```python
instrument_all(
    service_name="my-service",
    ignore_patterns=["/health", "/metrics", r".*\.css", r".*\.js"],
    capture_headers=False,
    capture_body=False,
    max_body_size=1024
)
```

### Collector Configuration

```python
collector = get_collector(
    transport_type="memory",
    batch_size=25,
    batch_interval=10,
    db_path="metrics.db",
    max_queue_size=5000,
    compression=True,
    retention_days=30
)
```

<br>

## 📖 API Reference

### Instrumentation Module

#### `instrument_all(service_name, **kwargs)`

Enables automatic HTTP request monitoring.

**Parameters:**

* `service_name` (str): Identifier for the service
* `ignore_patterns` (list): URL patterns to exclude
* `capture_headers` (bool): Include headers
* `capture_body` (bool): Include request/response bodies
* `max_body_size` (int): Maximum body size (bytes)

<br>

### Collector Module

#### `get_collector(transport_type, **kwargs)`

Creates and configures a data collector instance.

**Parameters:**

* `transport_type` (str): Backend ("memory", "file", "http")
* `batch_size` (int): Events per batch
* `batch_interval` (int): Flush interval (seconds)
* `db_path` (str): SQLite database file path
* `max_queue_size` (int): Maximum in-memory events

**Returns:** Collector instance (`start()`, `stop()` methods)

<br>

### Storage Module

Handles SQLite operations and provides query interfaces.

**Schema includes:**

* `api_events` → Individual request/response records
* `service_dependencies` → Inter-service communication patterns
* `endpoint_statistics` → Aggregated performance metrics

<br>

## ⚡ Performance Considerations

* **Memory Usage** → Configure `max_queue_size` for memory-limited environments
* **Database Performance** → Use SSDs, cleanup old records, tune batch sizes
* **Network Overhead** → Interception adds <1ms overhead

<br>

## 🛠️ Troubleshooting

**Dashboard shows no data**

* Ensure `collector.start()` is called
* Verify database path in dashboard config
* Make requests after instrumentation

**High memory usage**

* Reduce `max_queue_size`
* Increase `batch_size`
* Enable retention policies

**Performance degradation**

* Disable header/body capture
* Increase `batch_interval`
* Exclude noisy endpoints via `ignore_patterns`

<br>

## 📦 Requirements

* Python 3.8+
* SQLite 3.0+
* Dependencies:
  `streamlit`, `plotly`, `pandas`, `networkx`, `requests`, `python-dotenv`


## 📜 License

[CC BY-NC-SA 4.0](LICENSE) © Sudharsh | Non-commercial use only
