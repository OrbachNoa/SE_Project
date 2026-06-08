"""
SchedulePdfExporter — pure view-layer PDF export helper.

This module is intentionally kept separate from OutputScreen so that
the screen file stays focused on navigation and display logic. Nothing
here touches the application layer, the controller, or any service —
it only reads a ScheduleViewModel and writes a PDF file.

Public API
----------
export_schedule_pdf(view, current_index, parent_widget) -> None
    Full export flow: file dialog, HTML build, PDF write, result dialog.
"""
from __future__ import annotations

import html
import os
import re

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QTextDocument, QFont


def export_schedule_pdf(view, current_index: int, parent) -> None:
    """
    Run the full PDF export flow for the schedule currently on screen.

    Asks the user where to save, builds an HTML table from the view model,
    renders it to a PDF and shows a confirmation dialog. Every step is pure
    view layer — no controller or application service is touched.

    Parameters
    ----------
    view:
        The ScheduleViewModel for the schedule currently displayed.
    current_index:
        Zero-based index of the schedule inside the current page, used only
        to suggest a readable default file name.
    parent:
        The Qt widget used as the parent for dialogs (file picker, message
        boxes). Pass the OutputScreen instance so dialogs are centred on it.
    """
    # Ask the user where to save, suggesting a readable default file name.
    default_name = f"exam_schedule_solution_{current_index + 1}.pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent, "Save schedule as PDF", default_name, "PDF files (*.pdf)"
    )
    if not path:
        # The user closed the dialog without choosing a file.
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"

    # Build the HTML and render it to the chosen file.
    try:
        document_html = _build_schedule_html(view)
        _write_html_to_pdf(document_html, path)
    except Exception as error:
        QMessageBox.critical(parent, "Export error", f"Failed to create the PDF:\n{error}")
        return

    QMessageBox.information(
        parent, "Export complete", f"Schedule saved to:\n{os.path.abspath(path)}"
    )


def _build_schedule_html(view) -> str:
    """
    Build a printable HTML table from a schedule view model.

    QTextDocument only understands a small subset of HTML and ignores most
    CSS written through class selectors. To get clean columns we therefore
    use the classic table model it does support: a fixed table width, an
    explicit width on every cell, cellpadding for the spacing between
    columns and inline styles for the colors. Every dynamic value is escaped
    so the markup always stays valid.

    The four columns are Date, Course, Details and Programs. The Programs
    text is taken from the lines of the tooltip that describe the program
    and whether the course is obligatory or elective.
    """
    # Column widths, declared once so the header and the body always agree.
    width_date = "15%"
    width_course = "30%"
    width_details = "31%"
    width_programs = "24%"

    rows_html = []
    for row_index, item in enumerate(sorted(view.items, key=lambda it: it.date)):
        date_text = html.escape(str(item.date))
        course_text = html.escape(str(item.title))

        # The subtitle from the mapper contains HTML (<br>, <span>) that must
        # be converted to plain text before going into the PDF table. After
        # cleaning, the first line holds the course id and the remaining lines
        # hold the program / requirement pairs ("Prog 83101 (Obligatory)").
        clean_sub = item.subtitle.replace("<br>", "\n")
        clean_sub = re.sub(r"<[^>]+>", "", clean_sub)
        clean_sub = clean_sub.replace("ID: ", "")
        sub_parts = [p.strip() for p in clean_sub.split("\n") if p.strip()]

        # Build the Details column: course id + semester and moed pulled from
        # the second line of the tooltip ("date · FALL · Moed ALEPH").
        course_id_text = sub_parts[0] if sub_parts else ""
        tooltip_lines = str(item.tooltip).split("\n")
        if len(tooltip_lines) >= 2:
            meta_pieces = tooltip_lines[1].strip().split(" \u00b7 ", 1)
            if len(meta_pieces) > 1:
                # Append the semester and moed after the course id.
                course_id_text += " \u00b7 " + meta_pieces[1]
        details_text = html.escape(course_id_text)

        # Build the Programs column from the program lines that sit after the
        # course id in the cleaned subtitle (e.g. "Prog 83101 (Obligatory)").
        prog_parts = [p for p in sub_parts[1:] if p.strip()]
        if prog_parts:
            programs_text = "<br>".join(html.escape(p) for p in prog_parts)
        else:
            programs_text = "<span style='color:#94A3B8;'>\u2014</span>"

        # Alternate the row background so long tables stay easy to read.
        row_background = "#FFFFFF" if row_index % 2 == 0 else "#F4F7F9"

        rows_html.append(
            f"<tr bgcolor='{row_background}'>"
            f"<td width='{width_date}' style='color:#143D30; font-weight:bold;'>{date_text}</td>"
            f"<td width='{width_course}' style='font-weight:bold;'>{course_text}</td>"
            f"<td width='{width_details}' style='color:#64748B;'>{details_text}</td>"
            f"<td width='{width_programs}' style='color:#334155;'>{programs_text}</td>"
            "</tr>"
        )

    solution_line = html.escape(f"Solution {view.current_index + 1} of {view.total}")
    exam_count = len(view.items)

    # The header row uses the dark green brand color with white text. The
    # body rows follow with the data assembled above.
    return (
        "<html><body>"
        "<h1 style='color:#143D30; margin:0 0 2pt 0;'>Exam Schedule</h1>"
        f"<p style='color:#64748B; margin:0 0 14pt 0;'>{solution_line} &nbsp;\u00b7&nbsp; {exam_count} exams</p>"
        "<table width='100%' cellspacing='0' cellpadding='7'>"
        "<tr bgcolor='#143D30'>"
        f"<td width='{width_date}' style='color:#FFFFFF; font-weight:bold;'>Date</td>"
        f"<td width='{width_course}' style='color:#FFFFFF; font-weight:bold;'>Course</td>"
        f"<td width='{width_details}' style='color:#FFFFFF; font-weight:bold;'>Details</td>"
        f"<td width='{width_programs}' style='color:#FFFFFF; font-weight:bold;'>Programs</td>"
        "</tr>"
        f"{''.join(rows_html)}"
        "</table>"
        "</body></html>"
    )


def _write_html_to_pdf(document_html: str, path: str) -> None:
    """
    Render an HTML string to a PDF file using Qt printing support.

    The print module is imported here, not at the top of the file, so the
    rest of the screen still loads on a Qt build without print support. Any
    problem then only shows up when the user actually clicks Export.

    We print in screen resolution, which is 96 dots per inch. That matches
    the resolution QTextDocument lays the content out at, so there is no
    scale mismatch between the document and the page. Setting a high
    resolution device size by hand is what made earlier output render as an
    unreadable speck. The text is stored as vectors in the PDF, so it stays
    sharp at any zoom level.
    """
    from PyQt6.QtPrintSupport import QPrinter
    from PyQt6.QtGui import QPageSize

    printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    try:
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    except Exception:
        # A4 is the default page size, so a binding mismatch is harmless.
        pass

    document = QTextDocument()
    # A comfortable base font size for the whole document. Headings grow
    # from this automatically.
    document.setDefaultFont(QFont("Arial", 11))
    document.setHtml(document_html)

    # PyQt6 names the method "print"; fall back to "print_" for safety.
    print_method = getattr(document, "print", None) or getattr(document, "print_")
    print_method(printer)