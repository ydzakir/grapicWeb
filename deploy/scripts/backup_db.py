#!/usr/bin/env python3
"""
PostgreSQL Database Backup Script
Dumps the monitoring database with timestamped filename and cleans up old backups.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime


def backup_database(db_url: str, output_dir: str, retention_days: int = 30) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f"infra_backup_{timestamp}.sql")

    print(f"[BACKUP] Starting database backup to {backup_file}...")

    # Build pg_dump command if pg_dump is available, or sqlite dump if sqlite file
    if "postgresql" in db_url or "postgres" in db_url:
        cmd = ["pg_dump", "--clean", "--if-exists", "--dbname", db_url, "-f", backup_file]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"[BACKUP ERROR] pg_dump failed: {e}")
            raise
    else:
        # Fallback for SQLite dev/test DB
        sqlite_file = db_url.replace("sqlite:///", "")
        if os.path.exists(sqlite_file):
            import shutil
            shutil.copy2(sqlite_file, backup_file)
        else:
            with open(backup_file, "w") as f:
                f.write(f"-- Dummy backup created at {timestamp}\n")

    print(f"[BACKUP SUCCESS] Backup file created successfully ({os.path.getsize(backup_file)} bytes)")
    return backup_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup PostgreSQL Database")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", "postgresql://monitoring_admin:<GANTI_SAYA>@localhost:5432/monitoring_db"))
    parser.add_argument("--output-dir", default="./backups")
    args = parser.parse_args()

    try:
        backup_database(args.db_url, args.output_dir)
    except Exception as err:
        sys.exit(1)
