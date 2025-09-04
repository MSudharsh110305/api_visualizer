"""
Database migration system for API Visualizer
"""

import sqlite3
import logging
from typing import List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class Migration:
    """Represents a single database migration"""
    
    def __init__(self, version: int, description: str, up_func: Callable[[sqlite3.Connection], None]):
        self.version = version
        self.description = description
        self.up_func = up_func
        self.created_at = datetime.now()

class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.migrations = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations"""
        
        # Migration 1: Add indexes for better performance
        def migration_001_add_indexes(conn: sqlite3.Connection):
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_api_events_timestamp_service ON api_events(timestamp, service_name)",
                "CREATE INDEX IF NOT EXISTS idx_api_events_latency ON api_events(latency_ms)",
                "CREATE INDEX IF NOT EXISTS idx_dependencies_last_seen ON service_dependencies(last_seen)"
            ]
            for index_sql in indexes:
                conn.execute(index_sql)
        
        self.migrations.append(Migration(1, "Add performance indexes", migration_001_add_indexes))
        
        # Migration 2: Add user-agent and IP tracking
        def migration_002_add_tracking_fields(conn: sqlite3.Connection):
            try:
                conn.execute("ALTER TABLE api_events ADD COLUMN user_agent TEXT")
                conn.execute("ALTER TABLE api_events ADD COLUMN client_ip TEXT")
            except sqlite3.OperationalError:
                # Columns might already exist
                pass
        
        self.migrations.append(Migration(2, "Add user agent and IP tracking", migration_002_add_tracking_fields))
        
        # Migration 3: Add alerting table
        def migration_003_add_alerting(conn: sqlite3.Connection):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME,
                    metadata TEXT,  -- JSON
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_triggered_at ON alerts(triggered_at)")
        
        self.migrations.append(Migration(3, "Add alerting system", migration_003_add_alerting))
    
    def _create_migration_table(self):
        """Create migration tracking table"""
        conn = self.db.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def get_current_version(self) -> int:
        """Get current database schema version"""
        self._create_migration_table()
        
        conn = self.db.get_connection()
        cursor = conn.execute("SELECT MAX(version) FROM schema_migrations")
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        current_version = self.get_current_version()
        return [m for m in self.migrations if m.version > current_version]
    
    def migrate(self) -> int:
        """Apply all pending migrations"""
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return 0
        
        conn = self.db.get_connection()
        applied_count = 0
        
        for migration in pending:
            try:
                with conn:  # Transaction
                    logger.info(f"Applying migration {migration.version}: {migration.description}")
                    
                    # Apply the migration
                    migration.up_func(conn)
                    
                    # Record the migration
                    conn.execute(
                        "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                        (migration.version, migration.description)
                    )
                    
                    applied_count += 1
                    logger.info(f"Successfully applied migration {migration.version}")
                    
            except Exception as e:
                logger.error(f"Failed to apply migration {migration.version}: {e}")
                raise
        
        logger.info(f"Applied {applied_count} migrations successfully")
        return applied_count
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get history of applied migrations"""
        self._create_migration_table()
        
        conn = self.db.get_connection()
        cursor = conn.execute("""
            SELECT version, description, applied_at 
            FROM schema_migrations 
            ORDER BY version
        """)
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
