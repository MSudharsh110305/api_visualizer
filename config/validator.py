"""
Configuration validation with detailed error messages
"""

import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass

class ConfigValidator:
    """Validates configuration dictionaries"""
    
    def validate(self, config: Dict[str, Any]) -> None:
        """
        Validate complete configuration
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []
        
        # Validate storage config
        if 'storage' in config:
            errors.extend(self._validate_storage(config['storage']))
        
        # Validate alerting config
        if 'alerting' in config:
            errors.extend(self._validate_alerting(config['alerting']))
        
        # Validate instrumentation config
        if 'instrumentation' in config:
            errors.extend(self._validate_instrumentation(config['instrumentation']))
        
        # Validate dashboard config
        if 'dashboard' in config:
            errors.extend(self._validate_dashboard(config['dashboard']))
        
        # Validate logging config
        if 'logging' in config:
            errors.extend(self._validate_logging(config['logging']))
        
        if errors:
            raise ConfigValidationError(f"Configuration validation failed:\n" + "\n".join(errors))
    
    def _validate_storage(self, storage_config: Dict[str, Any]) -> List[str]:
        """Validate storage configuration"""
        errors = []
        
        # Check database path
        db_path = storage_config.get('db_path')
        if db_path:
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir)
                except Exception as e:
                    errors.append(f"Cannot create database directory {db_dir}: {e}")
        
        # Validate retention days
        retention_days = storage_config.get('retention_days', 30)
        if not isinstance(retention_days, int) or retention_days < 1:
            errors.append("storage.retention_days must be a positive integer")
        
        return errors
    
    def _validate_alerting(self, alerting_config: Dict[str, Any]) -> List[str]:
        """Validate alerting configuration"""
        errors = []
        
        # Validate thresholds
        thresholds = alerting_config.get('thresholds', {})
        
        for threshold_name, threshold_config in thresholds.items():
            if not isinstance(threshold_config, dict):
                continue
                
            value = threshold_config.get('value')
            if value is not None and not isinstance(value, (int, float)):
                errors.append(f"alerting.thresholds.{threshold_name}.value must be a number")
            
            if threshold_name == 'latency_ms' and value is not None and value < 0:
                errors.append("alerting.thresholds.latency_ms.value cannot be negative")
            
            if threshold_name == 'error_rate_percent' and value is not None:
                if value < 0 or value > 100:
                    errors.append("alerting.thresholds.error_rate_percent.value must be between 0 and 100")
        
        # Validate notifications
        notifications = alerting_config.get('notifications', {})
        
        # Validate Slack config
        slack_config = notifications.get('slack', {})
        if slack_config.get('enabled', False):
            webhook_url = slack_config.get('webhook_url')
            if not webhook_url or not webhook_url.startswith('https://hooks.slack.com/'):
                errors.append("Valid Slack webhook URL required when Slack notifications are enabled")
        
        # Validate email config
        email_config = notifications.get('email', {})
        if email_config.get('enabled', False):
            required_fields = ['smtp_server', 'from_addr', 'to_addrs']
            for field in required_fields:
                if not email_config.get(field):
                    errors.append(f"alerting.notifications.email.{field} is required when email notifications are enabled")
            
            smtp_port = email_config.get('smtp_port')
            if smtp_port and (not isinstance(smtp_port, int) or smtp_port < 1 or smtp_port > 65535):
                errors.append("alerting.notifications.email.smtp_port must be a valid port number")
        
        return errors
    
    def _validate_instrumentation(self, instr_config: Dict[str, Any]) -> List[str]:
        """Validate instrumentation configuration"""
        errors = []
        
        # Validate sample rate
        sample_rate = instr_config.get('sample_rate', 1.0)
        if not isinstance(sample_rate, (int, float)) or sample_rate < 0 or sample_rate > 1:
            errors.append("instrumentation.sample_rate must be between 0 and 1")
        
        # Validate transport type
        transport_type = instr_config.get('transport_type', 'memory')
        if transport_type not in ['memory', 'udp', 'redis']:
            errors.append("instrumentation.transport_type must be one of: memory, udp, redis")
        
        # Validate batch size
        batch_size = instr_config.get('batch_size', 100)
        if not isinstance(batch_size, int) or batch_size < 1:
            errors.append("instrumentation.batch_size must be a positive integer")
        
        return errors
    
    def _validate_dashboard(self, dashboard_config: Dict[str, Any]) -> List[str]:
        """Validate dashboard configuration"""
        errors = []
        
        # Validate port
        port = dashboard_config.get('port', 8501)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("dashboard.port must be a valid port number")
        
        # Validate refresh interval
        refresh_interval = dashboard_config.get('refresh_interval', 30)
        if not isinstance(refresh_interval, int) or refresh_interval < 1:
            errors.append("dashboard.refresh_interval must be a positive integer")
        
        return errors
    
    def _validate_logging(self, logging_config: Dict[str, Any]) -> List[str]:
        """Validate logging configuration"""
        errors = []
        
        # Validate log level
        level = logging_config.get('level', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level.upper() not in valid_levels:
            errors.append(f"logging.level must be one of: {', '.join(valid_levels)}")
        
        # Validate file path
        file_path = logging_config.get('file_path')
        if file_path:
            log_dir = os.path.dirname(os.path.abspath(file_path))
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except Exception as e:
                    errors.append(f"Cannot create log directory {log_dir}: {e}")
        
        return errors
