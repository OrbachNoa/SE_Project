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
from src.logic.CollectingScheduleObserver import CollectingScheduleObserver
from src.logic.StreamingScheduleObserver import StreamingScheduleObserver
from src.validators.maxProgramsValidator import MaxProgramsValidator
from src.validators.programExistenceValidator import ProgramExistenceValidator
from src.writers.textFileWriter import TextFileWriter
from src.data.DiskCacheRepository import DiskCacheRepository
from src.data.FileChangeDetector import FileChangeDetector
from src.data.CachedInputLoader import CachedInputLoader


def run_pipeline(courses_file=None, periods_file=None, programs_file=None,
                 output_file=None, courses=None, periods=None, programs=None,
                 validators=None, slot_builder=None, scheduler=None,
                 output_writer=None, output_path=None, schedule_observer=None):
    """Executes the complete flow of parsing, validation, scheduling, and output generation."""

    # Parse input files if paths are provided
    if courses_file:
        courses = CoursesFileParser().parse(courses_file)
    if periods_file:
        periods = ExamPeriodsFileParser().parse(periods_file)
    if programs_file:
        programs = ProgramsFileParser().parse(programs_file)

    # Resolve the final output path
    final_output_path = output_file or output_path

    # Initialize validators dynamically based on loaded courses if not provided
    if validators is None:
        valid_program_ids = {
            entry.programId
            for course in (courses or [])
            for entry in course.programEntries
        }
        validators = [
            MaxProgramsValidator(),
            ProgramExistenceValidator(valid_ids=valid_program_ids),
        ]

    # Execute early validation on selected programs
    for v in validators:
        if not v.validate(programs):
            raise ValueError(v.error_message(programs))

    # Build scheduling slots
    if slot_builder is None:
        slot_builder = SlotBuilder(periods, selected_programs=programs)
    slots = slot_builder.build(courses)

    # Configure conflict checkers and initialize the scheduler
    if scheduler is None:
        py_checker = ProgramYearConflictChecker()
        courses_in_slots = list({s.course for s in slots})
        py_checker.precompute_conflicts(courses_in_slots, programs)
        checkers = [py_checker, MoedOrderChecker()]
        scheduler = Scheduler(checkers)

    # Execute scheduling using a custom observer if provided (e.g., for streaming)
    if schedule_observer is not None:
        scheduler.generateSchedules(slots, schedule_observer)
        schedule_observer.on_finished()
        if schedule_observer.error:
            raise RuntimeError(schedule_observer.error)
        return None

    # Execute default scheduling with in-memory collection
    observer = CollectingScheduleObserver()
    scheduler.generateSchedules(slots, observer)
    if observer.error:
        raise RuntimeError(observer.error)

    schedules = observer.schedules

    # Write collected schedules to disk if an output path is defined
    writer = output_writer or TextFileWriter()
    if final_output_path:
        writer.write(schedules, final_output_path)

    return schedules


def _parse_args():
    """Parses command-line arguments for the CLI execution."""
    parser = argparse.ArgumentParser(description="Exam scheduler - generates valid exam schedules.")
    parser.add_argument("courses")
    parser.add_argument("periods")
    parser.add_argument("programs")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main():
    """Main entry point for the CLI application."""
    args = _parse_args()
    try:
        # Validate source files before starting the pipeline
        validate_all_files([args.courses, args.periods, args.programs])

        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "exam_schedules.txt")
        env_path = os.environ.get('EXAM_OUTPUT_PATH', default_path)
        output_path = args.output or env_path

        print(f"File validation successful. Output will be saved to: {output_path}")

        start_time = time.perf_counter()

        # Load inputs utilizing the disk-cache to optimize repeated runs
        loader = CachedInputLoader(
            repository=DiskCacheRepository(),
            detector=FileChangeDetector(),
            course_parser=CoursesFileParser(),
            period_parser=ExamPeriodsFileParser(),
        )
        courses, periods = loader.load(args.courses, args.periods)

        # Initialize a streaming observer to write results directly to disk
        streaming_observer = StreamingScheduleObserver(output_path)

        # Run the scheduling pipeline
        run_pipeline(
            courses=courses,
            periods=periods,
            programs_file=args.programs,
            schedule_observer=streaming_observer,
        )

        end_time = time.perf_counter()
        total_time = end_time - start_time

        print(f"Total execution time: {total_time:.4f} seconds")

    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()