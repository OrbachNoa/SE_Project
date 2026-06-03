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
from src.application.HybridScheduleResultState import HybridScheduleResultState
from src.data.DiskCacheRepository import DiskCacheRepository
from src.data.FileChangeDetector import FileChangeDetector
from src.data.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.parsers.ParserFactory import ParserFactory
from src.validators.ValidatorPipeline import ValidatorPipeline
from src.writers.textFileWriter import TextFileWriter


def build_controller() -> AppController:
    """Wire the full dependency graph and return a ready-to-use AppController."""

    # --- Shared SQLite repository ---
    # A SINGLE repository instance is shared between the writer side and the
    # reader side. SchedulingService writes generated schedules into it from the
    # background worker, while HybridScheduleResultState reads paged windows back
    # out of it for the output screen. They must be the same object, otherwise
    # the GUI would read from an empty database.
    schedule_repository = SQLiteScheduleRepository()

    # --- State ---
    # The schedule sub-state is the SQLite-backed Hybrid variant so the output
    # screen can page through more results than fit in memory. It is injected
    # into AppState; the input sub-state is created by AppState itself.
    schedule_state = HybridScheduleResultState(repository=schedule_repository)
    state = AppState(schedule_state=schedule_state)

    # --- Services ---
    importer = FileImportService(
        repository=DiskCacheRepository(),
        detector=FileChangeDetector(),
        parser_factory=ParserFactory(),
        validators=ValidatorPipeline(),
        state=state.get_input_state(),
    )
    # SchedulingService now requires the shared repository so the background
    # worker can stream batches of schedules straight into SQLite.
    scheduler = SchedulingService(repository=schedule_repository)
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