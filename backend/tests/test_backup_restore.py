import os
import sys
import tempfile
import pytest

# Ensure deploy package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from deploy.scripts.backup_db import backup_database
from deploy.scripts.restore_db import restore_database
from models.node import Node


@pytest.mark.asyncio
async def test_backup_and_restore_workflow(db_session):
    """Test creating a database backup file and restoring it into a disposable database."""
    # Insert sample record
    node = Node(
        name="SERVER-TEST-BACKUP-01",
        type="physical_server",
        status="up",
        review_status="approved",
        lifecycle_status="active",
    )
    db_session.add(node)
    await db_session.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create backup
        backup_file = backup_database(
            db_url="sqlite:///test_backup.db",
            output_dir=tmp_dir,
        )
        assert os.path.exists(backup_file)
        assert os.path.getsize(backup_file) > 0

        # Restore to disposable database path
        disposable_db = os.path.join(tmp_dir, "disposable_restore.db")
        success = restore_database(
            backup_file=backup_file,
            target_db_url=f"sqlite:///{disposable_db}",
        )
        assert success is True
        assert os.path.exists(disposable_db)
