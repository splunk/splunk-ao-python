"""ElevenLabs Voice Chatbot with Splunk AO Logging

A tutorial example showing how to:
1. Set up a real-time voice conversation with ElevenLabs Conversational AI
2. Log conversation turns to Splunk AO for observability and tracing

Prerequisites:
- macOS with portaudio installed (brew install portaudio)
- ElevenLabs API key and Agent ID
- Splunk AO API key and project configured
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# ElevenLabs SDK for voice conversations
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

# Splunk AO handler for logging and tracing
from splunk_ao_handler import get_splunk_ao_handler

# =============================================================================
# ELEVENLABS CONVERSATION CALLBACKS
# =============================================================================
#
# ElevenLabs Conversational AI uses callbacks to notify your app when
# events occur during the conversation:
# - User speaks and their speech is transcribed
# - Agent generates and speaks a response
#
# We use these callbacks to log each turn to Splunk AO.
# =============================================================================


def on_agent_response(response: str) -> None:
    """Called when the ElevenLabs agent responds.

    This callback fires after the agent generates a response.
    We log this to Splunk AO to complete the conversation turn trace.
    """
    print(f"\n[AGENT] {response}")

    splunk_ao = get_splunk_ao_handler()
    splunk_ao.log_agent_turn(response)


def on_user_transcript(transcript: str) -> None:
    """Called when user speech is transcribed.

    This callback fires after your speech is converted to text.
    We log this to Splunk AO to start a new conversation turn trace.
    """
    print(f"\n[USER] {transcript}")

    splunk_ao = get_splunk_ao_handler()
    splunk_ao.log_user_turn(transcript)


# =============================================================================
# MAIN CONVERSATION LOOP
# =============================================================================


def run_voice_conversation():
    """Run a voice conversation with ElevenLabs + Splunk AO logging.

    This function:
    1. Initializes the ElevenLabs client and Splunk AO logger
    2. Creates a conversation with audio input/output
    3. Runs until the user presses Ctrl+C
    4. Logs all turns to Splunk AO for observability
    """
    # Load ElevenLabs credentials from environment
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID")

    if not elevenlabs_api_key or not elevenlabs_agent_id:
        print("Error: ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set in .env")
        return

    # Initialize ElevenLabs client with your API key
    client = ElevenLabs(api_key=elevenlabs_api_key)

    # Initialize Splunk AO and start a new session
    splunk_ao = get_splunk_ao_handler()
    session_id = str(uuid.uuid4())
    splunk_ao.start_conversation(session_id)

    print("\n" + "=" * 60)
    print("ElevenLabs Voice Chatbot + Splunk AO Logging")
    print(f"Session ID: {session_id}")
    print("*** USE HEADPHONES to avoid audio feedback loop ***")
    print("Speak into your microphone to talk to the agent")
    print("Press Ctrl+C to end the session")
    print("=" * 60 + "\n")

    # Create the ElevenLabs conversation
    # - DefaultAudioInterface() handles microphone input and speaker output
    # - Callbacks connect events to our Splunk AO logging functions
    conversation = Conversation(
        client=client,
        agent_id=elevenlabs_agent_id,
        requires_auth=True,
        audio_interface=DefaultAudioInterface(),
        callback_agent_response=on_agent_response,
        callback_user_transcript=on_user_transcript,
    )

    # Start the conversation (this begins listening)
    print("[INFO] Starting conversation... Speak now!")
    conversation.start_session()

    # wait for the conversation to end (blocks until Ctrl+C or session ends)
    try:
        conversation.wait_for_session_end()
    except KeyboardInterrupt:
        print("\n[INFO] Ending conversation...")
        conversation.end_session()

    # End the Splunk AO session and flush remaining logs
    splunk_ao.end_conversation()
    print("[INFO] Conversation ended - logs sent to Splunk AO")


if __name__ == "__main__":
    run_voice_conversation()
