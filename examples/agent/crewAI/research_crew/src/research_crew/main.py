#!/usr/bin/env python
# src/research_crew/main.py
import os

from dotenv import load_dotenv

from research_crew.crew import ResearchCrew
from splunk_ao.handlers.crewai.handler import CrewAIEventListener

load_dotenv()

# Create output directory if it doesn't exist
os.makedirs("output", exist_ok=True)


def run() -> None:
    # Create the event listener for Splunk AO CrewAI integration
    CrewAIEventListener()

    """
    Run the research crew.
    """
    inputs = {"topic": "Artificial Intelligence in Healthcare"}

    # Create and run the crew
    result = ResearchCrew().crew().kickoff(inputs=inputs)

    # Print the result
    print("\n\n=== FINAL REPORT ===\n\n")
    print(result.raw)

    print("\n\nReport has been saved to output/report.md")


if __name__ == "__main__":
    run()
