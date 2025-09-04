import threading
import time
import logging

logger = logging.getLogger(__name__)

class AlertScheduler:
    """
    Runs AlertEngine checks periodically in a background thread
    """
    def __init__(self, alert_engine, interval_seconds=60):
        self.alert_engine = alert_engine
        self.interval = interval_seconds
        self.thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        if self.thread and self.thread.is_alive():
            logger.warning("AlertScheduler already running")
            return
        
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("AlertScheduler started")
    
    def stop(self):
        if not self.thread:
            return
        self._stop_event.set()
        self.thread.join()
        logger.info("AlertScheduler stopped")
    
    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.alert_engine.run_checks()
            except Exception as e:
                logger.error(f"AlertScheduler error: {e}")
            time.sleep(self.interval)
