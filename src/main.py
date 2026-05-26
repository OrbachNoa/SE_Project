# region Imports
import argparse
import os
import sys

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
    """
    Three-step scheduling pipeline:
        1. SlotBuilder  - turn courses+periods+programs into self-contained
                          slots (each slot carries its own candidate dates).
        2. Checker prep - precompute the program-year conflict graph once.
        3. Scheduler    - run backtracking using only slots and checkers.
    SlotBuilder and Scheduler are injectable, so tests can replace either.
    """

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

    # Step 1: build self-contained slots (domain -> search problem).
    # Each slot carries its own candidate dates, so the Scheduler does not
    # need any reference to periods.
    if slot_builder is None:
        slot_builder = SlotBuilder(periods, selected_programs=programs)
    slots = slot_builder.build(courses)

    # Step 2: prepare conflict checkers. The program-year checker needs a
    # one-time precomputation of the conflict graph. Done here (not in
    # Scheduler) so Scheduler stays a pure algorithm.
    if scheduler is None:
        py_checker = ProgramYearConflictChecker()
        courses_in_slots = list({s.course for s in slots})
        py_checker.precompute_conflicts(courses_in_slots, programs)
        checkers = [py_checker, MoedOrderChecker()]
        scheduler = Scheduler(checkers)

    # Step 3: run the backtracking search.
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
        # Validate file paths first, so missing files fail with a clear error.
        validate_all_files([args.courses, args.periods, args.programs])

        # Pick the output path: CLI flag > env var > Downloads folder fallback.
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "exam_schedules.txt")
        env_path = os.environ.get('EXAM_OUTPUT_PATH', default_path)
        output_path = args.output or env_path

        print(f"File validation successful. Output will be saved to: {output_path}")

        run_pipeline(
            courses_file=args.courses,
            periods_file=args.periods,
            programs_file=args.programs,
            output_file=output_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()