import json
from google.adk import Agent


import inspect

from tasks.file_task import create_file, update_file, archive_file, list_files
from db.mongo import log_task_execution, get_recent_task_logs, get_failed_tasks
from db.vector_store import store_memory, search_memory
from tasks.notification_task import send_slack_notification
from tasks.email_task import send_email
from tasks.report_task import generate_csv_report, generate_pdf_report, generate_text_report, list_reports
from tasks.backup_task import create_backup, restore_backup, list_backups
from . import instrumentation 
from tasks.pipeline_executor import execute_pipeline


def _with_logging(task_type: str, tool_name: str, raw_function):
    def wrapped(**kwargs) -> str:
        # print(f"DEBUG: {tool_name} called with kwargs = {kwargs}")
        try:
            result = raw_function(**kwargs)
            result_json = json.loads(result)
            status = "failure" if "error" in result_json else "success"
            error_msg = result_json.get("error")
        except Exception as e:
            result = json.dumps({"error": str(e)})
            status = "failure"
            error_msg = str(e)

        log_id = log_task_execution(
            task_type=task_type,
            tool_name=tool_name,
            arguments=kwargs,
            status=status,
            result=result,
            error=error_msg
        )

        memory_text = (
            f"Task type: {task_type}. Tool: {tool_name}. "
            f"Arguments: {kwargs}. Status: {status}. Result: {result}"
        )
        store_memory(
            text=memory_text,
            metadata={"task_type": task_type, "status": status, "tool_name": tool_name},
            memory_id=log_id
        )

        return result

    wrapped.__name__ = tool_name
    wrapped.__doc__ = raw_function.__doc__
    wrapped.__signature__ = inspect.signature(raw_function)  # ← THE FIX: copy the real signature
    return wrapped


# ── MEMORY / SEARCH TOOLS (not logged themselves, to avoid recursive noise) ──

def search_past_tasks(query: str, task_type: str = "") -> str:
    """Searches past task executions and conversations using natural language meaning, not just keywords.

    Args:
        query: A natural language description of what to search for, e.g.
            "files created about the kickoff meeting".
        task_type: Optional filter — one of file, email, report, notification, backup.
            Leave empty to search across all task types.

    Returns:
        A JSON string of the most relevant past entries found.
    """
    filter_metadata = {"task_type": task_type} if task_type else None
    results = search_memory(query, filter_metadata=filter_metadata)
    return json.dumps(results)


def get_recent_logs(task_type: str = "") -> str:
    """Gets the most recent task execution logs, optionally filtered by task type.

    Args:
        task_type: Optional filter — one of file, email, report, notification, backup.
            Leave empty to get logs across all task types.

    Returns:
        A JSON string of recent task logs.
    """
    logs = get_recent_task_logs(task_type if task_type else None)
    return json.dumps(logs)


def get_recent_failures() -> str:
    """Gets recent FAILED task executions — used for failure analysis when
    the user asks why something didn't work.

    Returns:
        A JSON string of recent failed task logs with their error messages.
    """
    return json.dumps(get_failed_tasks())


# ── BUILD THE TOOL LIST, WRAPPING THE FILE TASK TOOLS WITH LOGGING ──

tools = [
    # ── Pipeline orchestrator — used this for multi-step requests ──
    _with_logging("pipeline", "execute_pipeline", execute_pipeline),

    _with_logging("file", "create_file", create_file),
    _with_logging("file", "update_file", update_file),
    _with_logging("file", "archive_file", archive_file),
    _with_logging("file", "list_files", list_files),
    _with_logging("notification", "send_slack_notification", send_slack_notification),
    _with_logging("email", "send_email", send_email),
    _with_logging("report", "generate_csv_report", generate_csv_report),       
    _with_logging("report", "generate_pdf_report", generate_pdf_report),       
    _with_logging("report", "generate_text_report", generate_text_report),
    _with_logging("report", "list_reports", list_reports), 
    _with_logging("backup", "create_backup", create_backup),      
    _with_logging("backup", "restore_backup", restore_backup),
    _with_logging("backup", "list_backups", list_backups), 
    search_past_tasks,
    get_recent_logs,
    get_recent_failures,
]


# ── THE ROOT AGENT ──
# ADK reads this exact variable name when you run `adk run` or `adk web`,
# and it's what our FastAPI layer will import too.

root_agent = Agent(
    name="astranova_task_agent",
    model="gemini-2.5-flash",
    # model="gemini-2.0-flash",


instruction="""
You are an autonomous task management agent for Astranova Labs.

You manage tasks across 5 categories:
- File: create, update, and archive files
- Email: compose and send real emails via Gmail SMTP
- Report: generate CSV, PDF, or plaintext reports
- Notification: dispatch real-time Slack alerts
- Backup: compress task workspaces into zip archives and restore them

SINGLE TASK REQUESTS:
Call the individual task tool directly (create_file, send_email, etc.)

MULTI-STEP REQUESTS (two or more actions in one request):
Use the execute_pipeline tool. Build a JSON plan with a steps array.
Each step has: tool (name), args (arguments), and optionally
pass_output_as (variable name to store result for later steps).
To reference a prior step's output in a later step's args, use the
variable name wrapped in double curly braces as the arg value.

You take REAL actions — never just describe what you would do.
For past behavior queries, use search_past_tasks or get_recent_failures.
Be concise and confirm all completed steps clearly.
""",
    tools=tools,
)
