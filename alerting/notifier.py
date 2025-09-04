import logging
import requests
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

class BaseNotifier:
    def send(self, message, alert_type=None, severity=None, metadata=None):
        raise NotImplementedError("Send method not implemented")

class SlackNotifier(BaseNotifier):
    def __init__(self, config):
        self.webhook_url = config.get('webhook_url')
        
    def send(self, message, alert_type=None, severity=None, metadata=None):
        if not self.webhook_url:
            logger.error("Slack webhook URL not configured")
            return
        
        payload = {
            "text": f"*[{alert_type}] {severity.upper()}*\n{message}"
        }
        try:
            res = requests.post(self.webhook_url, json=payload, timeout=5)
            if res.status_code != 200:
                logger.error(f"Slack notification failed: {res.status_code}, {res.text}")
        except Exception as e:
            logger.error(f"Slack notification exception: {e}")

class EmailNotifier(BaseNotifier):
    def __init__(self, config):
        self.smtp_server = config.get('smtp_server', 'localhost')
        self.smtp_port = config.get('smtp_port', 25)
        self.from_addr = config.get('from_addr')
        self.to_addrs = config.get('to_addrs', [])
        self.username = config.get('username')
        self.password = config.get('password')
        self.use_tls = config.get('use_tls', False)
    
    def send(self, message, alert_type=None, severity=None, metadata=None):
        if not self.from_addr or not self.to_addrs:
            logger.error("Email from/to addresses not configured")
            return
        
        subject = f"[{severity.upper()}] {alert_type} Alert"
        msg = MIMEText(message)
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Subject"] = subject
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            server.quit()
            logger.info("Email alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

class ConsoleNotifier(BaseNotifier):
    def send(self, message, alert_type=None, severity=None, metadata=None):
        print(f"[{severity.upper()}] {alert_type}: {message}")
