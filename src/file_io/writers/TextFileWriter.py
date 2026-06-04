import sys
import os
from typing import List
from .OutputWriter import OutputWriter
from models.domain import ExamSchedule, ExamAssignment
from models.Enums import Semester, Moed

# Defines the standard academic rendering order for output sections.
SEMESTER_ORDER = {s.name: i for i, s in enumerate(Semester)}
MOED_ORDER     = {m.name: i for i, m in enumerate(Moed)}

class TextFileWriter(OutputWriter):
    """
    Writes generated schedules into a readable text file.
    """

    def write(self, schedules: List[ExamSchedule], path: str) -> None:
        """
        Exports all generated schedules to the requested file path.
        """
        try:
            # Defines the export contract to decouple the Scheduler from specific storage formats (OCP).
            with open(path, 'w', encoding='utf-8', buffering=512 * 1024) as f:
                if not schedules:
                    f.write("No valid exam schedules were generated.\n")
                    return

                # Cache formatted dates, so repeated dates are formatted only once.
                date_cache = {}

                # Cache enum names, so repeated enum lookups are avoided.
                enum_name_cache = {}

                for i, schedule in enumerate(schedules, 1):
                    f.write(f"=== Exam System Option {i} ===\n")
                    f.write(self.formatSchedule(schedule, date_cache, enum_name_cache))
                    f.write("\n\n")
        except IOError as e:
            print(f"Error: Unable to write to file at {path}. {e}", file=sys.stderr)
            raise

    def formatSchedule(self, schedule: ExamSchedule,
                       date_cache: dict = None,
                       enum_name_cache: dict = None) -> str:
        """
        Converts one schedule into grouped text output.
        """
        if not hasattr(schedule, 'assignments') or not schedule.assignments:
            return "No exams scheduled for this option."

        # Create local caches when shared caches were not provided.
        if date_cache is None:
            date_cache = {}
        if enum_name_cache is None:
            enum_name_cache = {}

        assignments = schedule.assignments

        # Sorts exams chronologically to ensure a natural reading flow.
        assignments = sorted(schedule.assignments, key=lambda x: x.date)

        # Group assignments by semester and moed, so the output has clear sections.
        grouped_data = {}
        for a in assignments:
            # Resolve enum names through the cache, so repeated lookups are avoided.
            sem = a.semester
            if sem not in enum_name_cache:
                enum_name_cache[sem] = sem.name
            moed = a.moed
            if moed not in enum_name_cache:
                enum_name_cache[moed] = moed.name

            key = (enum_name_cache[sem], enum_name_cache[moed])
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(a)

        output = []
        # Sorts the display buckets according to the globally defined academic calendar order.
        ordered_keys = sorted(
            grouped_data.keys(),
            key=lambda k: (SEMESTER_ORDER.get(k[0], 99), MOED_ORDER.get(k[1], 99)),
        )
        for key in ordered_keys:
            semester, moed = key
            items = grouped_data[key]
            output.append(f"\n--- SEMESTER: {semester} | MOED: {moed} ---")
            for a in items:
                # Format each unique date once, so repeated dates reuse the cache.
                d = a.date
                if d not in date_cache:
                    date_cache[d] = d.strftime('%d-%m-%Y')

                output.append(
                    f"Date: {date_cache[d]} | "
                    f"Course: {a.course.name} | "
                    f"Instructor: {a.course.instructor}"
                )

        return "\n".join(output)
