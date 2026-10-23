"""SplunkAOLogger must use what another process created when it loses a create race (SAO-18644)."""

import atexit
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from splunk_ao.exceptions import BadRequestError
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.logger.logger import LOST_RACE_LOOKUP_ATTEMPTS
from splunk_ao.projects import ProjectsAPIException

STREAM_EXISTS = b'{"detail": "Log stream demo-stream already exists for project demo-project."}'
PROJECT_EXISTS = '{"detail": "A project with this (name, type) already exists."}'


def make_logger() -> SplunkAOLogger:
    """A logger with no backend set-up. An ingestion hook skips project and stream look-ups in the constructor."""
    logger = SplunkAOLogger(project="demo-project", agent_stream="demo-stream", ingestion_hook=lambda request: None)
    atexit.unregister(logger.terminate)
    logger.project_id = "project-1"
    return logger


@pytest.fixture
def sleep() -> Generator[MagicMock, None, None]:
    with patch("splunk_ao.logger.logger.time.sleep") as mock_sleep:
        yield mock_sleep


@pytest.fixture
def streams() -> Generator[MagicMock, None, None]:
    with patch("splunk_ao.logger.logger.AgentStreams") as client_class:
        yield client_class.return_value


@pytest.fixture
def projects() -> Generator[MagicMock, None, None]:
    with patch("splunk_ao.logger.logger.Projects") as client_class:
        yield client_class.return_value


class TestInitAgentStream:
    def test_existing_stream_is_used_without_creating(self, streams: MagicMock, sleep: MagicMock) -> None:
        streams.get.return_value = MagicMock(id="stream-1")
        logger = make_logger()

        logger._init_agent_stream()

        assert logger.agent_stream_id == "stream-1"
        streams.create.assert_not_called()

    def test_new_stream_is_created(self, streams: MagicMock, sleep: MagicMock) -> None:
        streams.get.return_value = None
        streams.create.return_value = MagicMock(id="stream-2")
        logger = make_logger()

        logger._init_agent_stream()

        assert logger.agent_stream_id == "stream-2"
        streams.get.assert_called_once()
        sleep.assert_not_called()

    def test_lost_race_uses_the_winners_stream(self, streams: MagicMock, sleep: MagicMock) -> None:
        # Given: the first look-up finds nothing, our create is rejected, and the winner's stream is there next
        streams.get.side_effect = [None, MagicMock(id="winner-stream")]
        streams.create.side_effect = BadRequestError(400, STREAM_EXISTS)
        logger = make_logger()

        # When: the logger initializes
        logger._init_agent_stream()

        # Then: it uses the winner's stream and does not raise
        assert logger.agent_stream_id == "winner-stream"
        assert streams.get.call_count == 2
        streams.create.assert_called_once()
        sleep.assert_not_called()

    def test_create_error_is_raised_when_the_stream_never_appears(self, streams: MagicMock, sleep: MagicMock) -> None:
        # Given: a create that fails for a reason other than a lost race, so no stream ever shows up
        error = BadRequestError(400, b'{"detail": "Log stream is not allowed in this project type."}')
        streams.get.return_value = None
        streams.create.side_effect = error
        logger = make_logger()

        # When / Then: the original error comes back, after a bounded number of look-ups
        with pytest.raises(BadRequestError) as raised:
            logger._init_agent_stream()
        assert raised.value is error
        assert streams.get.call_count == 1 + LOST_RACE_LOOKUP_ATTEMPTS
        assert sleep.call_count == LOST_RACE_LOOKUP_ATTEMPTS - 1
        assert logger.agent_stream_id is None

    def test_create_error_is_raised_when_the_second_look_up_fails(self, streams: MagicMock, sleep: MagicMock) -> None:
        # Given: a rejected create and a look-up that then fails
        error = BadRequestError(400, STREAM_EXISTS)
        lookup_failure = RuntimeError("connection reset")
        streams.get.side_effect = [None, lookup_failure]
        streams.create.side_effect = error
        logger = make_logger()

        # When / Then: the create error is raised, with the look-up failure as its cause
        with pytest.raises(BadRequestError) as raised:
            logger._init_agent_stream()
        assert raised.value is error
        assert raised.value.__cause__ is lookup_failure


class TestInitProject:
    def test_existing_project_is_used_without_creating(self, projects: MagicMock, sleep: MagicMock) -> None:
        projects.get.return_value = MagicMock(id="project-1", type="gen_ai")
        logger = make_logger()

        logger._init_project()

        assert logger.project_id == "project-1"
        projects.create.assert_not_called()

    def test_new_project_is_created(self, projects: MagicMock, sleep: MagicMock) -> None:
        projects.get.return_value = None
        projects.create.return_value = MagicMock(id="project-2")
        logger = make_logger()

        logger._init_project()

        assert logger.project_id == "project-2"
        projects.get.assert_called_once()
        sleep.assert_not_called()

    def test_lost_race_uses_the_winners_project(self, projects: MagicMock, sleep: MagicMock) -> None:
        # Given: the first look-up finds nothing, our create is rejected, and the winner's project is there next
        projects.get.side_effect = [None, MagicMock(id="winner-project", type="gen_ai")]
        projects.create.side_effect = ProjectsAPIException(PROJECT_EXISTS)
        logger = make_logger()

        # When: the logger initializes
        logger._init_project()

        # Then: it uses the winner's project and does not raise
        assert logger.project_id == "winner-project"
        projects.create.assert_called_once()

    def test_lost_race_waits_until_the_winner_has_granted_access(self, projects: MagicMock, sleep: MagicMock) -> None:
        # Given: the winner's project is not visible to us for the first two look-ups
        projects.get.side_effect = [None, None, None, MagicMock(id="winner-project", type="gen_ai")]
        projects.create.side_effect = ProjectsAPIException(PROJECT_EXISTS)
        logger = make_logger()

        # When: the logger initializes
        logger._init_project()

        # Then: it waited between look-ups and then used the project
        assert logger.project_id == "winner-project"
        assert sleep.call_count == 2

    def test_winner_project_of_another_type_is_rejected(self, projects: MagicMock, sleep: MagicMock) -> None:
        projects.get.side_effect = [None, MagicMock(id="other", type="protect")]
        projects.create.side_effect = ProjectsAPIException(PROJECT_EXISTS)
        logger = make_logger()

        with pytest.raises(Exception, match="is not a Splunk AO project"):
            logger._init_project()

    def test_create_error_is_raised_when_the_project_never_appears(self, projects: MagicMock, sleep: MagicMock) -> None:
        # Given: a create that fails and a project that never shows up
        error = ProjectsAPIException('{"detail": "Not allowed."}')
        projects.get.return_value = None
        projects.create.side_effect = error
        logger = make_logger()

        # When / Then: the original error comes back, after a bounded number of look-ups
        with pytest.raises(ProjectsAPIException) as raised:
            logger._init_project()
        assert raised.value is error
        assert projects.get.call_count == 1 + LOST_RACE_LOOKUP_ATTEMPTS
        assert sleep.call_count == LOST_RACE_LOOKUP_ATTEMPTS - 1
