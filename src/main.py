import argparse
import logging
import os
import sys
import time

from data.programs import programs_data
from src.application.errors.ErrorModel import AppErrorInfo, ErrorSeverity
from src.application.errors.ExceptionMapper import default_registry
from src.application.errors.ErrorLogger import ErrorLogger
from src.file_io.validators.FileValidator import validate_all_files
from src.file_io.parsers.ParserFactory import ParserFactory
from src.logic.SlotBuilder import SlotBuilder
from src.logic.Scheduler import Scheduler
from src.logic.ScheduleFeasibilityValidator import ScheduleFeasibilityValidator
from src.logic.feasibility.InfeasibleScheduleError import InfeasibleScheduleError
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.checkers.config.CheckerFactory import build_checkers
from src.logic.observers.CollectingScheduleObserver import CollectingScheduleObserver
from src.logic.observers.StreamingScheduleObserver import StreamingScheduleObserver
from src.file_io.validators.MaxProgramsValidator import MaxProgramsValidator
from src.file_io.validators.ProgramExistenceValidator import ProgramExistenceValidator
from src.file_io.writers.TextFileWriter import TextFileWriter
from src.infrastructure.cache.DiskCacheRepository import DiskCacheRepository
from src.infrastructure.cache.FileChangeDetector import FileChangeDetector
from src.infrastructure.cache.CachedInputLoader import CachedInputLoader
from src.file_io.validators.ValidatorPipeline import ValidatorPipeline



def run_pipeline(courses_file=None, periods_file=None, programs_file=None,
                 output_file=None, courses=None, periods=None, programs=None,
                 validators=None, slot_builder=None, scheduler=None,
                 output_writer=None, output_path=None, schedule_observer=None,
                 config=None):
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
    feasibility_errors = ScheduleFeasibilityValidator().validate(
        courses, programs, slots, config
    )
    if feasibility_errors:
        raise InfeasibleScheduleError(feasibility_errors)

    # Configure conflict checkers and initialize the scheduler
    if scheduler is None:
        courses_in_slots = list({s.course for s in slots})
        checkers = build_checkers(config, courses_in_slots, programs, slots)
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
    parser.add_argument("--min-gap-obligatory", type=int, default=None)
    parser.add_argument("--min-gap-any", type=int, default=None)
    parser.add_argument("--elective-conflict-cap", type=int, default=None)
    parser.add_argument("--exam-span", type=int, default=None)
    parser.add_argument("--max-exams-per-day", type=int, default=None)
    return parser.parse_args()


def _validate_constraints_config(config: ConstraintsConfig) -> None:
    positive_fields = {
        "min-gap-obligatory": config.min_gap_obligatory,
        "min-gap-any": config.min_gap_any,
        "exam-span": config.exam_span,
        "max-exams-per-day": config.max_exams_per_day,
    }
    for name, value in positive_fields.items():
        if value is not None and value <= 0:
            raise ValueError(f"--{name} must be a positive integer")

    if config.elective_conflict_cap is not None and config.elective_conflict_cap < 0:
        raise ValueError("--elective-conflict-cap must be a non-negative integer")


# Exit codes by severity, so callers/scripts can branch on the kind of failure.
_EXIT_CODE_BY_SEVERITY = {
    ErrorSeverity.INFO: 0,
    ErrorSeverity.WARNING: 1,
    ErrorSeverity.ERROR: 1,
    ErrorSeverity.CRITICAL: 2,
}


def _report_and_exit(info: AppErrorInfo) -> None:
    """Print the clean message (never a traceback) and exit with a coded status."""
    print(f"Error: {info.user_message}", file=sys.stderr)
    sys.exit(_EXIT_CODE_BY_SEVERITY.get(info.severity, 1))


def main():
    """Main entry point for the CLI application."""
    args = _parse_args()
    # Route every failure through the same mapper the GUI uses, so the CLI shows
    # a clean message and a consistent exit code instead of a raw traceback.
    # Technical detail goes to the log (a NullHandler keeps it off stderr unless
    # the host configured logging), the user only sees user_message.
    registry = default_registry()
    error_logger = ErrorLogger()
    logging.getLogger("se_project.errors").addHandler(logging.NullHandler())
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

        # Build the Phase-3 threshold constraints from CLI flags (None = disabled)
        config = ConstraintsConfig(
            min_gap_obligatory=args.min_gap_obligatory,
            min_gap_any=args.min_gap_any,
            elective_conflict_cap=args.elective_conflict_cap,
            exam_span=args.exam_span,
            max_exams_per_day=args.max_exams_per_day,
        )
        _validate_constraints_config(config)

        # Run the scheduling pipeline
        run_pipeline(
            courses=courses,
            periods=periods,
            programs_file=args.programs,
            schedule_observer=streaming_observer,
            config=config,
        )

        end_time = time.perf_counter()
        total_time = end_time - start_time

        print(f"Total execution time: {total_time:.4f} seconds")

    except Exception as exc:
        # InfeasibleScheduleError, MemoryError, file/validation errors and any
        # unexpected fault all funnel through the registry into one clean report.
        info = registry.map(exc, {"argv": sys.argv})
        error_logger.log(info, cause=exc)
        _report_and_exit(info)


if __name__ == "__main__":
    main()
