import os
from typing import List
from src.writers.outputWriter import OutputWriter
from src.models.domain import ExamSchedule, ExamAssignment

class TextFileWriter(OutputWriter):
    """
    Concrete implementation of OutputWriter that generates a human-readable text file.
    The output is formatted, sorted, and grouped according to the system requirements.
    """

    def write(self, schedules: List[ExamSchedule], path: str) -> None:
        """
        Entry point for exporting the generated schedules to a file.
        Uses UTF-8 encoding to support various characters as required.
        """
        try:
            # Open the file for writing with UTF-8 encoding 
            with open(path, 'w', encoding='utf-8') as f:
                if not schedules:
                    f.write("No valid exam schedules were generated.\n")
                    return

                # Process each possible scheduling option
                for i, schedule in enumerate(schedules, 1):
                    f.write(f"=== Exam System Option {i} ===\n")
                    # Generate the formatted string for the current schedule
                    f.write(self.formatSchedule(schedule))
                    f.write("\n\n")
        except IOError as e:
            # Handle potential file system errors
            print(f"Error: Unable to write to file at {path}. {e}")

    def formatSchedule(self, schedule: ExamSchedule) -> str:
        """
        Converts an ExamSchedule object into a structured string.
        Groups exams by semester and moed, and sorts them chronologically.
        """
        # Ensure there are assignments to process
        if not hasattr(schedule, 'assignments') or not schedule.assignments:
            return "No exams scheduled for this option."

        output = []
        assignments = schedule.assignments 
        
        # Sort all assignments by date to ensure chronological order 
        assignments.sort(key=lambda x: x.date)

        # Group assignments by (Semester, Moed) to create distinct sections 
        grouped_data = {}
        for a in assignments:
            # Extract semester and moed labels from their respective enums
            semester_label = a.semester.name
            moed_label = a.moed.name
            
            key = (semester_label, moed_label)
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(a)

        # Iterate through grouped sections to build the final string
        for (semester, moed), items in grouped_data.items():
            # Section header 
            output.append(f"\n--- SEMESTER: {semester} | MOED: {moed} ---")
            
            for a in items:
                # Format date as DD-MM-YYYY 
                date_str = a.date.strftime('%d-%m-%Y')
                
                # Assemble the line with mandatory details: Date, Course Name, and Instructor
                line = (f"Date: {date_str} | "
                        f"Course: {a.course.name} | "
                        f"Instructor: {a.course.instructor}")
                output.append(line)
        
        return "\n".join(output)