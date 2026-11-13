import logging
import threading
from collections.abc import Callable
from typing import ClassVar

from splunk_ao.deployment import resolve_deployment
from splunk_ao.exporter import resolve_routing
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.schema.metrics import LocalMetricConfig
from splunk_ao.utils.env_helpers import _get_mode_or_default

_logger = logging.getLogger(__name__)


class SplunkAOLoggerSingleton:
    """
    A singleton class that manages a collection of SplunkAOLogger instances.

    This class ensures that only one instance exists across the application and
    provides a thread-safe way to retrieve or create SplunkAOLogger clients based on
    the given 'project' and 'agent_stream' parameters. If the parameters are not provided,
    the class attempts to read the values from the environment variables
    SPLUNK_AO_PROJECT and SPLUNK_AO_AGENT_STREAM, falling back to the standalone defaults.

    Loggers are cached under a tuple key built from the calling thread's name, the logger
    mode, the deployment, and the resolved project and agent stream (or experiment)
    identity, plus the distributed trace and span IDs when present. Because the thread name
    is part of the key, instances are never shared across threads.
    """

    _instance = None  # Class-level attribute to hold the singleton instance.
    _lock = threading.Lock()  # Lock for thread-safe instantiation and operations.
    _splunk_ao_loggers: ClassVar[dict[tuple[str, ...], SplunkAOLogger]] = {}  # Cache for loggers.

    def __new__(cls) -> "SplunkAOLoggerSingleton":
        """
        Override __new__ to ensure only one instance of SplunkAOLoggerSingleton is created.

        Returns
        -------
        SplunkAOLoggerSingleton
            The singleton instance.
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:  # Double-checked locking.
                    cls._instance = super().__new__(cls)
                    # Initialize the logger dictionary in the new instance.
                    cls._instance._splunk_ao_loggers = {}
        return cls._instance

    @staticmethod
    def _get_key(
        project: str | None,
        project_id: str | None,
        agent_stream: str | None,
        agent_stream_id: str | None,
        mode: str,
        experiment_id: str | None = None,
        ingestion_hook_id: int | None = None,
    ) -> tuple[str, ...]:
        """
        Generate a deployment-aware key from routing and tracing parameters.

        Parameters
        ----------
        project: (Optional[str])
            The project name.
        project_id: (Optional[str])
            The project ID.
        agent_stream: (Optional[str])
            The log stream name.
        agent_stream_id: (Optional[str])
            The log stream ID.
        experiment_id: (Optional[str])
            The experiment ID.
        mode:
            The logger mode.
        ingestion_hook_id: (Optional[int])
            Identity of the temporary ingestion hook compatibility path.

        Returns
        -------
        Tuple[str, ...]
            A tuple key used for caching.
        """
        _logger.debug("current thread is %s", threading.current_thread().name)

        # SplunkAOLoggerSingleton must NOT be shared across different threads
        current_thread_name = threading.current_thread().name
        key = (current_thread_name, mode)

        if ingestion_hook_id is not None:
            base_key: tuple[str, ...] = (
                *key,
                "hook",
                project or project_id or "",
                experiment_id or agent_stream or agent_stream_id or "",
            )
        else:
            deployment = resolve_deployment()
            routing = resolve_routing(
                deployment,
                project=project,
                project_id=project_id,
                agent_stream=agent_stream,
                agent_stream_id=agent_stream_id,
                experiment_id=experiment_id,
            )
            project_key = (
                f"name:{routing.project_name}" if routing.project_name is not None else f"id:{routing.project_id or ''}"
            )
            if routing.experiment_id is not None:
                destination_key = f"experiment:{routing.experiment_id}"
            elif routing.agent_stream_name is not None:
                destination_key = f"name:{routing.agent_stream_name}"
            else:
                destination_key = f"id:{routing.agent_stream_id or ''}"
            base_key = (*key, deployment.value, project_key, destination_key)

        if ingestion_hook_id is not None:
            base_key = (*base_key, str(ingestion_hook_id))

        return base_key

    @staticmethod
    def _get_base_keys(
        project: str | None,
        project_id: str | None,
        agent_stream: str | None,
        agent_stream_id: str | None,
        mode: str,
        experiment_id: str | None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        standard_key = SplunkAOLoggerSingleton._get_key(
            project, project_id, agent_stream, agent_stream_id, mode, experiment_id
        )
        hook_key = SplunkAOLoggerSingleton._get_key(
            project, project_id, agent_stream, agent_stream_id, mode, experiment_id, ingestion_hook_id=0
        )[:-1]
        return standard_key, hook_key

    def get(
        self,
        *,
        project: str | None = None,
        project_id: str | None = None,
        agent_stream: str | None = None,
        agent_stream_id: str | None = None,
        experiment_id: str | None = None,
        mode: str | None = None,
        local_metrics: list[LocalMetricConfig] | None = None,
        ingestion_hook: Callable | None = None,
    ) -> SplunkAOLogger:
        """
        Retrieve an existing SplunkAOLogger or create a new one if it does not exist.

        This method first computes the key from the project and agent_stream parameters,
        checks if a logger exists in the cache, and if not, creates a new SplunkAOLogger.
        The creation and caching are done in a thread-safe manner.

        Parameters
        ----------
        project (Optional[str], optional)
            The project name. Defaults to None.
        agent_stream (Optional[str], optional)
            The agent stream name. Defaults to None.
        experiment_id (Optional[str], optional)
            The experiment ID. Defaults to None.
        local_metrics (Optional[list[LocalScorerConfig]], optional)
            Local scorers to run on traces/spans.
            Only used if initializing a new logger, ignored otherwise.  Defaults to None.

        Returns
        -------
        SplunkAOLogger
            An instance of SplunkAOLogger corresponding to the key.
        """
        # Check for mode from environment variable if not provided
        mode = _get_mode_or_default(mode)

        # Compute the key based on provided parameters or environment variables.
        key = SplunkAOLoggerSingleton._get_key(
            project,
            project_id,
            agent_stream,
            agent_stream_id,
            mode,
            experiment_id,
            ingestion_hook_id=id(ingestion_hook) if ingestion_hook else None,
        )

        # First check without acquiring lock for performance.
        if key in self._splunk_ao_loggers:
            return self._splunk_ao_loggers[key]

        # Acquire lock for thread-safe creation of new logger.
        with self._lock:
            # Double-check in case another thread created the logger while waiting.
            if key in self._splunk_ao_loggers:
                return self._splunk_ao_loggers[key]

            # Prepare initialization arguments, only including non-None values.
            splunk_ao_client_init_args = {
                "project": project,
                "project_id": project_id,
                "agent_stream": agent_stream,
                "agent_stream_id": agent_stream_id,
                "experiment_id": experiment_id,
                "local_metrics": local_metrics,
                "mode": mode,
                "ingestion_hook": ingestion_hook,
            }
            # Create the logger with filtered kwargs.
            logger = SplunkAOLogger(**{k: v for k, v in splunk_ao_client_init_args.items() if v is not None})

            # Cache the newly created logger.
            if logger:
                self._splunk_ao_loggers[key] = logger
            return logger

    def get_existing(
        self,
        *,
        project: str | None = None,
        project_id: str | None = None,
        agent_stream: str | None = None,
        agent_stream_id: str | None = None,
        experiment_id: str | None = None,
        mode: str | None = None,
    ) -> SplunkAOLogger | None:
        """Return a cached standard logger without constructing one."""
        key = SplunkAOLoggerSingleton._get_key(
            project, project_id, agent_stream, agent_stream_id, _get_mode_or_default(mode), experiment_id
        )
        return self._splunk_ao_loggers.get(key)

    def reset(
        self,
        project: str | None = None,
        agent_stream: str | None = None,
        experiment_id: str | None = None,
        mode: str | None = None,
        *,
        project_id: str | None = None,
        agent_stream_id: str | None = None,
    ) -> None:
        """
        Reset (terminate and remove) the SplunkAOLogger instances matching the given key.

        Matching is by key prefix, so a logger's per-trace and hook-backed variants are
        included. With no arguments this covers the current thread's loggers at the default
        mode and resolved routing, not every cached instance; use ``reset_all()`` for that.

        Terminating drains completed spans before shutting the exporter down. Spans still
        open at that point are discarded rather than exported.

        Parameters
        ----------
        project (Optional[str], optional)
            The project name. Defaults to None.
        project_id (Optional[str], optional)
            The project ID. Defaults to None.
        agent_stream (Optional[str], optional)
            The agent stream name. Defaults to None.
        agent_stream_id (Optional[str], optional)
            The agent stream ID. Defaults to None.
        experiment_id (Optional[str], optional)
            The experiment ID. Defaults to None.
        mode (Optional[str], optional)
            The logger mode. Defaults to SPLUNK_AO_MODE env var, or "batch" if not set.
        """
        mode = _get_mode_or_default(mode)

        with self._lock:
            base_keys = SplunkAOLoggerSingleton._get_base_keys(
                project, project_id, agent_stream, agent_stream_id, mode, experiment_id
            )
            keys_to_remove = [
                key
                for key in self._splunk_ao_loggers
                if any(key[: len(base_key)] == base_key for base_key in base_keys)
            ]
            for key in keys_to_remove:
                self._splunk_ao_loggers[key].terminate()
                del self._splunk_ao_loggers[key]

    def reset_all(self) -> None:
        """Reset (terminate and remove) all SplunkAOLogger instances."""
        with self._lock:
            # Terminate and clear all logger instances.
            for logger in self._splunk_ao_loggers.values():
                logger.terminate()
            self._splunk_ao_loggers.clear()

    def flush(
        self,
        project: str | None = None,
        agent_stream: str | None = None,
        experiment_id: str | None = None,
        mode: str | None = None,
        *,
        project_id: str | None = None,
        agent_stream_id: str | None = None,
    ) -> None:
        """
        Drain completed spans for the matching cached SplunkAOLogger instances.

        With no arguments, drains the loggers registered for the current thread whose mode and
        resolved project/agent stream match the active defaults — not every cached logger.
        Passing a project or agent stream narrows this to the loggers matching that key.

        Open spans are left unconcluded, except for hook-backed loggers, which conclude any
        open spans on the active trace before handing it off.

        Draining is not a shutdown: exporters stay open and the loggers remain cached. Use
        ``reset()`` or ``reset_all()`` to terminate and evict them; otherwise each logger
        terminates via its ``atexit`` hook at interpreter exit.

        Parameters
        ----------
        project (Optional[str], optional)
            The project name. Defaults to None.
        project_id (Optional[str], optional)
            The project ID. Defaults to None.
        agent_stream (Optional[str], optional)
            The agent stream name. Defaults to None.
        agent_stream_id (Optional[str], optional)
            The agent stream ID. Defaults to None.
        experiment_id (Optional[str], optional)
            The experiment ID. Defaults to None.
        mode (Optional[str], optional)
            The logger mode. Defaults to SPLUNK_AO_MODE env var, or "batch" if not set.
        """
        mode = _get_mode_or_default(mode)

        with self._lock:
            base_keys = SplunkAOLoggerSingleton._get_base_keys(
                project, project_id, agent_stream, agent_stream_id, mode, experiment_id
            )
            keys_to_flush = [
                key
                for key in self._splunk_ao_loggers
                if any(key[: len(base_key)] == base_key for base_key in base_keys)
            ]
            for key in keys_to_flush:
                self._splunk_ao_loggers[key].flush()

    def flush_all(self) -> None:
        """
        Drain completed spans for every cached SplunkAOLogger instance.

        Open spans are left unconcluded, except for hook-backed loggers, which conclude any
        open spans on the active trace before handing it off.

        Draining is not a shutdown: exporters stay open and the loggers remain cached. Use
        ``reset_all()`` to terminate and evict them; otherwise each logger terminates via its
        ``atexit`` hook at interpreter exit.
        """
        with self._lock:
            for logger in self._splunk_ao_loggers.values():
                logger.flush()

    def get_all_loggers(self) -> dict[tuple[str, ...], SplunkAOLogger]:
        """
        Retrieve a copy of the dictionary containing all active loggers.

        Returns
        -------
        Dict[Tuple[str, ...], SplunkAOLogger]:
            A dictionary mapping keys to their corresponding SplunkAOLogger instances.
        """
        # Return a shallow copy of the loggers dictionary to prevent external modifications.
        return dict(self._splunk_ao_loggers)
