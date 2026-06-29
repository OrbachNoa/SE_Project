# System Architecture

## UML Class Diagram

The following diagram illustrates the core structure, domain models, parsers, validators, and the scheduler engine of the system.

**Version 1.0:**
![UML Diagram](./UmlDiagram.png)

**Version 2.0:**
https://yuval-keren.github.io/

**Version 3.0:**


## Architecture

* **`src/models/` (Domain):** Contains the core data structures and Enumerations.
* **`src/file_io/` (Input Management):** Contains all logic regarding reading files and writing output schedules while performing validations and parsing.
  * `validators/` (Validation): Ensures data integrity before the engine runs.
  * `parsers/` (Parsing): Parses the input files into structured data.
  * `writers/` (Writing): Writes the final schedule to a file.
  * `formatters/` (Formatting): Formats schedules for different output formats.
* **`src/logic/` (Engine):** The brain of the system.
  * `Scheduler.py`: Main class that runs the scheduling algorithm.
  * `SlotBuilder.py`: Contains the logic for building slots for schedule creation.
  * `ScheduleFeasibilityValidator.py`: Validates that a schedule is feasible before being accepted.
  * `checkers/`: Contains the logic for checking scheduling constant constraints and user defined constraints.
    * `config/`: Contains configuration for the checkers.
  * `observers/`: Contains observer classes for notifying the GUI of the scheduling process.
  * `clustering/`: Contains the clustering logic for grouping similar schedules by similarity metrics and user defined preferences.
    * `llm/`: Contains LLM-based components for intelligent cluster labeling for user preference clustering.
  * `comparators/`: Contains logic for comparing and scoring schedules.
  * `feasibility/`: Contains domain-level feasibility rules applied before scheduling.
  * `indexes/`: Contains index structures for efficient schedule lookups.
  * `parallel/`: Contains logic for parallel scheduling execution.
* **`src/infrastructure/` (Infrastructure):** Contains the infrastructure layer logic.
  * `cache/`: Contains the cache logic for input data tracking.
  * `concurrency/`: Contains the concurrency logic for scheduling.
  * `repositories/`: Contains the repository logic for data created persistency.
* **`src/application/` (Application):** Contains the application layer logic.
  * `AppController.py`: Manages the application state and dispatches commands.
  * `ImportBoundary.py`: Import input data using the facade.
  * `dto/` (Data Transfer Objects): Contains the data transfer objects used to pass data between the GUI and the engine.
  * `services/` (Services): Contains the service logic that manages the domain objects.
  * `state/` (State Management): Contains the state management logic.
  * `viewmodels/` (View Models): Contains the view model definitions used by the GUI.
  * `errors/` (Error Handling): Contains the application-level error handling logic.
* **`src/gui/` (GUI):** Contains the GUI logic.
  * `common/` (Common): Contains the common GUI logic.
    * `components/`: Contains reusable GUI components.
    * `helpers.py`: Contains helper functions for the GUI.
    * `BusyCursorGuard.py`: Context manager that shows a busy cursor during long operations.
    * `ScheduleExportMixin.py`: Mixin providing schedule export functionality to screens.
  * `features/` (Features): Contains the GUI feature modules.
    * `input/`: Contains the input feature logic.
      * `widgets/`: Input-specific widgets.
    * `output/`: Contains the output feature logic.
      * `widgets/`: Output-specific widgets.
      * `workers/`: Background workers.
    * `clusters/`: Contains the cluster exploration feature logic.
      * `widgets/`: Cluster-specific widgets.
  * `core/` (Core): Contains the core GUI logic.
    * `styles/`: Contains all style definitions for the GUI.
    * `app.py`: The main application window.
    * `screen.py`: Defines the different screens of the application.
    * `ScreenRouter.py`: Used for routing between screens based on user actions.
* **`src/main.py` (CLI Entry Point):** Contains the command-line interface entry point.
* **`src/GuiMain.py` (GUI Entry Point):** Contains the GUI entry point and application bootstrapping logic.
* **`src/config.py` (Configuration):** Contains global configuration constants and settings.
