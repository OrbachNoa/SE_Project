import sys
from PyQt6.QtWidgets import QApplication

from src.gui.app import App
from src.application.app_controller import AppController
from src.application.application_facade import ApplicationFacade
from src.application.app_state import AppState
from src.application.file_import_service import FileImportService
from src.application.scheduling_service import SchedulingService
from src.application.schedule_export_service import ScheduleExportService
from src.application.view_model_mapper import ViewModelMapper
from src.data.DiskCacheRepository import DiskCacheRepository
from src.data.FileChangeDetector import FileChangeDetector
from src.parsers.ParserFactory import ParserFactory
from src.validators.ValidatorPipeline import ValidatorPipeline
from src.writers.textFileWriter import TextFileWriter


def build_controller() -> AppController:
    """Wire the full dependency graph and return a ready-to-use AppController."""

    # --- State ---
    state = AppState()

    # --- Services ---
    importer = FileImportService(
        repository=DiskCacheRepository(),
        detector=FileChangeDetector(),
        parser_factory=ParserFactory(),
        validators=ValidatorPipeline(),
        state=state.get_input_state(),
    )
    scheduler = SchedulingService()
    exporter  = ScheduleExportService(writer=TextFileWriter())
    mapper    = ViewModelMapper()

    # --- Facade ---
    facade = ApplicationFacade(
        state=state,
        importer=importer,
        scheduler=scheduler,
        exporter=exporter,
        mapper=mapper,
    )

    return AppController(facade)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = build_controller()
    window = App(controller)
    window.start()
    sys.exit(app.exec())