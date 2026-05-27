# region Imports
import argparse
import os
import sys
import time

from src.validators.fileValidator import validate_all_files
from src.parsers.courseParser import CoursesFileParser
from src.parsers.dateParser import ExamPeriodsFileParser
from src.parsers.programParser import ProgramsFileParser
from src.logic.SlotBuilder import SlotBuilder
from src.logic.Scheduler import Scheduler
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.MoedOrderChecker import MoedOrderChecker
from src.validators.maxProgramsValidator import MaxProgramsValidator
from src.validators.programExistenceValidator import ProgramExistenceValidator
from src.writers.textFileWriter import TextFileWriter
# endregion


def run_pipeline(courses_file=None, periods_file=None, programs_file=None,
                 output_file=None, courses=None, periods=None, programs=None,
                 validators=None, slot_builder=None, scheduler=None,
                 output_writer=None, output_path=None):
    """Runs parsing, validation, scheduling, and output writing."""

    # Parse input files when paths were provided.
    if courses_file:
        courses = CoursesFileParser().parse(courses_file)
    if periods_file:
        periods = ExamPeriodsFileParser().parse(periods_file)
    if programs_file:
        programs = ProgramsFileParser().parse(programs_file)

    # Resolve the output path: explicit output_file wins, then output_path.
    final_output_path = output_file or output_path

    # Validate selected programs before any expensive work, so bad input fails fast.
    validators = validators or [MaxProgramsValidator(), ProgramExistenceValidator()]
    for v in validators:
        if not v.validate(programs):
            raise ValueError(v.error_message(programs))

    # Build slots first, so the scheduler gets a simple search problem.
    if slot_builder is None:
        slot_builder = SlotBuilder(periods, selected_programs=programs)
    slots = slot_builder.build(courses)

    # Prepare conflict checkers, so scheduling can test assignments quickly.
    if scheduler is None:
        py_checker = ProgramYearConflictChecker()
        courses_in_slots = list({s.course for s in slots})
        py_checker.precompute_conflicts(courses_in_slots, programs)
        checkers = [py_checker, MoedOrderChecker()]
        scheduler = Scheduler(checkers)

    # Run the backtracking search, so valid schedules can be found.
    schedules = scheduler.generateSchedules(slots)

    # Write schedules to a file when an output path was provided.
    writer = output_writer or TextFileWriter()
    if final_output_path:
        writer.write(schedules, final_output_path)

    return schedules


def _parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Exam scheduler - generates all valid exam schedules.")
    parser.add_argument("courses")
    parser.add_argument("periods")
    parser.add_argument("programs")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main():
    """Main entry point of the program."""
    args = _parse_args()
    try:
        # Validate file paths first, so missing files fail before scheduling.
        validate_all_files([args.courses, args.periods, args.programs])

        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "exam_schedules.txt")
        env_path = os.environ.get('EXAM_OUTPUT_PATH', default_path)
        output_path = args.output or env_path

        print(f"File validation successful. Output will be saved to: {output_path}")

        start_time = time.perf_counter()

        run_pipeline(
            courses_file=args.courses,
            periods_file=args.periods,
            programs_file=args.programs,
            output_file=output_path,
        )

        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        print(f"Total execution time: {total_time:.4f} seconds")

    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
