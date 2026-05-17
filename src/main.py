import argparse
import os
import sys

from src.validators.fileValidator import validate_all_files
from src.parsers.courseParser import CoursesFileParser
from src.parsers.dateParser import ExamPeriodsFileParser
from src.parsers.programParser import ProgramsFileParser
from src.logic.Scheduler import Scheduler
from src.writers.textFileWriter import TextFileWriter
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.ExcludedDatesChecker import ExcludedDatesChecker
from src.logic.ExamPeriodBoundaryChecker import ExamPeriodBoundaryChecker
from src.validators.maxProgramsValidator import MaxProgramsValidator
from src.validators.programExistenceValidator import ProgramExistenceValidator
from src.logic.MoedOrderChecker import MoedOrderChecker

def run_pipeline(courses_file=None, periods_file=None, programs_file=None, output_file=None,
                 courses=None, periods=None, programs=None, validators=None,
                 scheduler=None, output_writer=None, output_path=None):

    # Parse the courses file, so the scheduler can use course objects.
    if courses_file:
        courses = CoursesFileParser().parse(courses_file)
    # Parse the periods file, so the scheduler knows the allowed dates.
    if periods_file:
        periods = ExamPeriodsFileParser().parse(periods_file)
    # Parse the programs file, so only selected programs are scheduled.
    if programs_file:
        programs = ProgramsFileParser().parse(programs_file)

    # Choose the output path, so both argument names are supported.
    final_output_path = output_file or output_path

    # Validate selected programs, so bad input stops before scheduling.
    validators = validators or [MaxProgramsValidator(), ProgramExistenceValidator()]
    for v in validators:
        if not v.validate(programs):
            raise ValueError(v.error_message(programs))

    # Create the scheduler, so schedules can be generated when none was provided.
    if not scheduler:
        checkers = [
            ProgramYearConflictChecker(),
            ExcludedDatesChecker(periods),
            ExamPeriodBoundaryChecker(periods),
            MoedOrderChecker(),
        ]
        scheduler = Scheduler(courses, periods, checkers, validators, selected_programs=programs)

    # Generate all valid schedules from the parsed input.
    schedules = scheduler.generateAllSchedules()

    # Write schedules to a file when an output path was given.
    writer = output_writer or TextFileWriter()
    if final_output_path:
        writer.write(schedules, final_output_path)

    # Return schedules, so tests or callers can inspect the result.
    return schedules


def _parse_args():
    # Build command-line arguments, so users can run the program from terminal.
    parser = argparse.ArgumentParser(description="Exam scheduler - generates all valid exam schedules.")
    parser.add_argument("courses")
    parser.add_argument("periods")
    parser.add_argument("programs")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main():
    # Read command-line arguments, so the program knows the input files.
    args = _parse_args()
    try:
        # Validate file paths first, so missing files fail with a clear error.
        validate_all_files([args.courses, args.periods, args.programs])

        # Set default output path to the current user's Downloads folder, so there is a safe fallback location.
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "exam_schedules.txt")

        # Fetch path from Environment Variable, so custom system environments are supported.
        env_path = os.environ.get('EXAM_OUTPUT_PATH', default_path)

        # Choose the final output path based on priority, so manual flags override environment settings.
        output_path = args.output or env_path

        print(f"File validation successful. Output will be saved to: {output_path}")

        # Run the full scheduling flow, so output is created from the input files.
        run_pipeline(
            courses_file=args.courses,
            periods_file=args.periods,
            programs_file=args.programs,
            output_file=output_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        # Print a clear error, so the user knows what went wrong.
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Start the program only when this file is executed directly.
    main()
