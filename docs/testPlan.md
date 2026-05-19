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

### 3.1 File Parser Tests
Tests the abstract FileParser base class and three concrete parsers: CoursesFileParser, ExamPeriodsFileParser, ProgramsFileParser. Each parser reads a UTF-8 text file, splits on the $$$$ separator, and returns typed domain objects.

### 3.2 Domain Model Tests
Tests the core domain classes: Course, ExamPeriod, ExamAssignment, ExamSchedule, and supporting enums.

### 3.3 Input Validator Tests
Tests MaxProgramsValidator (max 5 programs) and ProgramExistenceValidator (only known program codes).

### 3.4 Conflict Checker Tests
Tests the three IConflictChecker implementations: ProgramYearConflictChecker, ExcludedDatesChecker, ExamPeriodBoundaryChecker.

### 3.5 Scheduler Engine Tests
Tests the Scheduler class — the core backtracking engine that generates all valid schedules.

### 3.6 Output Formatter Tests
Tests TextFileWriter — formatting and writing the final schedule output.

### 3.7 Integration Tests
Full end-to-end pipeline tests using real fixture files. No mocks.

### 3.8 Main Entry Point Tests
Tests the CLI main() function — correct exit codes, clean stderr, no Python tracebacks.

### 3.9 Behavioural & Completeness Tests
High-level correctness tests for the scheduling algorithm. Verify properties that span multiple classes.

### 3.10 Performance Tests
Verify the 30-second SRS constraint under realistic and maximum load scenarios.

# Test File Structure
tests/
|── Conftest.py
├── Test_Parsers.py          # TC-PRS-001 – TC-PARS-021
├── Test_Domain.py           # TC-DOM-001 – TC-DOM-014
├── Test_Validators.py       # TC-VAL-001 – TC-VAL-011
├── Test_Checkers.py         # TC-CHK-001 – TC-CHK-009
├── Test_Scheduler_Engine.py # TC-ENG-001 – TC-ENG-005
├── Test_Output.py           # TC-OUT-001 – TC-OUT-008
├── Test_Integration.py      # TC-INT-001 – TC-INT-005
├── Test_Main.py             # TC-MAIN-001 – TC-MAIN-006
├── Test_Behavioural.py      # TC-BEH-001 – TC-BEH-007
├── Test_Performance.py      # TC-PER-001 – TC-PER-002
└── fixtures/                # Sample input files used by all tests
    ├── courses_valid.txt
    ├── courses_no_exams.txt
    ├── periods_valid.txt
    ├── programs_valid.txt
    ├── programs_bad.txt
    └── programs_too_many.txt