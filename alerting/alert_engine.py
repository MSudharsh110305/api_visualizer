import logging
import time
from datetime import datetime, timedelta
from storage import get_database
from alerting.notifier import SlackNotifier, EmailNotifier, ConsoleNotifier

logger = logging.getLogger(__name__)

class AlertEngine:
    """
    Periodically queries metrics database and sends alerts based on config thresholds
    """

    def __init__(self, config):
        """
        Args:
            config (dict): Configuration dictionary for alert rules and notification channels
        """
        self.config = config or {}
        self.db = get_database(config.get('db_path'))
        self.notifiers = self._init_notifiers(config.get('notifications', {}))
        self.alerts_sent = set()  # to avoid duplicate alerts in current session
    
    def _init_notifiers(self, notif_config):
        notifiers = []
        if notif_config.get('slack', {}).get('enabled', False):
            notifiers.append(SlackNotifier(notif_config['slack']))
        if notif_config.get('email', {}).get('enabled', False):
            notifiers.append(EmailNotifier(notif_config['email']))
        if notif_config.get('console', {}).get('enabled', True):
            notifiers.append(ConsoleNotifier())
        return notifiers

    def _send_alert(self, alert_type, message, severity='warning', metadata=None):
        """
        Send alert notification to all configured channels.
        Deduplicate alerts by a simple hash of alert_type and message for session.
        """
        alert_id = f"{alert_type}:{message}"
        if alert_id in self.alerts_sent:
            # Already sent alert in this run to avoid spamming
            return
        self.alerts_sent.add(alert_id)

        logger.info(f"Sending alert [{severity}] {alert_type}: {message}")
        for notifier in self.notifiers:
            try:
                notifier.send(message=message, alert_type=alert_type, severity=severity, metadata=metadata)
            except Exception as e:
                logger.error(f"Notifier {notifier} failed: {e}")

    def check_latency_threshold(self):
        """
        Check if average or p95 latency exceeds configured threshold
        """
        latency_cfg = self.config.get('thresholds', {}).get('latency_ms', {})
        threshold_ms = latency_cfg.get('value', 1000)
        time_window = latency_cfg.get('time_window', '5m')

        avg_latency = self._get_avg_latency(time_window)
        if avg_latency is None:
            return
        
        if avg_latency > threshold_ms:
            self._send_alert(
                alert_type='High Latency',
                message=f"Average latency {avg_latency:.1f}ms exceeds threshold {threshold_ms}ms over {time_window}",
                severity='critical'
            )

    def check_error_rate(self):
        """
        Check if error rate exceeds configured threshold
        """
        error_cfg = self.config.get('thresholds', {}).get('error_rate_percent', {})
        threshold_rate = error_cfg.get('value', 5.0)
        time_window = error_cfg.get('time_window', '10m')

        error_rate = self._get_error_rate(time_window)
        if error_rate is None:
            return
        
        if error_rate > threshold_rate:
            self._send_alert(
                alert_type='High Error Rate',
                message=f"Error rate {error_rate:.1f}% exceeds threshold {threshold_rate}% over {time_window}",
                severity='critical'
            )

    def check_traffic_spike(self):
        """
        Check for unusual spike in traffic compared to recent average
        """
        traffic_cfg = self.config.get('thresholds', {}).get('traffic_spike_percent', {})
        threshold_percent = traffic_cfg.get('value', 100)
        time_window = traffic_cfg.get('time_window', '5m')

        current_rate = self._get_request_rate(time_window)
        baseline_rate = self._get_request_rate('1h')

        if current_rate is None or baseline_rate is None or baseline_rate == 0:
            return
        
        increase = ((current_rate - baseline_rate) / baseline_rate) * 100
        if increase > threshold_percent:
            self._send_alert(
                alert_type='Traffic Spike',
                message=f"Traffic rate increased by {increase:.1f}% over baseline in {time_window}",
                severity='warning'
            )

    def _get_avg_latency(self, time_window):
        # Example: Convert '5m' to minutes integer
        minutes = self._parse_time_window_minutes(time_window)
        cutoff = datetime.now() - timedelta(minutes=minutes)
        conn = self.db.get_connection()
        cursor = conn.execute("""
            SELECT AVG(latency_ms) FROM api_events WHERE timestamp > ?
        """, (cutoff.timestamp(),))
        result = cursor.fetchone()
        return result[0] if result else None

    def _get_error_rate(self, time_window):
        minutes = self._parse_time_window_minutes(time_window)
        cutoff = datetime.now() - timedelta(minutes=minutes)
        conn = self.db.get_connection()
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) as errors
            FROM api_events
            WHERE timestamp > ?
        """, (cutoff.timestamp(),))
        result = cursor.fetchone()
        if not result or result[0] == 0:
            return 0.0
        return (result[1] or 0) / result[0] * 100

    def _get_request_rate(self, time_window):
        minutes = self._parse_time_window_minutes(time_window)
        cutoff = datetime.now() - timedelta(minutes=minutes)
        conn = self.db.get_connection()
        cursor = conn.execute("""
            SELECT COUNT(*) FROM api_events WHERE timestamp > ?
        """, (cutoff.timestamp(),))
        result = cursor.fetchone()
        if not result:
            return 0
        return result[0] / minutes  # Requests per minute

    def _parse_time_window_minutes(self, window_str):
        if window_str.endswith('m'):
            return int(window_str[:-1])
        elif window_str.endswith('h'):
            return int(window_str[:-1]) * 60
        else:
            try:
                return int(window_str)
            except:
                return 5  # default 5 minutes

    def run_checks(self):
        """
        Run all configured checks sequentially
        """
        self.check_latency_threshold()
        self.check_error_rate()
        self.check_traffic_spike()
