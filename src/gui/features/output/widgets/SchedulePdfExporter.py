"""
SchedulePdfExporter — pure view-layer PDF export helper.
"""
from __future__ import annotations

import html
import os
import re

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QTextDocument, QFont
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageSize

from gui.core.styles.Palette import COLOR_PRIMARY, COLOR_GOLD, COLOR_TEXT, COLOR_BG, COLOR_MUTED


# The main entry point that coordinates asking the user for a path and triggering the export
def export_schedule_pdf(view, current_index: int, parent) -> None:
    """
    Run the full PDF export flow for the schedule currently on screen.
    """
    # Ask the user where to save, suggesting a readable default file name.
    default_name = f"exam_schedule_solution_{current_index + 1}.pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent, "Save schedule as PDF", default_name, "PDF files (*.pdf)"
    )
    # If the user closed the dialog without choosing a file, stop here.
    if not path:
        return
    # Add .pdf extension if the user forgot it.
    if not path.lower().endswith(".pdf"):
        path += ".pdf"

    # Build the HTML structure and send it to the PDF engine.
    try:
        document_html = _build_schedule_html(view)
        _write_html_to_pdf(document_html, path)
    except Exception as error:
        # Show an error alert if something goes wrong during the saving process.
        QMessageBox.critical(parent, "Export error", f"Failed to create the PDF:\n{error}")
        return

    # Let the user know the process was successful.
    QMessageBox.information(
        parent, "Export complete", f"Schedule saved to:\n{os.path.abspath(path)}"
    )


# A helper function that transforms your data model into a structured HTML string
def _build_schedule_html(view) -> str:
    """
    Build a printable HTML table from a schedule view model.
    Table contains 5 columns: Date, Course, Instructor, Details and Programs.
    """
    # Defining column widths to make the PDF look balanced
    width_date = "13%"
    width_course = "25%"
    width_instructor = "17%"
    width_details = "25%"
    width_programs = "20%"

    # Looping over the schedule items and creating a table row for each exam
    rows_html = []
    for row_index, item in enumerate(sorted(view.items, key=lambda it: it.date)):
        date_text = html.escape(str(item.date))
        course_text = html.escape(str(item.title))

        # Instructor column — use the instructor name or a dash if unknown
        instructor_text = html.escape(item.instructor) if item.instructor else "<span style='color:#94A3B8;'>—</span>"

        # Processing the details (Course ID, Semester, Moed, etc.) for the table cell
        clean_sub = item.subtitle.replace("<br>", "\n")
        clean_sub = re.sub(r"<[^>]+>", "", clean_sub)
        clean_sub = clean_sub.replace("ID: ", "")
        sub_parts = [p.strip() for p in clean_sub.split("\n") if p.strip()]
        course_id_text = sub_parts[0] if sub_parts else ""

        tooltip_lines = str(item.tooltip).split("\n")
        if len(tooltip_lines) >= 2:
            meta_pieces = tooltip_lines[1].strip().split(" · ", 1)
            if len(meta_pieces) > 1:
                course_id_text += " · " + meta_pieces[1]

        if item.evaluation:
            course_id_text += f" · {item.evaluation}"

        details_text = html.escape(course_id_text)

        # Building the programs column with tags/info
        prog_parts = [p for p in sub_parts[1:] if p.strip()]
        if prog_parts:
            programs_text = "<br>".join(html.escape(p) for p in prog_parts)
        else:
            programs_text = "<span style='color:#94A3B8;'>—</span>"

        # Alternate the row background color (zebra-striping) to keep it easy to read
        row_background = "#FFFFFF" if row_index % 2 == 0 else COLOR_BG

        # Combining all pieces into an HTML table row
        rows_html.append(
            f"<tr bgcolor='{row_background}'>"
            f"<td width='{width_date}' style='color:{COLOR_PRIMARY}; font-weight:bold;'>{date_text}</td>"
            f"<td width='{width_course}' style='color:{COLOR_TEXT}; font-weight:bold;'>{course_text}</td>"
            f"<td width='{width_instructor}' style='color:{COLOR_MUTED};'>{instructor_text}</td>"
            f"<td width='{width_details}' style='color:{COLOR_MUTED};'>{details_text}</td>"
            f"<td width='{width_programs}' style='color:{COLOR_TEXT};'>{programs_text}</td>"
            "</tr>"
        )

    solution_line = html.escape(f"Solution {view.current_index + 1} of {view.total}")
    exam_count = len(view.items)

    # Return the full HTML document with a gold header
    return (
        "<html><body>"
        f"<h1 style='color:{COLOR_PRIMARY}; margin:0 0 2pt 0;'>Exam Schedule</h1>"
        f"<p style='color:{COLOR_MUTED}; margin:0 0 14pt 0;'>{solution_line} &nbsp;·&nbsp; {exam_count} exams</p>"
        "<table width='100%' cellspacing='0' cellpadding='7'>"
        f"<tr bgcolor='{COLOR_GOLD}'>"
        f"<td width='{width_date}' style='color:{COLOR_TEXT}; font-weight:bold;'>Date</td>"
        f"<td width='{width_course}' style='color:{COLOR_TEXT}; font-weight:bold;'>Course</td>"
        f"<td width='{width_instructor}' style='color:{COLOR_TEXT}; font-weight:bold;'>Instructor</td>"
        f"<td width='{width_details}' style='color:{COLOR_TEXT}; font-weight:bold;'>Details</td>"
        f"<td width='{width_programs}' style='color:{COLOR_TEXT}; font-weight:bold;'>Programs</td>"
        "</tr>"
        f"{''.join(rows_html)}"
        "</table>"
        "</body></html>"
    )


# A helper function that uses Qt's printing system to actually render HTML to a physical file
def _write_html_to_pdf(document_html: str, path: str) -> None:
    """Render an HTML string to a PDF file using Qt printing support."""
    # Set up the virtual printer as a PDF generator
    printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    try:
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    except Exception:
        # A4 is the default page size, so a binding mismatch is harmless.
        pass

    # Create a document object, set the font, and load the HTML content
    document = QTextDocument()
    document.setDefaultFont(QFont("Arial", 11))
    document.setHtml(document_html)

    # Trigger the print command to save the document as a file
    print_method = getattr(document, "print", None) or getattr(document, "print_")
    print_method(printer)