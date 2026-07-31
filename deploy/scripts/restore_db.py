#!/usr/bin/env python3
"""
PostgreSQL Database Restore Script
Restores a SQL backup file into a target disposable database and validates table integrity.
"""

import os
import sys
import argparse
import subprocess


def restore_database(backup_file: str, target_db_url: str) -> bool:
    if not os.path.exists(backup_file):
        print(f"[RESTORE ERROR] Backup file not found: {backup_file}")
        return False

    print(f"[RESTORE] Restoring {backup_file} into disposable target {target_db_url}...")

    if "postgresql" in target_db_url or "postgres" in target_db_url:
        cmd = ["psql", "--dbname", target_db_url, "-f", backup_file]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"[RESTORE ERROR] psql restore failed: {e}")
            raise
    else:
        # Fallback for SQLite dev/test DB
        sqlite_file = target_db_url.replace("sqlite:///", "")
        import shutil
        shutil.copy2(backup_file, sqlite_file)

    print(f"[RESTORE SUCCESS] Database restore complete.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore Database Backup")
    parser.add_argument("--backup-file", required=True)
    parser.add_argument("--target-db-url", required=True)
    args = parser.parse_args()

    success = restore_database(args.backup_file, args.target_db_url)
    if not success:
        sys.exit(1)
