#region Path Setup
import sys
from pathlib import Path

SRC_ROOT     = Path(__file__).resolve().parent        # .../SE_Project/src
PROJECT_ROOT = SRC_ROOT.parent                         # .../SE_Project
for path in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
#endregion

#region Imports
import logging

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
from src.application.errors.ExceptionMapper import default_registry
from src.application.errors.ErrorLogger import ErrorLogger, configure_default_logging
from src.application.state.InputDataState import InputDataState
from src.application.services.FileImportService import FileImportService
from src.application.services.InputCacheService import InputCacheService
from src.application.services.InputDataMerger import InputDataMerger
from src.application.services.SchedulingService import SchedulingService
from src.application.services.ScheduleExportService import ScheduleExportService
from src.application.services.ViewModelMapper import ViewModelMapper
from src.application.state.HybridScheduleResultState import HybridScheduleResultState
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.infrastructure.cache.DiskCacheRepository import DiskCacheRepository
from src.infrastructure.cache.FileChangeDetector import FileChangeDetector
from src.file_io.parsers.ParserFactory import ParserFactory
from gui.core.app import App
from src.application.AppController import AppController
from src.file_io.writers.TextFileWriter import TextFileWriter
#endregion


def install_global_excepthook() -> None:
    """Route otherwise-uncaught GUI exceptions through the central error model.

    Without this, an exception escaping a Qt slot prints a traceback to the
    console and (on some platforms) silently aborts the event loop. Here we map
    it to an AppErrorInfo, log the technical detail, and show the user a clean
    dialog instead of a crash.
    """
    registry = default_registry()
    error_logger = ErrorLogger()

    def _hook(exc_type, exc_value, exc_tb):
        # Let Ctrl-C behave normally rather than popping a dialog.
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        info = registry.map(exc_value, {"source": "gui"})
        error_logger.log(info, cause=exc_value)
        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(None, "Unexpected Error", info.user_message)

    sys.excepthook = _hook


def build_controller() -> AppController:
    """
    Builds and returns the AppController with all dependencies wired.
    
    This function is the main entry point for the application's dependency injection.
    It creates all the necessary services and wires them together to form the AppController.
    """
    schedule_repository = SQLiteScheduleRepository()
    hybrid_state = HybridScheduleResultState(repository=schedule_repository)
    input_state = InputDataState()

    cache_repository = DiskCacheRepository()
    cache_detector   = FileChangeDetector()

    importer = FileImportService(
        cache_service=InputCacheService(cache_repository, cache_detector),
        parser_factory=ParserFactory(),
        merger=InputDataMerger(input_state),
        state=input_state,
    )

    scheduler = SchedulingService(repository=schedule_repository)
    exporter  = ScheduleExportService(writer=TextFileWriter())
    mapper    = ViewModelMapper()

    return AppController(
        importer=importer,
        scheduler=scheduler,
        exporter=exporter,
        mapper=mapper,
        input_state=input_state,
        schedule_state=hybrid_state,
    )


if __name__ == "__main__":
    """
    Main entry point for the application.

    This function is the main entry point for the application.
    It creates all the necessary services and wires them together to form the AppController.
    """
    configure_default_logging(level=logging.INFO)
    install_global_excepthook()
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    controller = build_controller()
    window = App(controller)
    window.start()
    sys.exit(app.exec())