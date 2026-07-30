from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from splunk_ao.experiment import Experiment
from splunk_ao.shared.base import SyncState

FIXED_PROJECT_ID = str(uuid4())
FIXED_EXPERIMENT_ID = str(uuid4())


def _make_status(progress_percent: float, *, failed: bool = False) -> MagicMock:
    """Build a status mock with the given progress, is_complete, and is_failed."""
    status = MagicMock()
    status.overall_progress = progress_percent
    status.is_complete = progress_percent >= 100.0
    status.is_failed = failed
    return status


def _make_experiment() -> Experiment:
    exp = Experiment._create_empty()
    exp.id = FIXED_EXPERIMENT_ID
    exp.project_id = FIXED_PROJECT_ID
    exp.name = "test-experiment"
    exp._set_state(SyncState.SYNCED)
    return exp


class TestMonitorProgress:
    @patch("splunk_ao.experiment.Experiment.get_status")
    @patch("splunk_ao.experiment.sleep", return_value=None)
    def test_completes_when_status_reaches_100(self, mock_sleep, mock_get_status):
        # Given: an experiment that progresses through 0%, 50%, then 100%
        mock_get_status.side_effect = [_make_status(0.0), _make_status(50.0), _make_status(100.0)]
        exp = _make_experiment()

        # When: monitoring progress until completion
        exp.monitor_progress(poll_interval_seconds=0.0)

        # Then: get_status is polled until 100% is reached
        assert mock_get_status.call_count == 3

    @patch("splunk_ao.experiment.Experiment.get_status")
    @patch("splunk_ao.experiment.sleep", return_value=None)
    def test_already_complete_on_first_poll(self, mock_sleep, mock_get_status):
        # Given: an experiment that is already at 100% on the first poll
        mock_get_status.return_value = _make_status(100.0)
        exp = _make_experiment()

        # When: monitoring progress
        exp.monitor_progress(poll_interval_seconds=0.0)

        # Then: get_status is called once and sleep is never called
        assert mock_get_status.call_count == 1
        mock_sleep.assert_not_called()

    @patch("splunk_ao.experiment.Experiment.get_status")
    @patch("splunk_ao.experiment.sleep", return_value=None)
    def test_uses_poll_interval_seconds(self, mock_sleep, mock_get_status):
        # Given: an experiment that completes on the second poll
        mock_get_status.side_effect = [_make_status(0.0), _make_status(100.0)]
        exp = _make_experiment()

        # When: monitoring with a custom poll interval
        exp.monitor_progress(poll_interval_seconds=5.0)

        # Then: sleep is called once with the specified interval
        mock_sleep.assert_called_once_with(5.0)

    def test_raises_without_experiment_id(self):
        # Given: an experiment without an id
        exp = Experiment._create_empty()
        exp.id = None
        exp.project_id = FIXED_PROJECT_ID

        # When/Then: monitoring raises ValueError about the missing experiment id
        with pytest.raises(ValueError, match="Experiment ID is not set"):
            exp.monitor_progress()

    def test_raises_without_project_id(self):
        # Given: an experiment without a project_id
        exp = Experiment._create_empty()
        exp.id = FIXED_EXPERIMENT_ID
        exp.project_id = None

        # When/Then: monitoring raises ValueError about the missing project id
        with pytest.raises(ValueError, match="Project ID is not set"):
            exp.monitor_progress()

    @patch("splunk_ao.experiment.Experiment.get_status")
    @patch("splunk_ao.experiment.sleep", return_value=None)
    def test_deprecated_job_id_warns(self, mock_sleep, mock_get_status):
        # Given: an experiment that is already complete, and a caller passing the deprecated job_id
        mock_get_status.return_value = _make_status(100.0)
        exp = _make_experiment()

        # When/Then: monitor_progress emits a DeprecationWarning when job_id is supplied
        with pytest.warns(DeprecationWarning, match="job_id"):
            exp.monitor_progress(job_id="some-old-job-id")

    @patch("splunk_ao.experiment.Experiment.get_status")
    @patch("splunk_ao.experiment.sleep", return_value=None)
    def test_raises_runtime_error_on_failed_experiment(self, mock_sleep, mock_get_status):
        # Given: an experiment that enters a failed state on the second poll
        mock_get_status.side_effect = [_make_status(30.0), _make_status(30.0, failed=True)]
        exp = _make_experiment()

        # When/Then: monitor_progress raises RuntimeError instead of polling forever
        with pytest.raises(RuntimeError, match="failed state"):
            exp.monitor_progress(poll_interval_seconds=0.0)

    @patch("splunk_ao.experiment.Experiment.get_status")
    @patch("splunk_ao.experiment.sleep", return_value=None)
    def test_raises_timeout_error_when_deadline_exceeded(self, mock_sleep, mock_get_status):
        # Given: an experiment stuck at 50% forever with a very short timeout
        mock_get_status.return_value = _make_status(50.0)
        exp = _make_experiment()

        # When/Then: monitor_progress raises TimeoutError
        # Use a tiny timeout and a non-zero interval so the real clock eventually trips it
        with pytest.raises(TimeoutError, match="did not complete within"):
            exp.monitor_progress(poll_interval_seconds=0.001, timeout_seconds=0.0)
