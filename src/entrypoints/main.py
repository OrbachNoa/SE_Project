import argparse
import os
import sys
import time

from data.programs import programs_data
from io.validators.FileValidator import validate_all_files
from io.parsers.ParserFactory import ParserFactory
from src.logic.SlotBuilder import SlotBuilder
from src.logic.Scheduler import Scheduler
from logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from logic.checkers.MoedOrderChecker import MoedOrderChecker
from logic.observers.CollectingScheduleObserver import CollectingScheduleObserver
from logic.observers.StreamingScheduleObserver import StreamingScheduleObserver
from io.validators.MaxProgramsValidator import MaxProgramsValidator
from io.validators.ProgramExistenceValidator import ProgramExistenceValidator
from io.writers.TextFileWriter import TextFileWriter
from infrastructure.cache.DiskCacheRepository import DiskCacheRepository
from infrastructure.cache.FileChangeDetector import FileChangeDetector
from infrastructure.cache.CachedInputLoader import CachedInputLoader
from io.validators.ValidatorPipeline import ValidatorPipeline



def run_pipeline(courses_file=None, periods_file=None, programs_file=None,
                 output_file=None, courses=None, periods=None, programs=None,
                 validators=None, slot_builder=None, scheduler=None,
                 output_writer=None, output_path=None, schedule_observer=None):
    """Executes the complete flow of parsing, validation, scheduling, and output generation."""

    # Parse input files if paths are provided
    parsed = ParserFactory.parse_files({
        "courses": courses_file,
        "periods": periods_file,
        "programs": programs_file
    })
    courses = parsed.get("courses", courses)
    periods = parsed.get("periods", periods)
    programs = parsed.get("programs", programs)

    # Resolve the final output path
    final_output_path = output_file or output_path

    # Initialize validators
    if validators is None:
        validators = [
            MaxProgramsValidator(),
            ProgramExistenceValidator(valid_ids=programs_data),
        ]

    # Execute early validation on selected programs
    pipeline = ValidatorPipeline(validators)
    result = pipeline.validate(programs)
    if not result.is_valid:
        raise ValueError("\n".join(result.errors))

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
            course_parser=ParserFactory.create("courses"),
            period_parser=ParserFactory.create("periods"),
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