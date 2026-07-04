"""
tasks/file_task.py

FILE TASK tools — real local file system operations.
Identical logic to before; ADK will wrap these as tools instead of Groq.

IMPORTANT FOR ADK: tool functions should have clear type hints and a
docstring — ADK reads these to generate the tool's schema automatically,
similar to how we manually wrote TOOL_DEFINITIONS for Groq. With ADK,
that boilerplate goes away.
"""

import os
import shutil
import json
from datetime import datetime

WORKSPACE_DIR = "data/file_task_workspace"
ARCHIVE_DIR = "data/file_task_archive"

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)


def create_file(filename: str, content: str) -> str:
    """Creates a new file with the given content inside the workspace.

    Args:
        filename: Name of the file to create, e.g. "notes.txt".
        content: The text content to write into the file.

    Returns:
        A JSON string describing the result of the operation.
    """
    filepath = os.path.join(WORKSPACE_DIR, filename)

    if os.path.exists(filepath):
        return json.dumps({"error": f"File '{filename}' already exists. Use update_file instead."})

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return json.dumps({
        "success": True,
        "action": "created",
        "filename": filename,
        "size_bytes": os.path.getsize(filepath)
    })


def update_file(filename: str, new_content: str, mode: str = "overwrite") -> str:
    """Updates an existing file's content.

    Args:
        filename: The file to update; must already exist.
        new_content: The text to write.
        mode: "overwrite" replaces all content, "append" adds to the end.

    Returns:
        A JSON string describing the result of the operation.
    """
    filepath = os.path.join(WORKSPACE_DIR, filename)

    if not os.path.exists(filepath):
        return json.dumps({"error": f"File '{filename}' does not exist. Use create_file instead."})

    write_mode = "a" if mode == "append" else "w"
    with open(filepath, write_mode, encoding="utf-8") as f:
        f.write(("\n" + new_content) if mode == "append" else new_content)

    return json.dumps({
        "success": True,
        "action": f"updated ({mode})",
        "filename": filename,
        "size_bytes": os.path.getsize(filepath)
    })


def archive_file(filename: str) -> str:
    """Moves a file from the active workspace into the archive folder.

    Args:
        filename: The file currently in the workspace to archive.

    Returns:
        A JSON string describing the result of the operation.
    """
    filepath = os.path.join(WORKSPACE_DIR, filename)

    if not os.path.exists(filepath):
        return json.dumps({"error": f"File '{filename}' not found in workspace."})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(filename)
    archived_name = f"{name}_{timestamp}{ext}"
    archived_path = os.path.join(ARCHIVE_DIR, archived_name)

    shutil.move(filepath, archived_path)

    return json.dumps({
        "success": True,
        "action": "archived",
        "original_filename": filename,
        "archived_as": archived_name
    })


def list_files() -> str:
    """Lists all files currently in the active workspace.

    Returns:
        A JSON string listing each file and its size.
    """
    files = os.listdir(WORKSPACE_DIR)
    if not files:
        return json.dumps({"message": "The workspace is currently empty."})

    file_details = [
        {"filename": f, "size_bytes": os.path.getsize(os.path.join(WORKSPACE_DIR, f))}
        for f in files
    ]
    return json.dumps({"files": file_details})
