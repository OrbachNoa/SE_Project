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

### 3.6 SlotBuilder Tests
Tests the SlotBuilder class — builds slots for scheduling.

### 3.7 Output Formatter Tests
Tests TextFileWriter — formatting and writing the final schedule output.

### 3.8 Integration Tests
Full end-to-end pipeline tests using real fixture files. No mocks.

### 3.9 Main Entry Point Tests
Tests the CLI main() function — correct exit codes, clean stderr, no Python tracebacks.

### 3.10 Behavioural & Completeness Tests
High-level correctness tests for the scheduling algorithm. Verify properties that span multiple classes.

### 3.11 Performance Tests
Verify the 30-second SRS constraint under realistic and maximum load scenarios.

# Test File Structure
```bash
tests/
|── Conftest.py
├── Test_Parsers.py          
├── Test_Domain.py           
├── Test_Validators.py       
├── Test_Checkers.py         
├── Test_Scheduler_Engine.py 
├── Test_SlotBuilder.py
├── Test_Output.py
├── Test_Integration.py      
├── Test_Main.py             
├── Test_Behavioural.py      
├── Test_Performance.py  
├── Test_Application_State.py  
├── Test_Boundary_DTOs.py
├── Test_Data_Cache.py
├── Test_Scheduling_Service.py
├── Test_Screen_Router.py
├── Test_Workers.py
├── Test_Navigation.py
└── fixtures/            
    ├── courses_valid.txt
    ├── courses_no_exams.txt
    ├── periods_valid.txt
    ├── programs_valid.txt
    ├── programs_bad.txt
    └── programs_too_many.txt
```