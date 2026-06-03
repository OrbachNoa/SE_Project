"""gui_main.py — The Composition Root for the Graphical User Interface (GUI) application.

Instantiates all decoupled services, structural state components, and parsing factories.
Wires them together via structural Dependency Injection (DI) to assemble the execution facade.
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from application.state.AppState import AppState
from application.ApplicationFacade import ApplicationFacade
from application.services.FileImportService import FileImportService
from application.services.InputCacheService import InputCacheService
from application.services.InputDataMerger import InputDataMerger
from application.services.SchedulingService import SchedulingService
from application.services.ScheduleExportService import ScheduleExportService
from application.services.ViewModelMapper import ViewModelMapper
from application.state.HybridScheduleResultState import HybridScheduleResultState
from infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
from infrastructure.cache.DiskCacheRepository import DiskCacheRepository
from infrastructure.cache.FileChangeDetector import FileChangeDetector
from file_io.parsers.ParserFactory import ParserFactory
from file_io.validators.ValidatorPipeline import ValidatorPipeline
from gui.App import App
from application.AppController import AppController
from file_io.writers.TextFileWriter import TextFileWriter


def build_app() -> tuple[QApplication, App]:
    """
    Assembles the structural dependency graph of the entire application.
    Constructs layers from data storage nodes up to the top view-controller components.
    """
    qt_app = QApplication(sys.argv)

    # ── 1. Storage & State Layer Initialization ──────────────────────────────
    # Instantiate the atomic SQLite repository used as a virtual memory overflow buffer
    schedule_repository = SQLiteScheduleRepository()          
    
    # Wrap the repository into a paged navigation state reader interface proxy
    hybrid_state = HybridScheduleResultState(schedule_repository)

    # Compose the root runtime state as the unified single source of truth
    state = AppState(schedule_state=hybrid_state)     
    
    # ── 2. Structural Infrastructure Services ────────────────────────────────
    # Initialize file loading service pipeline with local validation configurations
    input_state = state.get_input_state()
    cache_repository = DiskCacheRepository()
    cache_detector = FileChangeDetector()
    importer = FileImportService(
        cache_service=InputCacheService(cache_repository, cache_detector),
        parser_factory=ParserFactory(),
        validators=ValidatorPipeline([]),
        merger=InputDataMerger(input_state),
        state=input_state,
    )
    
    # ── 3. Facade Architecture Composition ────────────────────────────────────
    # Build the application facade, injecting the shared repository to the scheduling service
    facade = ApplicationFacade(
        state=state,
        importer=importer,
        scheduler=SchedulingService(schedule_repository),  # Injects the safe disk storage link to the background engine
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
