"""
Test suite for GenerationPresenter.

Scope   : Verifies schedule generation lifecycle, cancellation, and navigation.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-GEN-001..005
"""
from unittest.mock import MagicMock
from src.gui.features.input.GenerationPresenter import GenerationPresenter

# TC-GUI-GEN-001
# GenerationPresenter must block generation and show error if validation fails.
def test_generation_presenter_blocks_invalid_start():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = GenerationPresenter(view, controller, router, "output")
    show_error = MagicMock()
    
    # Act
    presenter.on_generate_clicked(["prog1"], lambda: False, show_error)
    
    # Assert
    show_error.assert_called_once()
    controller.generate_schedules.assert_not_called()


# TC-GUI-GEN-002
# GenerationPresenter must start generation and update UI if validation passes.
def test_generation_presenter_starts_generation():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = GenerationPresenter(view, controller, router, "output")
    
    # Act
    presenter.on_generate_clicked(["prog1"], lambda: True, MagicMock())
    
    # Assert
    view.set_running_mode.assert_called_with(True, "Initialising scheduler...")
    view.set_view_results_visible.assert_called_with(False)
    controller.generate_schedules.assert_called_once_with(["prog1"])


# TC-GUI-GEN-003
# GenerationPresenter must cancel scheduling and reset UI.
def test_generation_presenter_cancels_generation():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = GenerationPresenter(view, controller, router, "output")
    
    # Act
    presenter.on_cancel_clicked()
    
    # Assert
    controller.cancel_scheduling.assert_called_once()
    view.set_running_mode.assert_called_with(False, "")
    view.set_progress_text.assert_called_with("")
    view.mark_inputs_dirty.assert_called_once()


# TC-GUI-GEN-004
# GenerationPresenter must navigate to output on early results or search finished with results.
def test_generation_presenter_navigates_to_output():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = GenerationPresenter(view, controller, router, "output")
    
    # Act
    presenter.on_early_results_ready()
    
    # Assert
    view.set_view_results_visible.assert_called_with(True)
    router.show.assert_called_once_with("output")
    
    # Ensure it only navigates once
    router.reset_mock()
    presenter.on_search_finished()
    router.show.assert_not_called()


# TC-GUI-GEN-005
# GenerationPresenter must show error if search finishes with no results.
def test_generation_presenter_handles_no_results():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = GenerationPresenter(view, controller, router, "output")
    presenter._result_count = MagicMock(return_value=0)
    
    # Act
    presenter.on_search_finished()
    
    # Assert
    view.set_validation_message.assert_called_once()
    router.show.assert_not_called()
