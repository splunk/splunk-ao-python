import asyncio
from agent import SimpleAgent
from agent_framework.llm.openai_provider import OpenAIProvider
from agent_framework.llm.models import LLMConfig
from splunk_ao import splunk_ao_context
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def main():
    # Ensure Splunk AO environment variables are set
    if not os.getenv("SPLUNK_AO_API_KEY"):
        print("Warning: SPLUNK_AO_API_KEY not set. Splunk AO logging will be disabled.")

    # Prompt user for input
    industry = input("Enter an industry: ")
    audience = input("Enter a target audience: ")
    random_word = input("Enter a random word: ")

    # Set up LLM provider
    llm_provider = OpenAIProvider(config=LLMConfig(model="gpt-4", temperature=0.7))

    # Create agent instance
    agent = SimpleAgent(llm_provider=llm_provider)

    # Create the task description that includes getting HackerNews context
    task = (
        f"First, get some inspiration from recent HackerNews stories, then "
        f"generate a startup pitch for a {industry} company targeting {audience} "
        f"that includes the word '{random_word}'. Make the pitch creative and "
        f"incorporate relevant trends from the HackerNews stories."
    )

    # Run the agent within Splunk AO context for proper trace management
    with splunk_ao_context():
        result = await agent.run(task)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
