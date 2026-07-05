# Task Management Agent

An agentic AI platform where users interact entirely through natural language to create, execute, and monitor tasks across five distinct categories — each performing real system operations. Built using Google ADK, Gemini, MongoDB, ChromaDB, and Arize Phoenix.

---

## What it does

You talk to it in plain English. It decides what action to take, executes it for real, logs everything, and remembers it semantically — so you can ask "what did I do last week" or "why did my backup fail" and get meaningful answers grounded in actual logged data.

```
User: "Create a file called report.txt and email it to me"
Agent: Plans a 2-step pipeline → creates the file → emails it with the file content
       Logs both steps to MongoDB → embeds both into ChromaDB for future recall
```

---

## Task types

| Task | Description | Real action |
|---|---|---|
| **File** | Create, update, archive files | Local filesystem operations |
| **Email** | Compose and send emails | Gmail SMTP |
| **Report** | Generate structured documents | CSV, PDF, plaintext via ReportLab |
| **Notification** | Send real-time alerts | Slack webhook |
| **Backup** | Data preservation | ZIP compression + extraction via shutil |

---

## Key features

**Multi-step pipeline execution**
Single natural language requests trigger chained tool sequences. The LLM plans the pipeline as structured JSON; Python executes each step in order, passing the output of one step as input to the next using `{{variable_name}}` template substitution. The LLM never handles data flow — Python does.

**Semantic memory**
Every tool execution is embedded into ChromaDB using `sentence-transformers`. Ask "have I done something like this before?" and the agent searches by meaning, not keywords — finding relevant past actions even if phrased completely differently.

**Failure analysis**
Failed executions are logged to MongoDB with full error details and embedded into the vector store. Ask "why did my backup fail?" and the agent retrieves real failure records to explain.

**Observability**
Every agent invocation is traced in Arize Phoenix — latency, cost, and full span waterfall showing each tool call within a multi-step pipeline.

---

## Architecture

```
Natural language request
        ↓
ADK Agent (Gemini) — plans action or pipeline
        ↓
Pipeline Executor (Python) — executes steps in order,
  passes output of step N as input to step N+1
        ↓
Task Tools — real system operations
  File · Email · Report · Notification · Backup
        ↓
    ┌──────────────────┬─────────────────────┐
    ↓                  ↓                     ↓
MongoDB            ChromaDB           Arize Phoenix
(execution log)    (semantic memory)  (observability)
```

---

## Tech stack

| Component | Technology |
|---|---|
| Agent framework | Google ADK 2.x |
| LLM | Gemini 2.5 Flash |
| Backend | Python 3.14 |
| Database | MongoDB (local) |
| Vector store | ChromaDB + sentence-transformers |
| Observability | Arize Phoenix Cloud |
| Email | Gmail SMTP (smtplib) |
| Notifications | Slack Incoming Webhooks |
| PDF generation | ReportLab |

---

## Project structure

```
task-management-agent/
├── task_agent/
│   ├── agent.py              ADK root_agent — tool definitions, instruction, logging wrapper
│   ├── instrumentation.py    Arize Phoenix tracing setup (must import first)
│   └── __init__.py
├── tasks/
│   ├── file_task.py          create_file, update_file, archive_file, list_files
│   ├── email_task.py         send_email via Gmail SMTP
│   ├── report_task.py        generate_csv_report, generate_pdf_report, generate_text_report
│   ├── notification_task.py  send_slack_notification via webhook
│   ├── backup_task.py        create_backup, restore_backup, list_backups
│   └── pipeline_executor.py  multi-step pipeline engine with template variable substitution
├── db/
│   ├── mongo.py              MongoDB connection, task logging, failure queries
│   └── vector_store.py       ChromaDB embeddings, semantic search
└── .gitignore
```

---


## Example requests

**Single task:**
```
Create a file called meeting_notes.txt with the content "Q3 planning complete"
List the files in the workspace
Send a Slack notification saying "Deployment complete"
Generate a PDF report titled "Weekly Summary" called weekly.pdf with body "All systems operational"
Create a backup of the file workspace
```

**Multi-step pipeline:**
```
Create a file called update.txt with content "Project on track" and then email it to me
Generate a status report and send a Slack notification saying the report is ready
Create a file, back it up, then notify me on Slack
```

**Memory and analysis:**
```
Have I created any files before?
Show me recent task logs
What tasks have failed?
Search for anything related to backup failures
```

---

## How multi-step execution works

When you send a request with multiple actions, Gemini generates a structured JSON pipeline plan. Python's pipeline_executor.py takes that plan and:

1. Executes each step using the real tool function
2. Captures the output as structured data
3. Substitutes outputs into subsequent steps arguments using template syntax
4. Logs each step independently to MongoDB and ChromaDB

The LLM only plans. Python controls execution and data flow — that is what makes this genuinely agentic rather than just chained LLM calls.

---

## What makes this different from a chatbot

| Chatbot | This agent |
|---|---|
| Answers from memory | Takes real actions |
| Forgets everything | Logs every action permanently |
| Cannot search its past | Semantic recall over all history |
| No visibility into what happened | Full observability via Phoenix |
| One response at a time | Chains multiple real operations |
