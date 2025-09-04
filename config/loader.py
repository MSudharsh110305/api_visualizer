"""
Configuration loader with support for YAML, TOML, and environment variables
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from .models import APIVisualizerConfig
from .validator import ConfigValidator
from .defaults import get_default_config

logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    Loads and validates configuration from multiple sources
    """
    
    def __init__(self):
        self.validator = ConfigValidator()
    
    def load(self, config_path: Optional[str] = None, 
             environment: Optional[str] = None) -> APIVisualizerConfig:
        """
        Load configuration with environment and validation support
        
        Args:
            config_path: Path to config file
            environment: Target environment (dev, staging, prod)
            
        Returns:
            Validated APIVisualizerConfig instance
        """
        # Get environment
        env = environment or os.getenv('API_VISUALIZER_ENV', 'development')
        
        # Start with defaults
        config_dict = get_default_config()
        
        # Load from file if provided
        if config_path or self._find_config_file():
            file_path = config_path or self._find_config_file()
            file_config = self._load_from_file(file_path)
            config_dict = self._merge_configs(config_dict, file_config)
        
        # Load environment-specific overrides
        env_config = self._load_environment_overrides(env)
        if env_config:
            config_dict = self._merge_configs(config_dict, env_config)
        
        # Load from environment variables
        env_var_config = self._load_from_env_vars()
        config_dict = self._merge_configs(config_dict, env_var_config)
        
        # Validate and create config object
        self.validator.validate(config_dict)
        
        return APIVisualizerConfig.from_dict(config_dict)
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations"""
        possible_paths = [
            'config.yaml',
            'config.yml', 
            'config/config.yaml',
            'config/config.yml',
            os.path.expanduser('~/.api_visualizer/config.yaml'),
            '/etc/api_visualizer/config.yaml'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found config file: {path}")
                return path
        
        return None
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or TOML file"""
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    return yaml.safe_load(f) or {}
                elif file_path.endswith('.toml'):
                    try:
                        import toml
                        return toml.load(f)
                    except ImportError:
                        logger.error("toml package not installed for .toml config files")
                        return {}
                else:
                    logger.warning(f"Unsupported config file format: {file_path}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to load config from {file_path}: {e}")
            return {}
    
    def _load_environment_overrides(self, environment: str) -> Dict[str, Any]:
        """Load environment-specific configuration overrides"""
        env_file_patterns = [
            f'config.{environment}.yaml',
            f'config.{environment}.yml',
            f'config/{environment}.yaml',
            f'config/{environment}.yml'
        ]
        
        for pattern in env_file_patterns:
            if os.path.exists(pattern):
                logger.info(f"Loading environment config: {pattern}")
                return self._load_from_file(pattern)
        
        return {}
    
    def _load_from_env_vars(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        # Define environment variable mappings
        env_mappings = {
            'API_VISUALIZER_DB_PATH': ['storage', 'db_path'],
            'API_VISUALIZER_LOG_LEVEL': ['logging', 'level'],
            'API_VISUALIZER_SLACK_WEBHOOK': ['alerting', 'notifications', 'slack', 'webhook_url'],
            'API_VISUALIZER_SMTP_SERVER': ['alerting', 'notifications', 'email', 'smtp_server'],
            'API_VISUALIZER_SMTP_PORT': ['alerting', 'notifications', 'email', 'smtp_port'],
            'API_VISUALIZER_EMAIL_FROM': ['alerting', 'notifications', 'email', 'from_addr'],
            'API_VISUALIZER_EMAIL_TO': ['alerting', 'notifications', 'email', 'to_addrs'],
            'API_VISUALIZER_LATENCY_THRESHOLD': ['alerting', 'thresholds', 'latency_ms', 'value'],
            'API_VISUALIZER_ERROR_THRESHOLD': ['alerting', 'thresholds', 'error_rate_percent', 'value'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert value to appropriate type
                converted_value = self._convert_env_value(value, config_path)
                self._set_nested_value(config, config_path, converted_value)
        
        return config
    
    def _convert_env_value(self, value: str, config_path: list) -> Any:
        """Convert environment variable string to appropriate type"""
        # Handle special cases based on config path
        if 'port' in config_path:
            return int(value)
        elif 'enabled' in config_path:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif 'to_addrs' in config_path:
            return [addr.strip() for addr in value.split(',')]
        elif any(threshold in config_path for threshold in ['threshold', 'value']):
            try:
                return float(value)
            except ValueError:
                return value
        else:
            return value
    
    def _set_nested_value(self, config: Dict[str, Any], path: list, value: Any):
        """Set a nested configuration value"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
