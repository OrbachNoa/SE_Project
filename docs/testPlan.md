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
  * Tests the abstract FileParser base class, three concrete parsers (CoursesFileParser, ExamPeriodsFileParser, ProgramsFileParser), and the ParserFactory registry that creates them. Each parser reads a UTF-8 text file, splits on the $$$$ separator, and returns typed domain objects.

* **Test Domain Model:**
  * Tests the core domain classes: Course, ExamPeriod, ExamSchedule, and ProgramEntry, plus the supporting Semester/Moed/EvalType enums.

* **Test Input Validator:**
  * Tests MaxProgramsValidator (max 5 programs) and ProgramExistenceValidator (only known program codes), the IInputValidator base class's default error messaging, ValidationResult's state tracking, and ValidatorPipeline's aggregation and fail-fast behaviour.

* **Test Conflict Checker:**
  * Tests the fixed IConflictChecker implementations: ProgramYearConflictChecker and MoedOrderChecker. These checkers enforce hard scheduling rules that are always active regardless of user configuration.

* **Test Threshold Checkers:**
  * Tests the configurable threshold checkers: MinDaysBetweenExamsChecker, ElectiveConflictCapChecker, ExamSpanChecker, and MaxExamsPerDayChecker. Each checker is tested for boundary values (below k, exactly k, above k), correct scope filtering, and correct behaviour when disabled. These tests are maintained in a dedicated file separate from Test_Checkers.py, as the two checker families differ in their configuration model.

* **Test Scheduler Engine:**
  * Tests the Scheduler class — the core backtracking engine that generates all valid schedules. Verifies the expected schedule count for simple non-conflicting cases, multiple-solution and impossible-case handling, that every returned schedule is complete, that an injected custom checker is consulted, that a course shared across programs is scheduled once, that only EXAM-evaluated courses are scheduled, and the empty-result base case for a program with no EXAM-eligible courses.

* **Test Slot Builder:**
  * Tests the SlotBuilder class for converting courses and exam periods into Slots — difficulty-based sort ordering, filtering by selected program and exam-relevant evaluation type, candidate-date population from period availability, one slot per moed/semester, and the construction-time guard against a course whose semester has no matching period.

* **Test Observers:**
  * Tests the three IScheduleObserver implementations: CollectingScheduleObserver (in-memory collection), QueueScheduleObserver (batches schedules across a process boundary via a multiprocessing Queue), and StreamingScheduleObserver (writes schedules directly to disk), including their lifecycle and error-handling behaviour.

* **Test Boundary DTOs:**
  * Tests AssignmentDTO and ScheduleDTO for correct field storage and pickling across the process boundary, and ScheduleDTOAdapter for correctly reconstructing the richer domain-like view objects (dates, enums, nested course view) that downstream consumers expect.

* **Test Data Cache:**
  * Tests the input-caching infrastructure: FileChangeDetector for SHA-256 file hashing and change detection, and DiskCacheRepository for persisting a DataCache to and from a pickle file on disk — returning safely instead of crashing when the cache file is missing, corrupted, or unreadable.

* **Test ViewModel Mapper:**
  * Tests the ViewModelMapper class for correct conversion of schedule DTOs and domain objects (Course, ExamPeriod) into the schedule, calendar, program, and period-edit view models consumed by the GUI.

* **Test Metrics:**
  * Tests the five metric functions used to score and rank schedules: min_mandatory_gap, avg_all_courses_gap, peak_elective_conflict, mandatory_span, and max_exams_per_day. Also tests the index-building helpers that these functions rely on.

* **Test Schedule Scorer:**
  * Tests the ScheduleScorer class and its incremental state. Verifies that all five criterion scores are computed correctly for a complete schedule, that lower-is-better criteria are correctly negated, and that the incremental state correctly supports add and pop operations used during backtracking.

* **Test Schedule Reranker:**
  * Tests the rerank() function. Verifies descending ordering by a single criterion, tie-breaking by a second criterion, stability of equal-score entries, and the sentinel value for missing scores.

* **Test Checker Factory:**
  * Tests the build_checkers() function. Verifies that the correct set of checkers is assembled for any combination of active and inactive criteria, that the threshold k is correctly transmitted to each checker, and that the two base checkers are always present regardless of configuration.

* **Test Comparators:**
  * Tests the five IScheduleComparator implementations. Split into two files by direction: Test_Comparators.py covers the higher-is-better comparators (MinMandatoryGapComparator, AvgAllCoursesGapComparator, MandatorySpanComparator) and Test_ComparatorsNegated.py covers the lower-is-better comparators (MaxElectiveConflictsComparator, MaxExamsPerDayComparator). Each comparator is tested for correct ordering, tie stability, and use of the correct criterion.

* **Test Clustering Features:**
  * Tests the individual input-processing components of the clustering pipeline: ScoreFeatureExtractor for correct feature vector extraction from schedule scores, and FeatureNormalizer for correct normalisation to the unit interval including the constant-column edge case.

* **Test Clustering Distance Metrics:**
  * Tests EuclideanDistanceMetric and WeightedEuclideanDistanceMetric. The weighted metric is verified arithmetically against its scaling formula.

* **Test Clustering Algorithms:**
  * Tests KMeansClusteringStrategy for deterministic initialisation, silent k-capping, and correct cluster separation. Tests AutoKSelector for degenerate-case handling and silhouette-based selection. Tests ScheduleSampler for exact-size sampling and full-population passthrough.

* **Test Clustering Service:**
  * Tests the full clustering pipeline: fit() followed by cluster() produces correctly separated groups, cluster summaries remain in original units, and configuration parameters are validated at construction time.

* **Test Error Mapping:**
  * Tests the core exception-to-AppErrorInfo mapping rules in ExceptionMapperRegistry — how raw exceptions (MemoryError, PermissionError, parser ValueError, the domain InfeasibleScheduleError, FileNotFoundError, and unknown exceptions) are mapped to the correct category, severity, recoverable flag, and a stable error code.

* **Test Error Mapping Context:**
  * Tests context-driven error mapping, where a caller-supplied context dict steers ExceptionMapperRegistry's resulting category, severity, and message wording, and tests build_process_error_payload, the equivalent boundary used by worker-process stages.

* **Test File Import Service:**
  * Tests the FileImportService for correct error reporting — verifying that every failed import populates structured AppErrorInfo error details with the correct category, routed through the shared ExceptionMapperRegistry rather than a locally formatted string.

* **Test Text File Writer:**
  * Tests the TextFileWriter's write-failure path — verifying that a write failure propagates as a real OSError rather than being caught and locally reported.

#### 3.1.2 Integration Tests

* **Test Behavioural:**
  * High-level correctness tests for the scheduling algorithm. Verify properties that span multiple classes, including no duplicate schedules, every returned schedule passing every active conflict check, configurable gap and maximum-exams-per-day constraints, impossible-constraint detection, and the full scoring-and-ranking pipeline.

* **Test Feasibility Validator:**
  * Tests ScheduleFeasibilityValidator and the feasibility rules. Verifies that the validator returns an empty list for valid configurations, accumulates errors from multiple violated rules, and that structural rules and threshold-based rules contribute independently to the error list. Also covers the feasibility_bound() method of each configurable threshold checker, verifying that mathematically impossible configurations are detected before the scheduler begins, and that FeasibilityContext.selected_set correctly filters programs when a selection is provided.

* **Test Integration:**
  * Tests integration between parsers, validators, schedulers, and writers. Full end-to-end pipeline tests using real fixture files.

* **Test Application State:**
  * Tests InputDataState for managing loaded courses/periods and serializing them to and from a DataCache, and ScheduleResultState for tracking the generated schedule results and the currently selected one.

* **Test Main:**
  * Tests the CLI main() function — correct exit codes, clean stderr, no Python tracebacks.

* **Test Output:**
  * Tests TextFileWriter.formatSchedule for correct output formatting — zero-padded DD-MM-YYYY dates, fixed Semester/Moed section ordering, instructor name inclusion, date sorting within a section, and that write() creates a file on disk with the expected content.

* **Test Scheduling Service:**
  * Tests the SchedulingService facade for correct slot building and asynchronous schedule generation — including the background process/worker wiring, cancellation, and that a course whose semester has no matching period raises a clear error.

* **Test Hybrid State:**
  * Tests the HybridScheduleResultState class for correct SQLite-backed window management, including efficient page loading, count delegation, and database pagination.

### 3.2 GUI Tests
This field tests the GUI aspect of the system and is devided into Unit Tests and Integration Tests.

#### 3.2.1 Unit Tests

* **Test App Controller:**
  * Tests the AppController class — the application's single entry point for GUI screens — for correct delegation to its importer, scheduler, and exporter collaborators: verifying that load_file, generate_schedules, get_loaded_courses, get_loaded_periods, get_page_info, get_schedule_view, and cancel_scheduling all propagate the correct arguments and return values.

* **Test Cluster Request Worker:**
  * Tests the background cluster request worker to ensure it does not preload heavy sklearn exceptions on import, keeping the startup fast.

* **Test Cluster Worker:**
  * Tests the background worker responsible for computing schedule clusters via IPC.

* **Test Exclusion Model:**
  * Tests the ExclusionModel for managing excluded-date state — adding, removing, and querying excluded dates, and that navigating between periods auto-saves the in-memory edits on the period being left.

* **Test Input Screen Presenter:**
  * Tests the InputScreenPresenter for correct coordination between the InputScreen view and the AppController — verifying file load delegation, import mode forwarding, and course-list refresh after a successful load.

* **Test Output Screen Presenter:**
  * Tests the OutputScreenPresenter for correct counter refresh, solution-bar state (next/prev enabled flags), page loading, calendar rendering from a ScheduleViewModel, background thread lifecycle management on view transitions, PDF and TXT export guards (empty schedule, zero total), and export error handling.

* **Test Schedule Pdf Exporter:**
  * Tests the PDF export error path — verifying that a failure during HTML build or Qt printing is reported through the presenter's error-mapping callback rather than showing the raw exception.

* **Test Sort Worker:**
  * Tests the SortWorker QThread for correct emission of the ready signal with sorted results, correct handling of an empty input list, and that a failure during sorting is reported through the failed signal with a structured error record.

#### 3.2.2 Integration Tests

* **Test GUI:**
  * End-to-end GUI tests using `pytest-qt` (qtbot) that simulate complete user flows headlessly; covering file loading (replace and update modes), program selection, schedule generation, router navigation, dropdown-based PDF export, and full real-pipeline execution with actual parsers and a SQLite repository.

* **Test GUI Integration:**
  * Tests that the ScreenRouter correctly registers, transitions between, and tracks history for the InputScreen and OutputScreen.

* **Test Workers:**
  * Tests the SchedulerWorker QThread and SchedulerProcessRunner concurrency layer; covering IPC message dispatching, crash drainage, graceful cancellation, process termination, and error propagation via the queue.

### 3.3 Performance Tests
This field tests the performance aspect of the system.

* **Test Performance:**
  * Verify the 30-second constraint under realistic and maximum load scenarios. Additional tests cover scoring throughput on large result sets, sort ranking on high-volume collections, full scheduling with all threshold constraints active, and the clustering pipeline on a realistic sample size.

# Test File Structure
```bash
tests/
├── conftest.py
├── fixtures/
│   ├── courses_valid.txt
│   ├── courses_no_exams.txt
│   ├── courses_conflict.txt
│   ├── periods_valid.txt
│   ├── periods_one_day.txt
│   ├── programs_valid.txt
│   ├── programs_single.txt
│   ├── programs_bad_code.txt
│   └── programs_too_many.txt
├── logic/
│   ├── unit/
│   │   ├── Test_Domain.py
│   │   ├── Test_BoundaryDTOs.py
│   │   ├── Test_Checkers.py
│   │   ├── Test_ThresholdCheckers.py
│   │   ├── Test_SlotBuilder.py
│   │   ├── Test_Validators.py
│   │   ├── Test_Parsers.py
│   │   ├── Test_Observers.py
│   │   ├── Test_DataCache.py
│   │   ├── Test_ViewModelMapper.py
│   │   ├── Test_SchedulerEngine.py
│   │   ├── Test_Metrics.py
│   │   ├── Test_ScheduleScorer.py
│   │   ├── Test_ScheduleReranker.py
│   │   ├── Test_CheckerFactory.py
│   │   ├── Test_Comparators.py
│   │   ├── Test_ComparatorsNegated.py
│   │   ├── Test_ClusteringFeatures.py
│   │   ├── Test_ClusteringDistanceMetrics.py
│   │   ├── Test_ClusteringAlgorithms.py
│   │   ├── Test_ClusteringService.py
│   │   ├── Test_ErrorMapping.py
│   │   ├── Test_ErrorMappingContext.py
│   │   ├── Test_FileImportService.py
│   │   └── Test_TextFileWriter.py
│   └── integration/
│       ├── Test_ApplicationState.py
│       ├── Test_SchedulingService.py
│       ├── Test_HybridState.py
│       ├── Test_Behavioural.py
│       ├── Test_FeasibilityValidator.py
│       ├── Test_Integration.py
│       ├── Test_Main.py
│       └── Test_Output.py
├── gui/
│   ├── unit/
│   │   ├── Test_AppController.py
│   │   ├── Test_ClusterRequestWorker.py
│   │   ├── Test_ClusterWorker.py
│   │   ├── Test_ExclusionModel.py
│   │   ├── Test_InputScreenPresenter.py
│   │   ├── Test_OutputScreenPresenter.py
│   │   ├── Test_SchedulePdfExporter.py
│   │   └── Test_SortWorker.py
│   └── integration/
│       ├── Test_App.py
│       ├── Test_GUI.py
│       ├── Test_GuiIntegration.py
│       └── Test_Workers.py
└── performance/
    └── Test_Performance.py
```