# Exam Scheduler System

An automated, rule-based Exam Scheduling System designed to parse academic constraints, validate requirements, and generate conflict-free exam schedules for university programs.

## Overview

The Exam Scheduler automates the complex task of scheduling university exams. By taking in a list of courses, available exam periods, and a subset of selected programs, the system's engine calculates and outputs valid exam schedules that obey strict academic and logistical constraints efficiently and within strict runtime constraints.

## Architecture

The project follows a clean, highly modular architecture strictly separating logic (parsing, validation, computation, writing) from user view (GUI):

* **`src/models/` (Domain):** Contains the core data structures (`Course`, `ExamPeriod`, `ExamSchedule`, `ProgramEntry`) and Enumerations (`EvalType`, `Semester`, `Moed`, `Requirement`).
* **`src/file_io/` (Input Management):** Contains all logic regarding reading files and writing output schedules while performing validations and parsing.
  * `validators/` (Validation):** Ensures data integrity before the engine runs.
    * `FileValidator`: Verifies files exist, are not empty, and are valid UTF-8.
    * `MaxProgramsValidator`: Ensures no more than 5 programs are selected at once.
    * `ProgramExistenceValidator`: Ensures selected program codes exist in the master list.
  * `parsers/` (Parsing):** Parses the input files into structured data.
    * `FileParser`: Abstract parser for the input files.
    * `CourseParser`: Parses the courses file.
    * `ExamPeriodParser`: Parses the exam periods file.
    * `ProgramParser`: Parses the programs file.
    * `ParserFactory`: Creates the appropriate parser based on the input file.
  * `writers/` (Writing):** Writes the final schedule to a file.
    * `TextFileWriter`: Writes the final schedule to a text file.
    * `OutputWriter`: Handles the output of the final schedules.
* **`src/logic/` (Engine):** The brain of the system. 
  * `checkers/`: contains the logic for checking constraints.
    * `IConstraintsChecker`: Interface for checking constraints.
    * `ProgramYearConflictChecker`: Checks for program-year conflicts.
    * `MoedConflictChecker`: Checks for moed-level conflicts.
  * `Scheduler`: Main class that runs the scheduling algorithm.
  * `SlotBuilder`: Contains the logic for building slots.
  * `observers/` : Contains observer classes that are used to notify the GUI of the scheduling process.
    * `ISchedulerObserver`: Interface for observer classes.
    * `CollectingScheduleObserver`: Observer that collects the final schedule.
    * `StreamingScheduleObserver`: Observer that streams the final schedule step by step.
* **`src/infrastructure` (Infrastructure):** Contains the infrastructure layer logic.
  * `cache/`: Contains the cache logic.
    * `CachedInputLoader` : In charge of loading input data from the cache.
    * `DataCache` : Contains the cached data.
    * `DiskCacheRepository` : In charge of storing the cached data in the disk.
    * `FileChangeDetector` : Detects changes in the input files and invalidates the cache.
  * `concurrency/`: Contains the concurrency logic.
    * `SchedulerProcessRunner` : Runs the scheduler in a separate processes for better performance.
    * `SchedulerWorker` : Listens to the queue and updates the GUI with the schedules per process.
    * `QueueScheduleObserver` : Updates the queue with the schedules per process.
  * `repositories/`: Contains the repository logic.
    * `IDataRepository` : Interface for data repositories.
    * `SQLiteScheduleRepository` : Repository for storing schedules in a SQLite database.
* **`src/application/` (Application):** Contains the application layer logic.
  * `dto/` (Data Transfer Objects): contains the data transfer objects used to pass data between the GUI and the engine.
    * `ScheduleDTO` : Contains the schedule in a format that can be used by the GUI. 
    * `ScheduleDTOAdapter` : Adapter that converts each `Schedule` to `ScheduleDTO` pickable object.
  * `services/` (Services): contains the service logic.
    * `FileImportService` : Service for importing files.
    * `SchedulingService` : Service for scheduling exams.
    * `ScheduleExportService` : Service for exporting schedules.
    * `InputDataMerger` : Service for merging input data.
    * `ViewModelMapper` : Service for mapping ViewModels to DTOs.
    * `InputCacheService` : Service for caching input data.
  * `state/` (State Management): contains the state management logic.
    * `AppState` : Manages the current state of the application.
    * `InputDataState` : Manages the input data state of the application.
    * `SchedulerResultState` : Manages the schedule results and the state of the scheduling process.
    * `HybridScheduleResultState` : Manages the hybrid schedule results and the state of the scheduling process.
  * `viewmodels/` (View Models): contains the view model logic.
    * `AppController` : Manages the application state and dispatches commands.
    * `ApplicationFacade` : Interface between the GUI and the application layer.
    * `ImportBoundary` : Import input data using the facade.
* **`src/gui/` (GUI):** Contains the GUI logic.
  * `common/` (Common): contains the common GUI logic.
    * `components/`: contains the common GUI components.
      * `CalendarWidget.py` : used to display a calendar.
      * `CalendarEditorWidget.py` : used to display an editable calendar.
      * `OutputCalendarWidget.py` : used to display an output calendar.
      * `ExclusionModel.py` : used to exclude dates from calendar for the schedule editor.
      * `CourseListWidget.py` : used to display a list of courses.
      * `HeaderWidget.py` : used to display the main header of the application.
    * `helpers` : contains the helper functions for the GUI.
  * `features/` (Features): contains the GUI features logic.
    * `input/` : folder that contains the input feature logic including widgets and input screen presenter.
    * `output/` : folder that contains the output feature logic including widgets and output screen presenter.
  * `core/` (Core): contains the core GUI logic.
    * `styles/` : folder that contains all style choices for GUI in particular a pallete of colors for the entire system as well as individual stylings per widget\feature.
    * `app` : file containing the main application window.
    * `screen` : file containing the different screens of the application.
    * `ScreenRouter` : used for routing between screens based on user actions.
* **`src/entrypoints/` (Entry Points):** Contains the entry point logic.
  * `Main/` (Main): contains the main logic.
* **`src/GuiMain.py` (Main):** Contains the main logic.


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

## Error Handling

The system validates:
- Missing files
- Empty files
- Invalid UTF-8 encoding
- Invalid academic values
- Unknown program IDs

Invalid input causes descriptive exceptions before scheduling begins.
```

## GUI flow

The GUI allows user to import 2 required files and manually pick programs to schedule from the list of available programs. 
Then the user can configure input data in the form of calendars (by setting specific dates as holidays or exam periods for each program).
Finally the user can run the scheduler by click of a button and view the results in a calendar view with ability to switch between schedules, and export the best schedule to a file.
The user may also go back to update the exsiting data (by updating the calendar or clicking on load in update mode to add more data to schedule) and run the scheduler again or return to exsiting scheduling.

## Installation & Requirements

* **Python:** 3.12 or higher.
* **Dependencies:** Install the project dependencies via `requirements.txt`.
* **PyQt6:** used for the GUI.

```bash
pip install -r requirements.txt
```

## Usage

The system is operated via a Command Line Interface (CLI) and a Graphical User Interface (GUI). 
For CLI run user must provide paths to the three required input files: courses, exam periods, and selected programs.

```bash
python -m src.main <courses_file.txt> <periods_file.txt> <programs_file.txt> [--output my_schedule.txt]
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

To run tests under a specific testing suite:
```bash
pytest tests/<test_folder>
```

Continuous Integration is set up via GitHub Actions, which automatically runs the test suite on every push and Pull Request to ensure maximum stability.