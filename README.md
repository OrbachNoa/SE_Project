# Exam Scheduler System

An automated, rule-based Exam Scheduling System designed to parse academic constraints, validate requirements, and generate conflict-free exam schedules for university programs.

## Overview

The Exam Scheduler automates the complex task of scheduling university exams. By taking in a list of courses, available exam periods, and a subset of selected programs, the system's engine calculates and outputs valid exam schedules that obey strict academic and logistical constraints efficiently and within strict runtime constraints.

## Architecture

The project follows a clean, highly modular architecture strictly separating input parsing, validation, scheduling logic, and output generation:

* **`src/models/` (Domain):** Contains the core data structures (`Course`, `ExamPeriod`, `ExamSchedule`, `ProgramEntry`) and Enumerations (`EvalType`, `Semester`, `Moed`, `Requirement`).
* **`src/parsers/` (Input Management):** Reads raw text files and converts them into structured Domain objects. It handles specific formats and uses `$$$$` as a record separator.
* **`src/validators/` (Validation):** Ensures data integrity before the engine runs.
  * `FileValidator`: Verifies files exist, are not empty, and are valid UTF-8.
  * `MaxProgramsValidator`: Ensures no more than 5 programs are selected at once.
  * `ProgramExistenceValidator`: Ensures selected program codes exist in the master list.
* **`src/logic/` (Engine):** The brain of the system. The `Scheduler` generates schedules by running potential assignments through rigorous `Checkers`:
  * `ProgramYearConflictChecker`: Prevents students in the same program/year from having overlapping exams.
  * `ExcludedDatesChecker`: Honors university-wide holidays and excluded dates.
  * `ExamPeriodBoundaryChecker`: Ensures exams strictly fall within the official exam period dates.

The scheduling engine uses recursive backtracking with heuristic-based pruning to efficiently find all valid schedules. It iteratively builds schedules, pruning branches that violate constraints while minimizing conflicts and improving scheduling efficiency.
The engine is designed to operate within the project performance constraints.
* **`src/writers/` (Output):** Generates human-readable text files containing the final scheduled assignments (`TextFileWriter`).

## Error Handling

The system validates:
- Missing files
- Empty files
- Invalid UTF-8 encoding
- Invalid academic values
- Unknown program IDs

Invalid input causes descriptive exceptions before scheduling begins.

## Installation & Requirements

* **Python:** 3.12 or higher.
* **Dependencies:** Install the project dependencies via `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Usage

The system is operated via a Command Line Interface (CLI). You must provide paths to the three required input files: courses, exam periods, and selected programs.

```bash
python -m src.main <courses_file.txt> <periods_file.txt> <programs_file.txt> [--output my_schedule.txt]
```

### Arguments:
* `courses_file`: Text file containing course details, instructors, evaluation types, and program requirements.
* `periods_file`: Text file defining the semesters, Moeds, start/end dates, and excluded dates.
* `programs_file`: Text file containing a comma-separated list of 5-digit program IDs to schedule exams for.
* `--output` (Optional): The file path where the generated schedule will be written (defaults to `output.txt`).

## Testing

The project is backed by a comprehensive automated test suite built with `pytest`, covering domain logic, parsing, validation, integration, behavioural rules, and performance metrics.

To run the entire test suite:
```bash
pytest tests/ -v
```

To run tests while ignoring performance benchmarks:
```bash
pytest tests/ -m "not performance" -v --tb=short
```

Continuous Integration is set up via GitHub Actions, which automatically runs the test suite on every push to ensure maximum stability.