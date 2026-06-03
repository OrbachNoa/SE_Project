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

* **Test Data Cache:**
  * Tests DataCache for efficient storage and retrieval of schedule data.

* **Test Boundary DTOs:**
  * Tests boundary DTOs for schedule generation.

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

### 3.2 GUI Tests
This field tests the GUI aspect of the system and is devided into Unit Tests and Integration Tests.

#### 3.2.1 Unit Tests

* **Test Screen Router:**
  * Tests the ScreenRouter class for correct navigation between screens.

* **Test App Controller:**
  * Tests the AppController class for correct application state management.

* **Test Navigation:**
  * Tests the navigation between screens.

#### 3.2.2 Integration Tests

* **Test GUI:**
  * Tests the GUI for correct functionality.

* **Test GUI Integration:**
  * Tests the integration between the GUI and the backend.

* **Test Workers:**
  * Tests the workers for correct functionality.

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
│   │   ├── Test_Boundary_DTOs.py
│   │   ├── Test_Checkers.py
│   │   ├── Test_SlotBuilder.py
│   │   ├── Test_Validators.py
│   │   ├── Test_Parsers.py
│   │   ├── Test_Observers.py
│   │   ├── Test_Data_Cache.py
│   │   └── Test_Scheduler_Engine.py
│   └── integration/
│       ├── Test_Application_State.py
│       ├── Test_Scheduling_Service.py
│       ├── Test_Behavioural.py
│       ├── Test_Integration.py
│       ├── Test_Main.py
│       └── Test_Output.py
├── gui/
│   ├── unit/
│   │   ├── Test_Screen_Router.py
│   │   ├── Test_App_Controller.py
│   │   └── Test_Navigation.py
│   └── integration/
│       ├── Test_GUI.py
│       ├── Test_GUI_Integration.py
│       └── Test_Workers.py
└── performance/
    └── Test_Performance.py
```