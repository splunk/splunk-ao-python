import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

from splunk_ao.agent_streams import AgentStream
from splunk_ao.projects import Project
from splunk_ao.resources.models import ExperimentResponse, ProjectType
from splunk_ao.resources.models.log_stream_response import LogStreamResponse
from splunk_ao.resources.models.project_create_response import ProjectCreateResponse
from splunk_ao.resources.models.task_type import TaskType


def setup_mock_projects_client(mock_projects_client: Mock):
    now = datetime.datetime.now()
    mock_instance = mock_projects_client.return_value
    mock_instance.get = Mock(
        return_value=Project(
            ProjectCreateResponse(
                id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a",
                type_=ProjectType.GEN_AI,
                name="test",
                created_at=now,
                updated_at=now,
            )
        )
    )
    mock_instance.create = Mock(
        return_value=Project(
            ProjectCreateResponse(
                id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a",
                type_=ProjectType.GEN_AI,
                name="test",
                created_at=now,
                updated_at=now,
            )
        )
    )
    return mock_instance


def setup_mock_logstreams_client(mock_logstreams_client: Mock):
    now = datetime.datetime.now()
    mock_instance = mock_logstreams_client.return_value
    mock_instance.get = Mock(
        return_value=AgentStream(
            LogStreamResponse(
                id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9b",
                project_id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a",
                name="test",
                created_at=now,
                updated_at=now,
            )
        )
    )
    mock_instance.create = Mock(
        return_value=AgentStream(
            LogStreamResponse(
                id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9b",
                project_id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a",
                name="test",
                created_at=now,
                updated_at=now,
            )
        )
    )
    return mock_instance


def setup_mock_experiments_client(mock_experiment_client: Mock):
    now = datetime.datetime.now()
    mock_instance = mock_experiment_client.return_value
    mock_instance.get = Mock(
        return_value=ExperimentResponse(
            id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a",
            project_id="6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a",
            name="test",
            created_at=now,
            updated_at=now,
            task_type=TaskType.VALUE_16,
        )
    )
    return mock_instance


def setup_mock_traces_client(mock_traces_client: Mock):
    now = datetime.datetime.now()
    mock_instance = mock_traces_client.return_value
    mock_instance.get_project_by_name = Mock(return_value={"id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a")})
    mock_instance.get_log_stream_by_name = Mock(return_value={"id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9b")})
    mock_instance.ingest_traces = AsyncMock(return_value={})
    mock_instance.ingest_spans = AsyncMock(return_value={})
    mock_instance.update_trace = AsyncMock(return_value={})
    mock_instance.update_span = AsyncMock(return_value={})
    mock_instance.create_session = AsyncMock(
        return_value={
            "id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9c"),
            "name": "test",
            "previous_session_id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9e"),
            "external_id": "test",
            "project_id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9a"),
            "project_name": "test project",
            "log_stream_id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9b"),
        }
    )
    mock_instance.get_sessions = AsyncMock(
        return_value={"starting_token": 0, "limit": 100, "paginated": False, "records": [], "num_records": 0}
    )
    mock_instance.get_trace = AsyncMock(
        return_value={
            "id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9d"),
            "name": "test-trace",
            "type": "trace",
            "input": "test-input",
            "output": None,
            "created_at": now,
            "updated_at": now,
            "user_metadata": {},
            "spans": [],
            "metrics": {},
        }
    )
    mock_instance.get_span = AsyncMock(
        return_value={
            "id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9e"),
            "name": "test-workflow-span",
            "type": "workflow",
            "input": "test-input",
            "output": None,
            "created_at": now,
            "updated_at": now,
            "user_metadata": {},
            "metrics": {},
            "parent_id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9d"),
            "trace_id": UUID("6c4e3f7e-4a9a-4e7e-8c1f-3a9a3a9a3a9d"),
        }
    )

    return mock_instance
