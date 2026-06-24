import re


def format_schedule_csv(schedule_view) -> tuple[list[str], list[list[str]]]:
    """
    Converts a ScheduleViewModel object into a simple tabular structure
    (headers and rows) suitable for CSV export.
    Matches the exact layout and data of the PDF export.
    """
    headers = ["Date", "Course", "Instructor", "Details", "Programs"]
    rows = []

    if not schedule_view or not hasattr(schedule_view, 'items') or not schedule_view.items:
        return headers, rows

    # Sort items by date, identical to the PDF export logic
    for item in sorted(schedule_view.items, key=lambda it: it.date):

        # Date and Course Title
        date_text = str(getattr(item, 'date', ''))
        course_text = str(getattr(item, 'title', ''))

        # Instructor (use a dash if no instructor is assigned)
        instructor_val = getattr(item, 'instructor', '')
        instructor_text = instructor_val if instructor_val else "—"

        # Extracting "Details" from subtitle and tooltip
        subtitle = getattr(item, 'subtitle', '')

        # Clean HTML tags and br elements
        clean_sub = subtitle.replace("<br>", "\n")
        clean_sub = re.sub(r"<[^>]+>", "", clean_sub)
        clean_sub = clean_sub.replace("ID: ", "")

        # Split into parts
        sub_parts = [p.strip() for p in clean_sub.split("\n") if p.strip()]
        course_id_text = sub_parts[0] if sub_parts else ""

        # Extract Semester and Moed from the tooltip
        tooltip = str(getattr(item, 'tooltip', ''))
        tooltip_lines = tooltip.split("\n")
        if len(tooltip_lines) >= 2:
            meta_pieces = tooltip_lines[1].strip().split(" · ", 1)
            if len(meta_pieces) > 1:
                course_id_text += " · " + meta_pieces[1]

        # Add Evaluation Type (e.g., EXAM)
        evaluation = getattr(item, 'evaluation', '')
        if evaluation:
            course_id_text += f" · {evaluation}"

        details_text = course_id_text

        # Extracting "Programs" from the remaining subtitle parts
        prog_parts = [p for p in sub_parts[1:] if p.strip()]
        programs_text = "\n".join(prog_parts) if prog_parts else "—"

        # Append the processed row to our rows list
        rows.append([date_text, course_text, instructor_text, details_text, programs_text])

    return headers, rows