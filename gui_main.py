"""gui_main.py — The Composition Root for the Graphical User Interface (GUI) application.

Instantiates all decoupled services, structural state components, and parsing factories.
Wires them together via structural Dependency Injection (DI) to assemble the execution facade.
"""
import sys

from PyQt6.QtWidgets import QApplication

from src.application.app_state import AppState
from src.application.application_facade import ApplicationFacade
from src.application.file_import_service import FileImportService
from src.application.scheduling_service import SchedulingService
from src.application.schedule_export_service import ScheduleExportService
from src.application.view_model_mapper import ViewModelMapper
from src.application.import_mode import ImportMode
from src.application.HybridScheduleResultState import HybridScheduleResultState
from src.data.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.data.DiskCacheRepository import DiskCacheRepository
from src.data.FileChangeDetector import FileChangeDetector
from src.parsers.ParserFactory import ParserFactory
from src.validators.ValidatorPipeline import ValidatorPipeline
from src.gui.app import App
from src.application.app_controller import AppController
from src.writers.textFileWriter import TextFileWriter


def build_app() -> tuple[QApplication, App]:
    """
    Assembles the structural dependency graph of the entire application.
    Constructs layers from data storage nodes up to the top view-controller components.
    """
    qt_app = QApplication(sys.argv)

    # ── 1. Storage & State Layer Initialization ──────────────────────────────
    # Instantiate the atomic SQLite repository used as a virtual memory overflow buffer
    repository = SQLiteScheduleRepository()          
    
    # Wrap the repository into a paged navigation state reader interface proxy
    hybrid_state = HybridScheduleResultState(repository)

    # Compose the root runtime state as the unified single source of truth
    state = AppState(schedule_state=hybrid_state)     
    
    # ── 2. Structural Infrastructure Services ────────────────────────────────
    # Initialize file loading service pipeline with local validation configurations
    importer = FileImportService(
        repository=DiskCacheRepository(),
        detector=FileChangeDetector(),
        parser_factory=ParserFactory(),
        validators=ValidatorPipeline([]),
        state=state.get_input_state(),
    )
    
    # ── 3. Facade Architecture Composition ────────────────────────────────────
    # Build the application facade, injecting the shared repository to the scheduling service
    facade = ApplicationFacade(
        state=state,
        importer=importer,
        scheduler=SchedulingService(repository),  # Injects the safe disk storage link to the background engine
        exporter=ScheduleExportService(writer=TextFileWriter()),
        mapper=ViewModelMapper(),
    )
    
    # ── 4. UI Layer Instantiation ────────────────────────────────────────────
    # Bind the unified application facade inside a thin mediator controller node
    controller = AppController(facade)
    
    # Generate the main visualization window view bound to its specific controller
    window = App(controller)

    return qt_app, window


def main() -> None:
    """Application main runtime entry point."""
    qt_app, window = build_app()
    window.start()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()