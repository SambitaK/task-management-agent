"""
tasks/report_task.py

REPORT TASK — generates structured documents and data exports.
Supports CSV (data exports) and PDF (formatted reports), and plaintext.

Reports are saved into their own workspace folder, separate from
file_task's workspace, since they're a conceptually different task type.
"""

import os
import csv
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

REPORTS_DIR = "data/report_task_workspace"
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_csv_report(filename: str, headers: str, rows: str) -> str:
    """Generates a CSV report from structured data.

    Args:
        filename: Name for the CSV file, e.g. "sales_report.csv".
        headers: Comma-separated column headers, e.g. "Name,Amount,Date".
        rows: Row data as a string with rows separated by semicolons and
            values within a row separated by commas, e.g.
            "Alice,100,2026-01-01;Bob,200,2026-01-02".

    Returns:
        A JSON string describing the result of the operation.
    """
    if not filename.endswith(".csv"):
        filename += ".csv"

    filepath = os.path.join(REPORTS_DIR, filename)

    try:
        header_list = [h.strip() for h in headers.split(",")]
        row_list = [
            [v.strip() for v in row.split(",")]
            for row in rows.split(";") if row.strip()
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header_list)
            writer.writerows(row_list)

        return json.dumps({
            "success": True,
            "action": "csv_report_generated",
            "filename": filename,
            "rows_written": len(row_list)
        })

    except Exception as e:
        return json.dumps({"error": f"Failed to generate CSV report: {str(e)}"})


def generate_pdf_report(filename: str, title: str, body_text: str, table_data: str = "") -> str:
    """Generates a formatted PDF report with a title, body text, and an
    optional table.

    Args:
        filename: Name for the PDF file, e.g. "monthly_summary.pdf".
        title: The report's title, shown at the top of the document.
        body_text: The main paragraph content of the report.
        table_data: Optional table data, rows separated by semicolons and
            values within a row separated by commas, e.g.
            "Header1,Header2;Value1,Value2". First row is treated as headers.

    Returns:
        A JSON string describing the result of the operation.
    """
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    filepath = os.path.join(REPORTS_DIR, filename)

    try:
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(body_text, styles["Normal"]))
        story.append(Spacer(1, 20))

        if table_data.strip():
            rows = [
                [v.strip() for v in row.split(",")]
                for row in table_data.split(";") if row.strip()
            ]
            table = Table(rows)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ]))
            story.append(table)

        doc.build(story)

        return json.dumps({
            "success": True,
            "action": "pdf_report_generated",
            "filename": filename,
            "title": title
        })

    except Exception as e:
        return json.dumps({"error": f"Failed to generate PDF report: {str(e)}"})


def generate_text_report(filename: str, content: str) -> str:
    """Generates a simple plaintext report.

    Args:
        filename: Name for the text file, e.g. "summary.txt".
        content: The full text content of the report.

    Returns:
        A JSON string describing the result of the operation.
    """
    if not filename.endswith(".txt"):
        filename += ".txt"

    filepath = os.path.join(REPORTS_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return json.dumps({
            "success": True,
            "action": "text_report_generated",
            "filename": filename,
            "size_bytes": os.path.getsize(filepath)
        })

    except Exception as e:
        return json.dumps({"error": f"Failed to generate text report: {str(e)}"})


def list_reports() -> str:
    """Lists all generated reports currently saved.

    Returns:
        A JSON string listing each report file and its size.
    """
    files = os.listdir(REPORTS_DIR)
    if not files:
        return json.dumps({"message": "No reports have been generated yet."})

    file_details = [
        {"filename": f, "size_bytes": os.path.getsize(os.path.join(REPORTS_DIR, f))}
        for f in files
    ]
    return json.dumps({"reports": file_details})