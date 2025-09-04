"""
Default configuration values for all modules
"""

from typing import Dict, Any

def get_default_config() -> Dict[str, Any]:
    """Get default configuration for all modules"""
    return {
        'environment': 'development',
        'service_name': 'api-visualizer',
        
        'instrumentation': {
            'enabled': True,
            'sample_rate': 1.0,
            'exclude_urls': ['/health', '/ping', '/metrics', '/favicon.ico'],
            'include_urls': [],
            'transport_type': 'memory',
            'batch_size': 100,
            'batch_timeout': 5.0
        },
        
        'storage': {
            'db_path': 'api_visualizer.db',
            'connection_pool_size': 5,
            'retention_days': 30,
            'auto_vacuum': True,
            'backup_enabled': False,
            'backup_interval_hours': 24
        },
        
        'alerting': {
            'check_interval': 60,
            'thresholds': {
                'latency_ms': {
                    'enabled': True,
                    'value': 1000,
                    'time_window': '5m',
                    'severity': 'critical'
                },
                'error_rate_percent': {
                    'enabled': True,
                    'value': 5.0,
                    'time_window': '10m',
                    'severity': 'critical'
                },
                'traffic_spike_percent': {
                    'enabled': True,
                    'value': 100,
                    'time_window': '5m',
                    'severity': 'warning'
                }
            },
            'notifications': {
                'slack': {
                    'enabled': False,
                    'webhook_url': '',
                    'channel': '#alerts',
                    'username': 'API-Visualizer',
                    'icon_emoji': ':warning:'
                },
                'email': {
                    'enabled': False,
                    'smtp_server': 'localhost',
                    'smtp_port': 587,
                    'from_addr': '',
                    'to_addrs': [],
                    'username': '',
                    'password': '',
                    'use_tls': True
                },
                'console_enabled': True
            },
            'deduplication_enabled': True,
            'deduplication_window_minutes': 15
        },
        
        'dashboard': {
            'host': '0.0.0.0',
            'port': 8501,
            'title': 'API Visualizer Dashboard',
            'refresh_interval': 30,
            'max_events_display': 1000
        },
        
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_path': None,
            'max_file_size': '10MB',
            'backup_count': 5
        }
    }
