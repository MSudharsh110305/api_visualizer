"""
API Visualizer Configuration Module
Centralized configuration management with validation and environment support
"""

from .loader import ConfigLoader
from .models import (
    APIVisualizerConfig,
    InstrumentationConfig,
    StorageConfig,
    AlertingConfig,
    DashboardConfig
)

# Global configuration instance
_config = None

def load_config(config_path=None, environment=None):
    """
    Load configuration from file or environment
    
    Args:
        config_path (str): Path to configuration file
        environment (str): Environment name (dev, staging, prod)
    
    Returns:
        APIVisualizerConfig: Loaded and validated configuration
    """
    global _config
    
    if _config is None:
        loader = ConfigLoader()
        _config = loader.load(config_path=config_path, environment=environment)
    
    return _config

def get_config():
    """Get the current configuration instance"""
    global _config
    
    if _config is None:
        _config = load_config()
    
    return _config

def reload_config(config_path=None, environment=None):
    """Force reload configuration"""
    global _config
    _config = None
    return load_config(config_path=config_path, environment=environment)

__all__ = [
    'load_config',
    'get_config', 
    'reload_config',
    'APIVisualizerConfig',
    'InstrumentationConfig',
    'StorageConfig',
    'AlertingConfig',
    'DashboardConfig'
]
