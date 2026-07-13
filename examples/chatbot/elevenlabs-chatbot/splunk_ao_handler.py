"""Splunk AO Handler for ElevenLabs Voice Chatbot

Provides observability for AI applications by capturing:
- Sessions: Group related conversations (e.g., a user's chat session)
- Traces: Individual request-response cycles within a session
- Spans: Detailed steps within a trace (e.g., LLM calls, tool use)

This allows you to monitor conversation quality, debug issues, and
analyze patterns in your AI application.
"""

import os
from typing import Optional

from splunk_ao import SplunkAOLogger, Message, MessageRole


class SplunkAOHandler:
    """Handles Splunk AO logging for voice conversations.

    Captures each conversation turn (user speech -> agent response) as a trace,
    with the LLM interaction logged as a span within that trace.
    """

    def __init__(self):
        self._logger: Optional[SplunkAOLogger] = None
        self._session_id: Optional[str] = None
        self._turn_count = 0

        # Load Splunk AO config from environment
        self._project_name = os.getenv("SPLUNK_AO_PROJECT", "elevenlabs-voice-poc")
        self._log_stream = os.getenv("SPLUNK_AO_LOG_STREAM", "voice-chatbot")

        self._init_logger()

    def _init_logger(self):
        """Initialize the Splunk AO Logger.

        The logger connects to a specific project and log stream in Splunk AO.
        Log streams help organize logs by environment (dev, staging, prod)
        or by feature area.
        """
        try:
            self._logger = SplunkAOLogger(
                project=self._project_name,
                log_stream=self._log_stream,
            )
            print(f"[SPLUNK_AO] Logger initialized for project: {self._project_name}")
        except Exception as e:
            print(f"[SPLUNK_AO] Logger init failed: {e}")

    def start_conversation(self, session_id: str):
        """Start a new conversation session in Splunk AO.

        A session groups all the turns of a single conversation together,
        making it easy to view the full conversation history in the Splunk AO UI.
        """
        self._session_id = session_id
        self._turn_count = 0

        if self._logger:
            # external_id links this session to your own session tracking
            self._logger.start_session(name=f"Voice-{session_id[:8]}", external_id=session_id)
            print(f"[SPLUNK_AO] Started session: {session_id[:8]}")

    def log_user_turn(self, transcript: str) -> None:
        """Log when the user speaks.

        This starts a new trace for this conversation turn.
        The trace captures the full request-response cycle.
        """
        self._turn_count += 1
        self._last_user_input = transcript

        if self._logger:
            try:
                # Each turn gets its own trace for clear organization
                self._logger.start_trace(input=transcript, name=f"Turn-{self._turn_count}")
            except Exception as e:
                print(f"[SPLUNK_AO] Trace start error: {e}")

    def log_agent_turn(self, response: str) -> None:
        """Log when the agent responds.

        This adds an LLM span to capture the model interaction,
        then concludes the trace with the final output.
        """
        if self._logger:
            try:
                user_input = getattr(self, "_last_user_input", "")

                # Log the LLM interaction as a span
                # Even though ElevenLabs handles the actual LLM call,
                # we log it here for visibility into the conversation flow
                self._logger.add_llm_span(
                    input=user_input,
                    output=Message(content=response, role=MessageRole.assistant),
                    model="elevenlabs-agent",
                )

                # Conclude the trace with the final response
                self._logger.conclude(output=response)

                # Flush to send logs to Splunk AO immediately
                self._logger.flush()
            except Exception as e:
                print(f"[SPLUNK_AO] Logging error: {e}")

    def end_conversation(self):
        """End the conversation session and cleanup.

        Ensures all logs are flushed and the session is properly closed.
        """
        if self._logger:
            try:
                self._logger.flush()
                self._logger.clear_session()
                print(f"[SPLUNK_AO] Session ended ({self._turn_count} turns)")
            except Exception as e:
                print(f"[SPLUNK_AO] Cleanup error: {e}")

        self._session_id = None
        self._turn_count = 0


# Singleton instance for the Splunk AO handler
_splunk_ao_handler: Optional[SplunkAOHandler] = None


def get_splunk_ao_handler() -> SplunkAOHandler:
    """Get or create the Splunk AO handler singleton."""
    global _splunk_ao_handler
    if _splunk_ao_handler is None:
        _splunk_ao_handler = SplunkAOHandler()
    return _splunk_ao_handler
