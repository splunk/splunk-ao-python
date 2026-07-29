# Getting Started: Monitoring LangChain Agents with Splunk AO

This guide will walk you through setting up a Python project that uses [LangChain](https://python.langchain.com/) to build an AI agent, and [Splunk AO](https://www.rungalileo.io/) to monitor and log your agent's activity.
---

## 1. Prerequisites

- **Python 3.8+** installed on your system.
- A Splunk AO account and API key (see [Splunk AO docs](https://docs.rungalileo.io/) for how to get one).
- An OpenAI API key (for using OpenAI models with LangChain).

---

## 2. Install Required Packages

Open a terminal, create a virtual environment and install the required packages:

```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- `langchain` and `langchain-openai` are for building and running the agent.
- `python-dotenv` is for loading environment variables (API keys).
- `galileo` is for Splunk AO monitoring.

---

## 3. Set Up Environment Variables

Copy the existing `.env.example` file, and rename it to `.env` in your project directory. 

```
SPLUNK_AO_API_KEY=your-splunk-ao-api-key             # Your Splunk AO API key.
SPLUNK_AO_PROJECT=your-splunk-ao-project-name        # Your Splunk AO project name.
SPLUNK_AO_AGENT_STREAM=your-splunk-ao-log-stream       # The name of the log stream you want to use for logging.

# Provide the console url below if you are using a custom deployment, and not using app.galileo.ai
# SPLUNK_AO_CONSOLE_URL=your-splunk-ao-console-url

OPENAI_API_KEY=your-openai-api-key
```

- Replace `your-openai-api-key`, `your-splunk-ao-project-name`, and `your-splunk-ao-log-stream` with your actual values.
- If you are using a custom deployment of Splunk AO, set `SPLUNK_AO_CONSOLE_URL` to the URL of your Splunk AO deployment.
- This keeps your credentials secure and out of your code.

---

## 4. Create Your Agent Script

Create a file called `main.py` and add the following code:

```python
from dotenv import load_dotenv
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from splunk_ao import splunk_ao_context
from splunk_ao.handlers.langchain import SplunkAOCallback
import os

# 1. Load environment variables (API keys)
load_dotenv()

# 2. Define a simple tool for the agent to use
@tool
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}! 👋"

# 3. Set up Splunk AO monitoring context
with splunk_ao_context(project="langchain-docs", agent_stream="my_log_stream"):
    # 4. Initialize the agent with the Splunk AO callback for monitoring
    agent = initialize_agent(
        tools=[greet],
        llm=ChatOpenAI(model="gpt-4", temperature=0.7, callbacks=[SplunkAOCallback()]),
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # 5. Run the agent and print the response
    if __name__ == "__main__":
        result = agent.invoke({"input": "Say hello to Erin"})
        print(f"\nAgent Response:\n{result}")
```

---

### Explanation of Each Step

1. **Load environment variables:**  
   This loads your API keys from the `.env` file so you don't have to hard-code them.

2. **Define a tool:**  
   Tools are functions your agent can use. Here, we define a simple `greet` tool.

3. **Set up Splunk AO context:**  
   The `splunk_ao_context` context manager ensures all logs are tagged with your chosen project and log stream in Splunk AO.

4. **Initialize the agent:**  
   - The agent is set up with your tool, an OpenAI LLM, and the `SplunkAOCallback` for monitoring.
   - The callback automatically logs all agent activity to Splunk AO.

5. **Run the agent:**  
   - The agent is asked to "Say hello to Erin".
   - The response is printed to your terminal.

---

## 5. Run Your Script

In your terminal, run:

```sh
python main.py
```

You should see output like:

```
Agent Response:
Hello, Erin! 👋
```

---

## 6. View Logs in Splunk AO

- Log in to your Splunk AO dashboard.
- Navigate to the project (`langchain-docs`) and log stream (`my_log_stream`) you specified.
- You should see logs for your agent run, including:
  - The input prompt
  - The agent's reasoning steps
  - Tool usage
  - The final answer

---

## 7. Troubleshooting

- **No logs in Splunk AO?**
  - Double-check your API keys and project/log stream names.
  - Ensure your `.env` file is in the same directory as your script.
- **Errors about traces not being concluded?**
  - Make sure you are not using both the `@log` decorator and the `SplunkAOCallback` at the same time.
  - Only use the `SplunkAOCallback` for agent monitoring.

---

## 8. Customizing Your Agent

- **Add more tools:**  
  Define more functions with the `@tool` decorator and add them to the `tools` list.
- **Change the model:**  
  Use a different OpenAI model by changing the `model` parameter in `ChatOpenAI`.
- **Change the project/log stream:**  
  Update the values in `splunk_ao_context` to organize your logs.

---

## 9. Best Practices & Tips

- **Use the Splunk AO context manager** to ensure logs are tagged correctly within the Splunk AO UI.
- **Use environment variables** for all secrets and API keys.

---

You now have a fully working, observable LangChain agent with Splunk AO monitoring!
If you want to add more features, track custom metrics, or troubleshoot, refer to the Splunk AO and LangChain documentation or reach out for support.
