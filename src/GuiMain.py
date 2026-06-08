import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

SRC_ROOT     = Path(__file__).resolve().parent        # .../SE_Project/src
PROJECT_ROOT = SRC_ROOT.parent                         # .../SE_Project
for path in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from src.application.state.AppState import AppState
from src.application.ApplicationFacade import ApplicationFacade
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
from gui.app import App
from src.application.AppController import AppController
from src.file_io.writers.TextFileWriter import TextFileWriter


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