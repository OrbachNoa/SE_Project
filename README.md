# Exam Scheduler System

An automated, rule-based Exam Scheduling System designed to parse academic constraints, validate requirements, and generate conflict-free exam schedules for university programs.

![System logo](data/assets/logo.png)

## Overview

The Exam Scheduler automates the complex task of scheduling university exams. By taking in a list of courses, available exam periods, and a subset of selected programs, the system's engine calculates and outputs valid exam schedules that obey strict academic and logistical constraints efficiently and within strict runtime constraints.

## Architecture - Core components

- **Parsers (`src/parsers/`)**: Responsible for reading the raw text input files and converting them into strongly typed domain objects (`Course`, `ExamPeriod`, etc.).
- **Validators (`src/validators/`)**: Validate the structural integrity of the input files before any scheduling logic runs.
- **Checkers (`src/logic/`)**: Enforce the business rules of the exam schedule by known constraints and applied user preferences.
- **Scheduler (`src/logic/Scheduler.py`)**: The central engine that orchestrates the generation of valid schedules.
- **GUI (`src/gui/`)**: The graphical user interface for the application. Includes screens for input, output, clustering, etc. 
- **Sorting (`src/logic/comparators/`)**: Responsible for sorting the exam schedule (e.g., group exams together).
- **Clustering (`src/logic/clustering/`)**: Responsible for clustering generated exam schedules based on course similarity. It also contains an LLM-based module for analyzing and translating natural language user preferences into clustering criteria.


## Schedling Engine

The scheduling engine uses recursive backtracking with heuristic-based pruning to efficiently find all valid schedules. It iteratively builds schedules, pruning branches that violate constraints while minimizing conflicts and improving scheduling efficiency.
The engine is designed to operate within the project performance constraints.

## Threading & Concurrency Model

Long-running operations (like the backtracking algorithm) run in a separate CPU process to avoid freezing the main GUI thread.

**Core Components:**
- `SchedulerProcessRunner` — Executes the heavy search in an isolated subprocess.
- `SchedulerWorker` (`QThread`) — Listens to the subprocess via IPC (Queue) and safely emits PyQt signals to the GUI.

**Usage Example:**
```python
# 1. Initialize the worker with IPC channels and the background process
self.worker = SchedulerWorker(queue, cancel_event, process)

# 2. Connect worker signals to GUI callbacks (Thread-safe UI updates)
self.worker.schedule_found.connect(self.on_schedule_found)
self.worker.search_finished.connect(self.on_finished)

# 3. Start the listener (which in turn starts the background process)
self.worker.start()

# To gracefully stop the search and prevent zombie processes:
self.worker.cancel()
```

## Error Handling

The system validates:
- Missing files
- Empty files
- Invalid UTF-8 encoding
- Invalid academic values
- Unknown program IDs

Invalid input causes descriptive exceptions before scheduling begins.

## GUI flow

The GUI allows user to import 2 required files and manually pick programs to schedule from the list of available programs. 
Then the user can configure input data in the form of calendars (by setting specific dates as holidays or exam periods for each program).
Finally the user can run the scheduler by click of a button and view the results in a calendar view with ability to switch between schedules, and export the best schedule to a file.
The user may also go back to update the exsiting data (by updating the calendar or clicking on load in update mode to add more data to schedule) and run the scheduler again or return to exsiting scheduling.

## Clustering

Our added feature to system is the ability to cluster generated exam schedules based on course similarity. The clustering is done using the K-Means algorithm, which is a popular clustering algorithm that is used to partition a dataset into k clusters.

List of llm optional requests in English and Hebrew:
```
- Give me all schedules with least back to back exams and most spacious gaps between exams for instructors.
- I want no more than one exam per day, no more than 2 exams per week and at leat 5 days between them
- give me 6 groups such that the lecturer will have enough time to check the exams between moeds
- give me the most comfortable schedule for busy student
- אני רוצה חלוקה ל5 קבוצות, בלי מבחנים עוקבים ועם לפחות 7 ימים בין מבחנים
- תחלק ל3 קבוצות, כשיש לי לא יותר מ3 ימים בין בחינות
```

## Installation & Requirements

* **Python:** 3.12 or higher.
* **Dependencies:** Install the project dependencies via `requirements.txt`.
* **PyQt6:** used for the GUI.
* **psutil:** used for monitoring system performance.
* **scikit-learn:** used for the clustering.
* **numpy:** used for the clustering.
* **openpyxl:** used for the Excel export.

Create and activate a virtual environment first, so the dependencies install in an isolated environment instead of your global Python:

```bash
python -m venv .venv
```

On Windows:
```bash
.venv\Scripts\activate
```

On macOS/Linux:
```bash
source .venv/bin/activate
```

Then install the dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The system is operated via a Command Line Interface (CLI) and a Graphical User Interface (GUI). 
For CLI run user must provide paths to the three required input files: courses, exam periods, and selected programs.

```bash
python -m src.main <courses_file.txt> <periods_file.txt> <programs_file.txt> [--output my_schedule.txt]
```

For CLI run with custom constraints, use the following command (each of the constraints are optional):

```bash
python -m src.main <courses_file.txt> <periods_file.txt> <programs_file.txt> --min-gap-obligatory <int> --min-gap-any <int> --elective-conflict-cap <int> --exam-span <int> --max-exams-per-day <int>
```

For GUI run user must call main GUI entry point.

```bash
python -m src.GuiMain
```

### Arguments:
* `courses_file`: Text file containing course details, instructors, evaluation types, and program requirements.
* `periods_file`: Text file defining the semesters, Moeds, start/end dates, and excluded dates.
* `programs_file`: Text file containing a comma-separated list of 5-digit program IDs to schedule exams for.
* `--output` (Optional): The file path where the generated schedule will be written (defaults to `output.txt`).
* `--min-gap-obligatory` (Optional): The minimum number of days between two consecutive obligatory exams.
* `--min-gap-any` (Optional): The minimum number of days between any two consecutive exams.
* `--elective-conflict-cap` (Optional): The maximum number of elective exams a student can have in a single day.
* `--exam-span` (Optional): The number of days over which the exams should be scheduled.
* `--max-exams-per-day` (Optional): The maximum number of exams that can be scheduled in a single day.

## Testing

The project is backed by a comprehensive automated test suite built with `pytest`, covering domain logic, parsing, validation, integration, behavioural rules, and performance metrics.

Note: In order to run tests `pytest-qt` must be installed.

To run the entire test suite:
```bash
pytest tests/ -v
```

To run tests while ignoring performance benchmarks:
```bash
pytest tests/ -m "not performance" -v --tb=short
```

To run tests under a specific testing suite:
```bash
pytest tests/<test_folder>
```

Continuous Integration is set up via GitHub Actions, which automatically runs the test suite on every push and Pull Request to ensure maximum stability.