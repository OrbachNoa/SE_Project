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
Tests are divided into 3 main layers: Logic, GUI, and Performance.

### 3.1 Logic Tests
This field tests the core logic of the system and is divided into Unit Tests and Integration Tests.

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

* **Test Base Excel Writer:**
  * Validates BaseExcelWriter.write() in src/file_io/writers/BaseExcelWriter.py: the falsy-path no-op, real workbook/table/header/row generation (verified by re-reading the saved .xlsx with openpyxl), the empty-rows edge case, and column-width auto-sizing against None/blank cells.

* **Test Cached Input Loader:**
  * Tests the input loader's cache-hit and cache-miss/changed logic, confirming it parses files only when necessary and updates the cache.

* **Test Checkers:**
  * Tests the individual threshold checkers and their feasibility bounds.

* **Test Cluster Request Translator:**
  * Tests the ClusterRequestTranslator for safely parsing UI cluster requests.

* **Test Clustering Coordinator:**
  * Tests the prepare()'s ValueError guards (empty population, no readable score vectors) and its happy path populating is_prepared/flat_criteria; cluster()'s RuntimeError when called before prepare(); and run_on_schedules()'s ValueError on an empty schedule list plus its happy path. The repository collaborator is a duck-typed mock (count_scores/read_score_vectors); ClusterConfig/ClusteringService run for real, exercising this environment's pure-Python clustering fallback (no sklearn required).

* **Test Comparators Negated:**
  * Tests the negated schedule comparators (e.g. MaxExamsPerDay) for correct descending sort orders.

* **Test Constraint Metadata:**
  * Verifies the ConstraintMeta dataclass construction and the exact field values (field_name, min_k, max_k, default_k, unit) declared for each optional scheduling rule in the CONSTRAINTS tuple.

* **Test CPU Topology:**
  * Tests the deterministic coverage of the platform-independent parts of CPU topology detection — the non-Windows short circuit for _windows_pcore_groups(), the psutil-backed logical/physical core counters, the HT-arithmetic fallback grouping for both a recognizable hybrid layout and a non-hybrid layout, and recommended_worker_count()'s reservation behaviour on the hybrid path versus the full-physical-count behaviour on the non-hybrid path.

* **Test Cube Collector Observer:**
  * Verifies on_schedule_found() builds one WorkUnit per call with the correct seed_dates extracted from the schedule's assignments, that collected units accumulate across multiple calls, and that the remaining IScheduleObserver methods (on_progress, should_cancel, on_finished, on_error) are pure no-ops that never raise.

* **Test Domain:**
  * Tests the core domain classes (Course, ExamPeriod, ExamSchedule) for state correctness.

* **Test Error Logger:**
  * Tests the errorLogger message formatting, severity mapping, and default configuration logic.

* **Test Extended Feature Computer:**
  * Tests the ExtendedFeatureComputer for correct matrix aggregations and edge cases.

* **Test File Validator:**
  * Validates validate_language, validate_file_exists, validate_file_not_empty, and validate_all_files in src/file_io/validators/FileValidator.py.

* **Test Heuristic Request Parser:**
  * Tests the dependency-free keyword parsing of free-text clustering requests into a validated ClusterConfig, covering criterion keyword matching (English and Hebrew), emphasis-word weight boosting, K extraction from digit and spelled-out number patterns, the ValueError-to-default() fallback, and both language branches of the interpretation sentence.

* **Test Input Cache Service:**
  * Tests the try_load()'s four branches (no cache, mismatched file-set keys, detector reports a change, true cache hit) and persist()'s serialize-then-save pipeline, including the hashes attached to the saved DataCache.

* **Test Input Data Merger:**
  * Tests the REPLACE mode delegating straight to state.replace_courses/ replace_periods, UPDATE mode merging courses (dedup by courseId, incoming wins) and periods (dedup by (semester, moed), incoming wins), and an unsupported mode raising ValueError. A real InputDataState is used (not a mock) so the merge logic genuinely runs end to end against production state methods.

* **Test Mandatory Span Gap Rule:**
  * Verifies the early-exit branches (no config, no exam_span, no mandatory gap), the satisfiable case where two mandatory-exam groups can coexist, and the infeasible case where the forced earliest/latest dates of two mandatory-exam groups in the same (program, year) cohort can never satisfy the minimum gap given the required exam span.

* **Test Packed Schedule Codec:**
  * Tests the binary pack/unpack round-trips for compact schedule batch blobs, the 16-bit size guards, magic-byte validation, selective row unpacking, schedule encoding into slot-aligned date indexes, and row-to-DTO reconstruction including its defensive fallback for a course with no program entries.

* **Test Parsers:**
  * Tests the Parsers component.

* **Test Queue Schedule Observer:**
  * Tests the constructor validation, on_progress duplicate suppression, _reserve_result_slot's global result-limit gating with cancel_event tripping, the run_id wrapping behaviour of _wrap() across every outgoing message kind, and on_error forwarding a dict payload as-is. These cases are additive to the existing buffering/flush/lifecycle coverage in Test_Observers.py and do not duplicate it.

* **Test Queue Work Source:**
  * Tests the get_next()'s cancel-event short circuit, its retry loop across one or more queue.Empty timeouts before a real item arrives, and its None-sentinel stop signal.

* **Test SQLite Schedule Repository:**
  * Tests the persistence of compressed schedule batches, paging, lazy score updates, and dynamic sort indexing.

* **Test Schedule Csv Formatter:**
  * Validates format_schedule_csv() in src/file_io/formatters/ScheduleCsvFormatter.py — the falsy-input short circuit, date sorting, instructor fallback, HTML/subtitle cleanup, tooltip-derived metadata, evaluation-type suffix, and the Programs column fallback placeholder.

* **Test Schedule Export Service:**
  * Tests the save() creating the parent directory before delegating to the injected writer's write() with an adapted DTO, and format() delegating to the writer's formatSchedule().

* **Test Search Space Partitioner:**
  * Verifies SearchSpacePartitioner.partition() against an empty slot list, a small realistic slot list that splits into the desired number of units with plausible seed_dates, and the pruning of dead units (seeds whose continuation has zero valid children). Also covers WorkUnit as a small frozen dataclass: construction and field access.

* **Test Selected Program Index:**
  * Verifies construction (__init__, from_slots), program-membership checks (includes), per-course/per-slot entry lookups including the entries_for_slot fallback path, has_entries_for_course, and the slot-grouping methods (slots_by_program_year, slots_by_program, slots_by_program_year_semester_moed) together with the internal _group_slots caching behavior.

* **Test Sort Criteria:**
  * Verifies label_for() behavior for resolving criterion labels.

* **Test Validators:**
  * Tests the Validators component.

* **Test View Model Mapper:**
  * Tests the View Model Mapper component.

#### 3.1.2 Integration Tests

* **Test Behavioural:**
  * Tests the high-level correctness tests for the scheduling algorithm. Verify properties that span multiple classes, including no duplicate schedules, every returned schedule passing every active conflict check, configurable gap and maximum-exams-per-day constraints, impossible-constraint detection, and the full scoring-and-ranking pipeline.

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
This field tests the GUI aspect of the system and is divided into Unit Tests and Integration Tests.

#### 3.2.1 Unit Tests

* **Test App Controller:**
  * Tests the AppController class — the application's single entry point for GUI screens — for correct delegation to its importer, scheduler, and exporter collaborators: verifying that load_file, generate_schedules, get_loaded_courses, get_loaded_periods, get_page_info, get_schedule_view, and cancel_scheduling all propagate the correct arguments and return values.

* **Test Cluster Workers:**
  * Tests the background cluster workers for correct off-thread behaviour: ClusterWorker running the clustering coordinator's prepare()/cluster(k) lifecycle and mapping failures to clean user messages via the error registry, and ClusterRequestWorker keeping its module cheap to import (no eager scikit-learn load at startup).

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

* **Test Input Import Presenter:**
  * Tests the InputImportPresenter for managing file selection dialogs, import mode toggling (replace vs update), and reporting import success/failure to the user.

* **Test Constraints Presenter:**
  * Tests the ConstraintsPresenter for updating configuration settings into the controller and notifying the view of unsaved changes.

* **Test Generation Presenter:**
  * Tests the GenerationPresenter for initiating the scheduling process, reacting to early-finish signals, and managing cancellation requests.

* **Test Solution Paging Presenter:**
  * Tests the SolutionPagingPresenter for paginating through large sets of generated schedules, caching bounds safely, and updating the UI navigation controls.

* **Test Sort Lifecycle Presenter:**
  * Tests the SortLifecyclePresenter for safely launching and retiring the background SortWorker thread during schedule re-ordering.

* **Test Cluster Presenters:**
  * Tests the cluster presenter components (Overview, Detail, Compare, Calendar Overlay) for correct cluster UI logic: ClusterOverviewPresenter handling K-value inputs and routing to comparison/detail views, ClusterDetailPresenter paginating schedules within a family and handling expired sessions, ClusterComparePresenter fetching side-by-side representations, and ClusterCalendarOverlayPresenter merging mutually shared schedule items versus family-specific ones.

* **Test Period Navigator:**
  * Tests the PeriodNavigator widget logic for safely moving forward and backward through available exam periods while ensuring bounds are respected.

#### 3.2.2 Integration Tests

* **Test GUI:**
  * Tests the end-to-end GUI tests using `pytest-qt` (qtbot) that simulate complete user flows headlessly; covering file loading (replace and update modes), program selection, schedule generation, router navigation, dropdown-based PDF export, and full real-pipeline execution with actual parsers and a SQLite repository.

* **Test Workers:**
  * Tests the SchedulerWorker QThread and SchedulerProcessRunner concurrency layer; covering IPC message dispatching, crash drainage, graceful cancellation, process termination, and error propagation via the queue.

### 3.3 Performance Tests
This field tests the performance aspect of the system.

* **Test Performance:**
  * Tests the verify the 30-second constraint under realistic and maximum load scenarios. Additional tests cover scoring throughput on large result sets, sort ranking on high-volume collections, full scheduling with all threshold constraints active, and the clustering pipeline on a realistic sample size.

# Test File Structure
```bash
tests/
├── fixtures
│   ├── courses_conflict.txt
│   ├── courses_no_exams.txt
│   ├── courses_valid.txt
│   ├── periods_one_day.txt
│   ├── periods_valid.txt
│   ├── programs_bad_code.txt
│   ├── programs_single.txt
│   ├── programs_too_many.txt
│   └── programs_valid.txt
├── gui
│   ├── integration
│   │   ├── Test_GUI.py
│   │   └── Test_Workers.py
│   ├── unit
│   │   ├── Test_AppController.py
│   │   ├── Test_ClusterPresenters.py
│   │   ├── Test_ClusterWorkers.py
│   │   ├── Test_ConstraintsPresenter.py
│   │   ├── Test_ExclusionModel.py
│   │   ├── Test_GenerationPresenter.py
│   │   ├── Test_InputImportPresenter.py
│   │   ├── Test_InputScreenPresenter.py
│   │   ├── Test_OutputScreenPresenter.py
│   │   ├── Test_PeriodNavigator.py
│   │   ├── Test_SchedulePdfExporter.py
│   │   ├── Test_SolutionPagingPresenter.py
│   │   ├── Test_SortLifecyclePresenter.py
│   │   └── Test_SortWorker.py
│   └── conftest.py
├── logic
│   ├── integration
│   │   ├── Test_ApplicationState.py
│   │   ├── Test_Behavioural.py
│   │   ├── Test_FeasibilityValidator.py
│   │   ├── Test_HybridState.py
│   │   ├── Test_Integration.py
│   │   ├── Test_Main.py
│   │   ├── Test_Output.py
│   │   └── Test_SchedulingService.py
│   └── unit
│       ├── Test_BaseExcelWriter.py
│       ├── Test_BoundaryDTOs.py
│       ├── Test_CachedInputLoader.py
│       ├── Test_CheckerFactory.py
│       ├── Test_Checkers.py
│       ├── Test_ClusterRequestTranslator.py
│       ├── Test_ClusteringAlgorithms.py
│       ├── Test_ClusteringCoordinator.py
│       ├── Test_ClusteringDistanceMetrics.py
│       ├── Test_ClusteringFeatures.py
│       ├── Test_ClusteringService.py
│       ├── Test_Comparators.py
│       ├── Test_ComparatorsNegated.py
│       ├── Test_ConstraintMetadata.py
│       ├── Test_CpuTopology.py
│       ├── Test_CubeCollectorObserver.py
│       ├── Test_DataCache.py
│       ├── Test_Domain.py
│       ├── Test_ErrorLogger.py
│       ├── Test_ErrorMapping.py
│       ├── Test_ErrorMappingContext.py
│       ├── Test_ExtendedFeatureComputer.py
│       ├── Test_FileImportService.py
│       ├── Test_FileValidator.py
│       ├── Test_HeuristicRequestParser.py
│       ├── Test_InputCacheService.py
│       ├── Test_InputDataMerger.py
│       ├── Test_MandatorySpanGapRule.py
│       ├── Test_Metrics.py
│       ├── Test_Observers.py
│       ├── Test_PackedScheduleCodec.py
│       ├── Test_Parsers.py
│       ├── Test_QueueScheduleObserver.py
│       ├── Test_QueueWorkSource.py
│       ├── Test_SQLiteScheduleRepository.py
│       ├── Test_ScheduleCsvFormatter.py
│       ├── Test_ScheduleExportService.py
│       ├── Test_ScheduleReranker.py
│       ├── Test_ScheduleScorer.py
│       ├── Test_SchedulerEngine.py
│       ├── Test_SearchSpacePartitioner.py
│       ├── Test_SelectedProgramIndex.py
│       ├── Test_SlotBuilder.py
│       ├── Test_SortCriteria.py
│       ├── Test_TextFileWriter.py
│       ├── Test_ThresholdCheckers.py
│       ├── Test_Validators.py
│       └── Test_ViewModelMapper.py
├── performance
│   └── Test_Performance.py
└── conftest.py
```