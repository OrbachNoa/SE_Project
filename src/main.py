import argparse
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

def run_pipeline(courses_file=None, periods_file=None, programs_file=None, output_file=None,
                 courses=None, periods=None, programs=None, validators=None,
                 scheduler=None, output_writer=None, output_path=None):

    # Parses raw input files into structured domain objects to prepare data for the scheduling logic.
    if courses_file:
        courses = CoursesFileParser().parse(courses_file)
    if periods_file:
        periods = ExamPeriodsFileParser().parse(periods_file)
    if programs_file:
        programs = ProgramsFileParser().parse(programs_file)

    final_output_path = output_file or output_path

    # Runs pre-check validators on selected programs to catch invalid inputs before starting the scheduling engine.
    validators = validators or [MaxProgramsValidator(), ProgramExistenceValidator()]
    for v in validators:
        if not v.validate(programs):
            raise ValueError(f"Validation failed for programs: {programs}")
    # Initializes the Scheduler with specific rule-checkers to enforce constraints like date boundaries and excluded days.
    if not scheduler:
        checkers = [
            ProgramYearConflictChecker(),
            ExcludedDatesChecker(periods),
            ExamPeriodBoundaryChecker(periods)
        ]
        scheduler = Scheduler(courses, periods, checkers, validators, selected_programs=programs)

    # Triggers the core logic to calculate and return all possible valid exam schedules based on the constraints.
    schedules = scheduler.generateAllSchedules()

    # Delegates the results to an output writer to save the generated schedules into a physical file.
    writer = output_writer or TextFileWriter()
    if final_output_path:
        writer.write(schedules, final_output_path)

    return schedules

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("courses")
    parser.add_argument("periods")
    parser.add_argument("programs")
    parser.add_argument("--output", default="output.txt")

    args = parser.parse_args()

    # Verifies that all provided file paths exist and are accessible to prevent runtime crashes during parsing.
    validate_all_files([args.courses, args.periods, args.programs])

    run_pipeline(
        courses_file=args.courses,
        periods_file=args.periods,
        programs_file=args.programs,
        output_file=args.output
    )

if __name__ == "__main__":
    main()