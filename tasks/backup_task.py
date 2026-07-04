"""
tasks/backup_task.py

BACKUP TASK — data preservation and directory management.
Compresses files/folders into a zip archive and copies them between
directories, simulating a real backup workflow.
"""

import os
import shutil
import json
from datetime import datetime

# Backups are taken FROM the existing task workspaces (file_task, report_task)
# and stored INTO a dedicated backups folder — simulating a real backup flow
# where you preserve outputs from other tasks.
SOURCE_DIRS = {
    "file": "data/file_task_workspace",
    "report": "data/report_task_workspace",
}
BACKUP_DIR = "data/backup_task_workspace"
os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup(source: str, backup_name: str = "") -> str:
    """Compresses a task workspace into a timestamped zip archive.

    Args:
        source: Which workspace to back up — "file" or "report".
        backup_name: Optional custom name for the backup archive
            (without extension). If not given, a timestamped name is used.

    Returns:
        A JSON string describing the result of the operation.
    """
    if source not in SOURCE_DIRS:
        return json.dumps({
            "error": f"Unknown source '{source}'. Valid options: {list(SOURCE_DIRS.keys())}"
        })

    source_dir = SOURCE_DIRS[source]

    if not os.path.exists(source_dir) or not os.listdir(source_dir):
        return json.dumps({"error": f"Source directory '{source_dir}' is empty or doesn't exist."})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = backup_name.strip() if backup_name.strip() else f"{source}_backup_{timestamp}"
    archive_path_no_ext = os.path.join(BACKUP_DIR, archive_name)

    try:
        # shutil.make_archive adds the .zip extension automatically
        final_path = shutil.make_archive(archive_path_no_ext, "zip", source_dir)

        return json.dumps({
            "success": True,
            "action": "backup_created",
            "source": source,
            "archive_path": final_path,
            "size_bytes": os.path.getsize(final_path)
        })

    except Exception as e:
        return json.dumps({"error": f"Failed to create backup: {str(e)}"})


def restore_backup(backup_filename: str, destination: str) -> str:
    """Extracts a backup archive into a destination workspace.

    Args:
        backup_filename: The zip filename to restore, e.g. "file_backup_20260628_140000.zip".
        destination: Which workspace to restore into — "file" or "report".

    Returns:
        A JSON string describing the result of the operation.
    """
    if destination not in SOURCE_DIRS:
        return json.dumps({
            "error": f"Unknown destination '{destination}'. Valid options: {list(SOURCE_DIRS.keys())}"
        })

    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.exists(backup_path):
        return json.dumps({"error": f"Backup file '{backup_filename}' not found."})

    destination_dir = SOURCE_DIRS[destination]
    os.makedirs(destination_dir, exist_ok=True)

    try:
        shutil.unpack_archive(backup_path, destination_dir, "zip")

        return json.dumps({
            "success": True,
            "action": "backup_restored",
            "backup_filename": backup_filename,
            "restored_to": destination_dir
        })

    except Exception as e:
        return json.dumps({"error": f"Failed to restore backup: {str(e)}"})


def list_backups() -> str:
    """Lists all backup archives currently stored.

    Returns:
        A JSON string listing each backup file and its size.
    """
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")]
    if not files:
        return json.dumps({"message": "No backups have been created yet."})

    file_details = [
        {"filename": f, "size_bytes": os.path.getsize(os.path.join(BACKUP_DIR, f))}
        for f in files
    ]
    return json.dumps({"backups": file_details})