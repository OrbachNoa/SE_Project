#region Path Setup
import sys
from pathlib import Path

SRC_ROOT     = Path(__file__).resolve().parent        # .../SE_Project/src
PROJECT_ROOT = SRC_ROOT.parent                         # .../SE_Project
for path in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
#endregion

from dotenv import load_dotenv
load_dotenv()

#region Imports
import logging

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import qInstallMessageHandler
from src.application.errors.ExceptionMapper import default_registry
from src.application.errors.ErrorLogger import ErrorLogger, configure_default_logging
from src.application.state.InputDataState import InputDataState
from src.application.services.FileImportService import FileImportService
from src.application.services.InputCacheService import InputCacheService
from src.application.services.InputDataMerger import InputDataMerger
from src.application.services.SchedulingService import SchedulingService
from src.application.services.ScheduleExportService import ScheduleExportService
from src.application.services.ViewModelMapper import ViewModelMapper
from src.application.services.ClusterSessionController import ClusterSessionController
from src.application.state.HybridScheduleResultState import HybridScheduleResultState
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.logic.clustering.ExtendedFeatureComputer import ALL_EXTENDED_FEATURES
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


# Substrings of known-cosmetic Qt warnings that carry no actionable information
# and would otherwise print on every launch. Mixing pixel-based `font-size` in
# our QSS with native Windows widget styling makes Qt's style engine read a
# point size off a pixel-only font during the first style polish pass, which
# is always -1 by Qt's own convention (point size is unset when pixel size is
# used) — harmless, but noisy. Anything else still reaches stderr as usual.
_SUPPRESSED_QT_WARNINGS = ("QFont::setPointSize",)


def install_qt_message_filter() -> None:
    """Drop known-cosmetic Qt log lines; pass every other message through."""

    def _handler(_msg_type, _context, message: str) -> None:
        if any(s in message for s in _SUPPRESSED_QT_WARNINGS):
            return
        print(message, file=sys.stderr)

    qInstallMessageHandler(_handler)


def build_controller() -> tuple[AppController, ClusterSessionController]:
    """
    Builds and returns the AppController and ClusterSessionController, fully wired.

    This function is the main entry point for the application's dependency injection.
    It creates all the necessary services and wires them together to form the two
    controllers: the AppController (scheduling / input / lifecycle) and the
    ClusterSessionController (the clustering session used by the cluster screens).
    """
    # Clustering's extra score columns are wired in here, at the composition
    # root, rather than imported inside the repository itself.
    schedule_repository = SQLiteScheduleRepository(extra_score_criteria=ALL_EXTENDED_FEATURES)
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
    # Spawn the persistent worker-process pool now, in the background, so the
    # OS-process / interpreter cold-start cost lands while the user is loading
    # files instead of on their first "Generate" click.
    scheduler.warm_up_async()
    exporter  = ScheduleExportService(writer=TextFileWriter())
    mapper    = ViewModelMapper()

    controller = AppController(
        importer=importer,
        scheduler=scheduler,
        exporter=exporter,
        mapper=mapper,
        input_state=input_state,
        schedule_state=hybrid_state,
    )

    # The clustering session lives in its own controller, wired with the same
    # collaborators AppController already holds. AppController does not know
    # about it: it only emits schedule_results_changed when a run starts or
    # finishes, and we connect that here to the cluster session's invalidation
    # (observer seam) so the two stay decoupled.
    cluster_controller = ClusterSessionController(
        schedule_state=hybrid_state,
        mapper=mapper,
        input_state=input_state,
        exporter=exporter,
    )
    controller.schedule_results_changed.connect(cluster_controller.invalidate_clustering)

    # Same idea as the scheduler pool warm-up above, applied to the
    # clustering engine: pre-import it in the background so the Clusters
    # screen opens instantly later, without paying that cost at launch for
    # sessions that never open it.
    controller.warm_up_clustering_async()
    return controller, cluster_controller


if __name__ == "__main__":
    """
    Main entry point for the application.

    This function is the main entry point for the application.
    It creates all the necessary services and wires them together to form the AppController.
    """
    configure_default_logging(level=logging.INFO)
    install_global_excepthook()
    install_qt_message_filter()
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    controller, cluster_controller = build_controller()
    window = App(controller, cluster_controller)
    window.start()
    sys.exit(app.exec())