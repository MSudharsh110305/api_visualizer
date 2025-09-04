"""
Configuration data models with validation and type safety
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import logging

@dataclass
class InstrumentationConfig:
    """Configuration for the instrumentation module"""
    enabled: bool = True
    sample_rate: float = 1.0
    exclude_urls: List[str] = field(default_factory=lambda: ['/health', '/ping', '/metrics'])
    include_urls: List[str] = field(default_factory=list)
    transport_type: str = 'memory'
    batch_size: int = 100
    batch_timeout: float = 5.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstrumentationConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class StorageConfig:
    """Configuration for the storage module"""
    db_path: str = 'api_visualizer.db'
    connection_pool_size: int = 5
    retention_days: int = 30
    auto_vacuum: bool = True
    backup_enabled: bool = False
    backup_interval_hours: int = 24
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StorageConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class NotificationConfig:
    """Base notification configuration"""
    enabled: bool = False

@dataclass
class SlackConfig(NotificationConfig):
    """Slack notification configuration"""
    webhook_url: str = ''
    channel: str = '#alerts'
    username: str = 'API-Visualizer'
    icon_emoji: str = ':warning:'

@dataclass
class EmailConfig(NotificationConfig):
    """Email notification configuration"""
    smtp_server: str = 'localhost'
    smtp_port: int = 587
    from_addr: str = ''
    to_addrs: List[str] = field(default_factory=list)
    username: str = ''
    password: str = ''
    use_tls: bool = True

@dataclass
class ThresholdConfig:
    """Alert threshold configuration"""
    enabled: bool = True
    value: float = 0
    time_window: str = '5m'
    severity: str = 'warning'

@dataclass
class AlertingConfig:
    """Configuration for the alerting module"""
    check_interval: int = 60
    
    # Thresholds
    latency_ms: ThresholdConfig = field(default_factory=lambda: ThresholdConfig(
        value=1000, severity='critical'
    ))
    error_rate_percent: ThresholdConfig = field(default_factory=lambda: ThresholdConfig(
        value=5.0, time_window='10m', severity='critical'
    ))
    traffic_spike_percent: ThresholdConfig = field(default_factory=lambda: ThresholdConfig(
        value=100, severity='warning'
    ))
    
    # Notifications
    slack: SlackConfig = field(default_factory=SlackConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    console_enabled: bool = True
    
    # Deduplication
    deduplication_enabled: bool = True
    deduplication_window_minutes: int = 15
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertingConfig':
        config = cls()
        
        # Handle thresholds
        thresholds = data.get('thresholds', {})
        if 'latency_ms' in thresholds:
            config.latency_ms = ThresholdConfig(**thresholds['latency_ms'])
        if 'error_rate_percent' in thresholds:
            config.error_rate_percent = ThresholdConfig(**thresholds['error_rate_percent'])
        if 'traffic_spike_percent' in thresholds:
            config.traffic_spike_percent = ThresholdConfig(**thresholds['traffic_spike_percent'])
        
        # Handle notifications
        notifications = data.get('notifications', {})
        if 'slack' in notifications:
            config.slack = SlackConfig(**notifications['slack'])
        if 'email' in notifications:
            config.email = EmailConfig(**notifications['email'])
        
        # Handle other fields
        for key in ['check_interval', 'console_enabled', 'deduplication_enabled', 'deduplication_window_minutes']:
            if key in data:
                setattr(config, key, data[key])
        
        return config

@dataclass
class DashboardConfig:
    """Configuration for the dashboard module"""
    host: str = '0.0.0.0'
    port: int = 8501
    title: str = 'API Visualizer Dashboard'
    refresh_interval: int = 30
    max_events_display: int = 1000
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = None
    max_file_size: str = '10MB'
    backup_count: int = 5
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class APIVisualizerConfig:
    """Main configuration class containing all module configurations"""
    environment: str = 'development'
    service_name: str = 'api-visualizer'
    
    # Module configurations
    instrumentation: InstrumentationConfig = field(default_factory=InstrumentationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIVisualizerConfig':
        """Create configuration from dictionary"""
        config = cls()
        
        # Basic fields
        config.environment = data.get('environment', 'development')
        config.service_name = data.get('service_name', 'api-visualizer')
        
        # Module configurations
        if 'instrumentation' in data:
            config.instrumentation = InstrumentationConfig.from_dict(data['instrumentation'])
        if 'storage' in data:
            config.storage = StorageConfig.from_dict(data['storage'])
        if 'alerting' in data:
            config.alerting = AlertingConfig.from_dict(data['alerting'])
        if 'dashboard' in data:
            config.dashboard = DashboardConfig.from_dict(data['dashboard'])
        if 'logging' in data:
            config.logging = LoggingConfig.from_dict(data['logging'])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'environment': self.environment,
            'service_name': self.service_name,
            'instrumentation': self.instrumentation.__dict__,
            'storage': self.storage.__dict__,
            'alerting': self.alerting.__dict__,
            'dashboard': self.dashboard.__dict__,
            'logging': self.logging.__dict__
        }
    
    def setup_logging(self):
        """Setup logging based on configuration"""
        level = getattr(logging, self.logging.level.upper(), logging.INFO)
        
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(self.logging.format))
        handlers.append(console_handler)
        
        # File handler if specified
        if self.logging.file_path:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.logging.file_path,
                maxBytes=self._parse_size(self.logging.max_file_size),
                backupCount=self.logging.backup_count
            )
            file_handler.setFormatter(logging.Formatter(self.logging.format))
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=level,
            handlers=handlers,
            force=True
        )
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
