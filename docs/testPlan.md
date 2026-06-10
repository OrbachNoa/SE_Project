# Test Plan – Exam Scheduling System:

## 1. Overview
This Test Plan defines the testing approach for the Exam Scheduling System. The system receives three input files (courses, exam periods, programs), validates them, and uses a backtracking algorithm to generate all valid exam schedules. Tests are organized by system layer and cover Unit, Integration, Behavioural, and Performance testing. All tests follow the Arrange-Act-Assert (AAA) pattern and are executed with pytest.

## 2. Test Strategy

### Unit Tests - 
Each class/method tested in isolation using mocks/stubs where needed
### Integration Tests - 
Full 4-phase pipeline: Parse → Validate → Generate → Write
### Behavioural Tests - 
Scheduling correctness: completeness, conflict detection, backtracking
### Performance Tests - 
Schedule generation must complete within 30 seconds

## 3. Test Layers
Tests are devided into 3 main layers: Logic, GUI, and Performance.

### 3.1 Logic Tests
This field tests the core logic of the system and is devided into Unit Tests and Integration Tests.

#### 3.1.1 Unit Tests

* **Test File Parsers:**
  * Tests the abstract FileParser base class and three concrete parsers: CoursesFileParser, ExamPeriodsFileParser, ProgramsFileParser. Each parser reads a UTF-8 text file, splits on the $$$$ separator, and returns typed domain objects.

* **Test Domain Model:**
  * Tests the core domain classes: Course, ExamPeriod, ExamAssignment, ExamSchedule, and supporting enums.

* **Test Input Validator:**
  * Tests MaxProgramsValidator (max 5 programs) and ProgramExistenceValidator (only known program codes).

* **Test Conflict Checker:**
  * Tests the three IConflictChecker implementations: ProgramYearConflictChecker, MoedOrderChecker.

* **Test Scheduler Engine:**
  * Tests the Scheduler class — the core backtracking engine that generates all valid schedules.

* **Test Slot Builder:**
  * Tests the SlotBuilder class — builds slots for scheduling.

* **Test Observers:**
  * Tests Observer pattern implementation for monitoring schedule generation progress.

* **Test Boundary DTOs:**
  * Tests boundary DTOs for schedule generation.

* **Test Data Cache:**
  * Tests the DataCache class for efficient storage and retrieval of schedule data, including add/get courses/periods, clear, count, and iteration.

* **Test ViewModel Mapper:**
  * Tests the ViewModelMapper class for correct conversion of domain model objects to ViewModels.

#### 3.1.2 Integration Tests

* **Test Behavioural:**
  * High-level correctness tests for the scheduling algorithm. Verify properties that span multiple classes.

* **Test Integration:**
  * Tests integration between parsers, validators, schedulers, and writers. Full end-to-end pipeline tests using real fixture files.

* **Test Application State:**
  * Tests ApplicationState for managing application-wide state and transitions.

* **Test Main:**
  * Tests the CLI main() function — correct exit codes, clean stderr, no Python tracebacks.

* **Test Output:**
  * Tests the file writer outputs in correct format with the correct data.

* **Test Scheduling Service:**
  * Tests the SchedulingService for correct scheduling logic.

* **Test Hybrid State:**
  * Tests the HybridState class for correct state management.

### 3.2 GUI Tests
This field tests the GUI aspect of the system and is devided into Unit Tests and Integration Tests.

#### 3.2.1 Unit Tests

* **Test Action Bar Widget:**
  * Tests the ActionBarWidget for correct initial state, button rendering, mode toggle (replace/update), and signal emission when load/generate buttons are clicked.

* **Test App Controller:**
  * Tests the AppController class for correct delegation to the ApplicationFacade — verifying that load_file, generate_schedules, get_loaded_courses, get_loaded_periods, get_page_info, get_schedule_view, and cancel all propagate the correct arguments and return values.

* **Test Calendar Editor Widget:**
  * Tests the CalendarEditorWidget for correct display of exam periods, date exclusion toggling, and proper rendering of excluded-date indicators.

* **Test Calendar Widget:**
  * Tests the CalendarWidget for correct month rendering, exam-date highlighting, and interaction with the period navigator when the displayed month changes.

* **Test Course List Widget:**
  * Tests the CourseListWidget for correct rendering of course blocks from a list of domain Course objects, and correct filtering behaviour by program ID.

* **Test Exclusion Model:**
  * Tests the ExclusionModel for managing excluded-date state — adding, removing, and querying excluded dates, and ensuring the model fires the correct change signals.

* **Test Input Screen:**
  * Tests the InputScreen widget for correct rendering of the action bar and program selector card, file-load button wiring, and mode switching between replace and update.

* **Test Input Screen Presenter:**
  * Tests the InputScreenPresenter for correct coordination between the InputScreen view and the AppController — verifying file load delegation, import mode forwarding, and course-list refresh after a successful load.

* **Test Navigation:**
  * Tests the NavigationState model for correct index tracking across a schedule result set — including boundary guards, reset-on-set-schedules, and out-of-bounds error handling.

* **Test Output Screen:**
  * Tests the OutputScreen widget for correct initial state, forward/backward schedule navigation, calendar month display, schedule counter updates, and back-to-input routing.

* **Test Output Screen Presenter:**
  * Tests the OutputScreenPresenter for correct counter refresh, solution-bar state (next/prev enabled flags), page loading, calendar rendering from a ScheduleViewModel, PDF export guards (empty schedule, zero total), and export error handling.

* **Test Period Navigator:**
  * Tests the PeriodNavigator for correct initialisation with and without periods, next/previous navigation boundary enforcement, label generation, date-list construction, and rejection of invalid date ranges.

* **Test Program Selector:**
  * Tests the ProgramSelectorDialog for correct initial selection state, checkbox toggle behaviour, and enforcement of the maximum five-program selection limit with a warning popup.

* **Test Program Selector Card Widget:**
  * Tests the ProgramSelectorCardWidget for correct initial badge and placeholder state, chip rendering after selection, badge count updates, and mouse-click flow for both accept and cancel dialog outcomes.

* **Test Solution Bar Widget:**
  * Tests the SolutionBarWidget for correct initial disabled state, button tooltips, back/export click signal emission, next/previous navigation signal emission, paging signal emission, and rejection of clicks on disabled buttons.

#### 3.2.2 Integration Tests

* **Test GUI:**
  * End-to-end GUI tests using `pytest-qt` (qtbot) that simulate complete user flows headlessly; covering file loading (replace and update modes), program selection, schedule generation, router navigation, PDF export, and full real-pipeline execution with actual parsers and a SQLite repository.

* **Test GUI Integration:**
  * Tests that the ScreenRouter correctly registers, transitions between, and tracks history for the InputScreen and OutputScreen.

* **Test Workers:**
  * Tests the SchedulerWorker QThread and SchedulerProcessRunner concurrency layer; covering IPC message dispatching, crash drainage, graceful cancellation, process termination, and error propagation via the queue.

### 3.3 Performance Tests
This field tests the performance aspect of the system.

* **Test Performance:**
  * Verify the 30-second SRS constraint under realistic and maximum load scenarios.

# Test File Structure
```bash
tests/
├── conftest.py
├── fixtures/
│   ├── courses_valid.txt
│   ├── courses_no_exams.txt
│   ├── periods_valid.txt
│   ├── programs_valid.txt
│   ├── programs_bad.txt
│   └── programs_too_many.txt
├── logic/
│   ├── unit/
│   │   ├── Test_Domain.py
│   │   ├── Test_BoundaryDTOs.py
│   │   ├── Test_Checkers.py
│   │   ├── Test_SlotBuilder.py
│   │   ├── Test_Validators.py
│   │   ├── Test_Parsers.py
│   │   ├── Test_Observers.py
│   │   ├── Test_DataCache.py
│   │   ├── Test_ViewModelMapper.py
│   │   └── Test_SchedulerEngine.py
│   └── integration/
│       ├── Test_ApplicationState.py
│       ├── Test_SchedulingService.py
│       ├── Test_HybridState.py
│       ├── Test_Behavioural.py
│       ├── Test_Integration.py
│       ├── Test_Main.py
│       └── Test_Output.py
├── gui/
│   ├── unit/
│   │   ├── Test_AppController.py
│   │   ├── Test_ActionBarWidget.py
│   │   ├── Test_CalendarEditorWidget.py
│   │   ├── Test_CalendarWidget.py
│   │   ├── Test_CourseListWidget.py
│   │   ├── Test_ExclusionModel.py
│   │   ├── Test_InputScreen.py
│   │   ├── Test_InputScreenPresenter.py
│   │   ├── Test_OutputScreen.py
│   │   ├── Test_OutputScreenPresenter.py
│   │   ├── Test_PeriodNavigator.py
│   │   ├── Test_ProgramSelector.py
│   │   ├── Test_ProgramSelectorCardWidget.py
│   │   ├── Test_SolutionBarWidget.py
│   │   └── Test_Navigation.py
│   └── integration/
│       ├── Test_GUI.py
│       ├── Test_GUIIntegration.py
│       └── Test_Workers.py
└── performance/
    └── Test_Performance.py
```