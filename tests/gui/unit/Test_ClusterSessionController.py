"""Unit tests for ClusterSessionController — the clustering session behind
the four cluster GUI screens.

ClusterSessionController is the real class under test here (mirroring how
Test_AppController.py tests the real AppController); its collaborators
(schedule state, mapper, input state, exporter) are mocked instead.

Scope   : Extended-metrics recomputation on demand, the Qt-signal observer
          seam that ties AppController's schedule_results_changed to session
          invalidation, and the prepare()-cache-compatibility gate that
          decides whether a config change requires re-fitting the clustering
          vectors.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<scenario>
TC-IDs  : TC-CSC-001..004

Conventions mirror tests/gui/unit/Test_AppController.py: each test carries a
unique TC-ID in the comment block above it, and uses the shared `qapp`
fixture (tests/conftest.py) since AppController exposes PyQt signals.
"""
import dataclasses

import pytest
from unittest.mock import MagicMock

from src.application.AppController import AppController
from src.application.services.ClusterSessionController import ClusterSessionController
from src.application.dto.ScheduleDTO import AssignmentDTO, ScheduleDTO
from src.logic.clustering.ExtendedFeatureComputer import MAX_REST_DAYS
from src.logic.clustering.ClusterConfig import ClusterConfig

pytestmark = pytest.mark.usefixtures("qapp")


# ===========================================================================
# TC-CSC-001: cluster metric details recompute extended scores on demand. The
# repository initially contains placeholder zeros for extended columns, but
# the metrics dialog must show values computed from the concrete schedule.
#
# Moved from Test_AppController.py (formerly TC-AC-024) — clustering session
# state and get_cluster_schedule_scores now live on ClusterSessionController,
# not AppController.
# ===========================================================================
def test_get_cluster_schedule_scores_recomputes_extended_metrics():
    # Arrange
    dto = ScheduleDTO(
        assignments=[
            AssignmentDTO(
                course_id="CS101",
                course_name="Algorithms",
                instructor="I1",
                date="2026-01-01",
                semester="FALL",
                moed="ALEPH",
                program_requirements=[("P1", "OBLIGATORY")],
            ),
            AssignmentDTO(
                course_id="CS102",
                course_name="Databases",
                instructor="I2",
                date="2026-01-10",
                semester="FALL",
                moed="ALEPH",
                program_requirements=[("P1", "OBLIGATORY")],
            ),
        ],
        total_assignments=2,
        scores={MAX_REST_DAYS: 0.0},
    )
    repo = MagicMock()
    repo.get_schedules_by_ids.return_value = [dto]
    schedule_state = MagicMock()
    schedule_state.get_repository.return_value = repo

    session = ClusterSessionController(schedule_state, MagicMock(), MagicMock(), MagicMock())
    session._cluster_coordinator = MagicMock()
    session._cluster_coordinator.gidx_at.return_value = 42
    cluster = MagicMock()
    cluster.member_indices = [0]
    session._cluster_run = MagicMock()
    session._cluster_run.result.get_cluster.return_value = cluster

    # Act
    scores = session.get_cluster_schedule_scores(0, 0)

    # Assert
    assert scores[MAX_REST_DAYS] == -9.0
    repo.update_extended_scores.assert_called_once()
    assert repo.update_extended_scores.call_args[0][0] == [42]
    assert repo.update_extended_scores.call_args[0][1][0][MAX_REST_DAYS] == -9.0


# ===========================================================================
# TC-CSC-002: AppController.schedule_results_changed is the observer seam
# that decouples the two controllers (see module docstring in
# ClusterSessionController.py). A new schedule run must invalidate the
# cached clustering session -- coordinator/run/interpretation cleared -- but
# _active_k must survive, so re-entering the cluster screen re-uses the same
# K the user was looking at instead of silently landing on a different one.
# ===========================================================================
def test_schedule_results_changed_invalidates_cluster_session():
    # Arrange
    controller = AppController(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    session = ClusterSessionController(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    session._cluster_coordinator = MagicMock()
    session._cluster_run = MagicMock()
    session._active_k = 5
    session._cluster_interpretation = "grouped by exam load"
    controller.schedule_results_changed.connect(session.invalidate_clustering)

    # Act
    controller.schedule_results_changed.emit()

    # Assert
    assert session._cluster_coordinator is None
    assert session._cluster_run is None
    assert session._cluster_interpretation == ""
    assert session._active_k == 5


# ===========================================================================
# TC-CSC-003: _prepare_compatible must reject the cache when any field that
# feeds prepare()/fit_vectors() differs -- serving stale vectors for a
# changed criterion/weight/normalizer/seed would silently mis-cluster.
# ===========================================================================
def test_prepare_compatible_false_on_criteria_weights_normalizer_or_seed_change():
    # Arrange
    session = ClusterSessionController(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    base = ClusterConfig()

    # Act / Assert
    assert not session._prepare_compatible(base, dataclasses.replace(base, criteria=("MAX_EXAMS_PER_DAY",)))
    assert not session._prepare_compatible(base, dataclasses.replace(base, weights={"MIN_MANDATORY_GAP": 2.0}))
    assert not session._prepare_compatible(base, dataclasses.replace(base, normalizer="minmax"))
    assert not session._prepare_compatible(base, dataclasses.replace(base, seed=7))


# ===========================================================================
# TC-CSC-004: k and k_mode are consumed only by cluster(), not prepare(), so
# a config that changes only those must still be treated as cache-compatible
# -- otherwise every K change would force an unnecessary re-prepare/re-fit.
# ===========================================================================
def test_prepare_compatible_true_when_only_k_or_k_mode_differs():
    # Arrange
    session = ClusterSessionController(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    base = ClusterConfig(k=3, k_mode="fixed")

    # Act / Assert
    assert session._prepare_compatible(base, dataclasses.replace(base, k=5))
    assert session._prepare_compatible(base, dataclasses.replace(base, k_mode="auto"))
    assert session._prepare_compatible(base, dataclasses.replace(base, k=5, k_mode="auto"))
