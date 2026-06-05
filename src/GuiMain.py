import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

SRC_ROOT     = Path(__file__).resolve().parent        # .../SE_Project/src
PROJECT_ROOT = SRC_ROOT.parent                         # .../SE_Project
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
from gui.app import App
from application.AppController import AppController
from file_io.writers.TextFileWriter import TextFileWriter


def build_controller() -> AppController:
    schedule_repository = SQLiteScheduleRepository()
    hybrid_state = HybridScheduleResultState(repository=schedule_repository)
    state = AppState(schedule_state=hybrid_state)

    input_state      = state.get_input_state()
    cache_repository = DiskCacheRepository()
    cache_detector   = FileChangeDetector()

    importer = FileImportService(
        cache_service=InputCacheService(cache_repository, cache_detector),
        parser_factory=ParserFactory(),
        validators=ValidatorPipeline(),
        merger=InputDataMerger(input_state),
        state=input_state,
    )

    scheduler = SchedulingService(repository=schedule_repository)
    exporter  = ScheduleExportService(writer=TextFileWriter())
    mapper    = ViewModelMapper()

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