"""
tasks/pipeline_executor.py

 MULTI-STEP PIPELINE EXECUTOR

This is the core of the multi-step execution feature. It:
1. Receives a structured task plan from the Planner LLM
2. Executes each step in order using real Python functions
3. Captures each step's output as structured data
4. Substitutes output values into subsequent steps' arguments
   using {{variable_name}} template syntax
5. Logs each step individually to MongoDB and ChromaDB

The LLM only plans — this module controls the actual execution
and data flow between steps.
"""

import json
import re
from db.mongo import log_task_execution
from db.vector_store import store_memory

# Import all available tools so the executor can call any of them
from tasks.file_task import create_file, update_file, archive_file, list_files
from tasks.email_task import send_email
from tasks.notification_task import send_slack_notification
from tasks.report_task import (
    generate_csv_report, generate_pdf_report,
    generate_text_report, list_reports
)
from tasks.backup_task import create_backup, restore_backup, list_backups

# Registry mapping tool name strings to real Python functions
TOOL_REGISTRY = {
    "create_file": create_file,
    "update_file": update_file,
    "archive_file": archive_file,
    "list_files": list_files,
    "send_email": send_email,
    "send_slack_notification": send_slack_notification,
    "generate_csv_report": generate_csv_report,
    "generate_pdf_report": generate_pdf_report,
    "generate_text_report": generate_text_report,
    "list_reports": list_reports,
    "create_backup": create_backup,
    "restore_backup": restore_backup,
    "list_backups": list_backups,
}

# Maps each tool to its task type for MongoDB logging
TOOL_TASK_TYPE = {
    "create_file": "file", "update_file": "file",
    "archive_file": "file", "list_files": "file",
    "send_email": "email",
    "send_slack_notification": "notification",
    "generate_csv_report": "report", "generate_pdf_report": "report",
    "generate_text_report": "report", "list_reports": "report",
    "create_backup": "backup", "restore_backup": "backup",
    "list_backups": "backup",
}


def _resolve_template_vars(args: dict, context: dict) -> dict:
    """
    Replaces {{variable_name}} placeholders in argument values
    with actual values from the execution context (outputs of
    previous steps).

    e.g. if context = {"file_content": "Hello world"}
    and args = {"body": "{{file_content}}"}
    then returns {"body": "Hello world"}
    """
    resolved = {}
    for key, value in args.items():
        if isinstance(value, str):
            def replace_match(match):
                var_name = match.group(1).strip()
                return str(context.get(var_name, match.group(0)))
            resolved[key] = re.sub(r"\{\{(.+?)\}\}", replace_match, value)
        else:
            resolved[key] = value
    return resolved


def execute_pipeline(task_plan_json: str) -> str:
    """
    Executes a multi-step task pipeline from a structured JSON plan.

    This is the tool the Planner LLM calls when a user requests
    multiple actions in one request. The LLM builds the plan;
    this function executes it step by step.

    Args:
        task_plan_json: A JSON string describing the pipeline steps.
            Each step must have:
            - "tool": the function name to call
            - "args": the arguments to pass (can use {{var}} templates)
            - "pass_output_as" (optional): a variable name to store
              this step's output for use in later steps

    Example input:
        {
          "pipeline_description": "Create a file and email it",
          "steps": [
            {
              "tool": "create_file",
              "args": {"filename": "report.txt", "content": "Hello!"},
              "pass_output_as": "file_result"
            },
            {
              "tool": "send_email",
              "args": {
                "to_address": "user@example.com",
                "subject": "Your report",
                "body": "File created: {{file_result}}"
              }
            }
          ]
        }

    Returns:
        A JSON string summarizing all step outcomes.
    """
    # Parse the plan
    try:
        plan = json.loads(task_plan_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid task plan JSON: {str(e)}"})

    steps = plan.get("steps", [])
    if not steps:
        return json.dumps({"error": "No steps found in task plan."})

    pipeline_description = plan.get("pipeline_description", "Multi-step task")

    # Execution context — stores outputs of completed steps
    # so later steps can reference them via {{variable_name}}
    context = {}

    step_results = []
    successful = 0
    failed = 0

    print(f"\n[Pipeline] Starting: {pipeline_description}")
    print(f"[Pipeline] {len(steps)} steps to execute\n")

    for i, step in enumerate(steps, start=1):
        tool_name = step.get("tool")
        raw_args = step.get("args", {})
        output_var = step.get("pass_output_as")

        print(f"[Pipeline] Step {i}: {tool_name}({raw_args})")

        # Validate tool exists
        if tool_name not in TOOL_REGISTRY:
            error_msg = f"Unknown tool '{tool_name}'"
            step_results.append({
                "step": i,
                "tool": tool_name,
                "status": "failure",
                "error": error_msg
            })
            failed += 1
            print(f"[Pipeline] Step {i} FAILED: {error_msg}")
            continue

        # Resolve {{variable}} placeholders using outputs from prior steps
        resolved_args = _resolve_template_vars(raw_args, context)

        # Execute the actual Python function
        try:
            tool_fn = TOOL_REGISTRY[tool_name]
            result_str = tool_fn(**resolved_args)
            result_json = json.loads(result_str)
            status = "failure" if "error" in result_json else "success"
            error_msg = result_json.get("error")
        except Exception as e:
            result_str = json.dumps({"error": str(e)})
            result_json = {"error": str(e)}
            status = "failure"
            error_msg = str(e)

        # Store output in context for subsequent steps to reference
        if output_var and status == "success":
            context[output_var] = result_str

        # Log this step to MongoDB
        task_type = TOOL_TASK_TYPE.get(tool_name, "unknown")
        log_id = log_task_execution(
            task_type=task_type,
            tool_name=tool_name,
            arguments=resolved_args,
            status=status,
            result=result_str,
            error=error_msg
        )

        # Embed this step into ChromaDB for semantic memory
        memory_text = (
            f"Pipeline step {i} of {len(steps)}. "
            f"Task type: {task_type}. Tool: {tool_name}. "
            f"Pipeline: {pipeline_description}. "
            f"Arguments: {resolved_args}. "
            f"Status: {status}. Result: {result_str}"
        )
        store_memory(
            text=memory_text,
            metadata={
                "task_type": task_type,
                "status": status,
                "tool_name": tool_name,
                "pipeline": "true"
            },
            memory_id=log_id
        )

        step_results.append({
            "step": i,
            "tool": tool_name,
            "status": status,
            "result": result_json,
            "error": error_msg
        })

        if status == "success":
            successful += 1
            print(f"[Pipeline] Step {i} SUCCESS: {result_str[:100]}")
        else:
            failed += 1
            print(f"[Pipeline] Step {i} FAILED: {error_msg}")

    # Build the final summary
    overall = "success" if failed == 0 else (
        "partial_success" if successful > 0 else "failure"
    )

    summary = {
        "pipeline_description": pipeline_description,
        "overall_status": overall,
        "total_steps": len(steps),
        "successful_steps": successful,
        "failed_steps": failed,
        "step_results": step_results
    }

    print(f"\n[Pipeline] Complete: {overall} ({successful}/{len(steps)} steps succeeded)")
    return json.dumps(summary)