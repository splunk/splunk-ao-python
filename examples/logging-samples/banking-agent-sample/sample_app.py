# /// script
# requires-python = ">=3.11"
# dependencies = ["splunk-ao[openai]", "python-dotenv"]
# ///
"""
Agent Observability with Splunk AO — Sample Application
Topic: Agent Streams

This script demonstrates a simple tool-using agent instrumented with Splunk AO.
Splunk AO captures every LLM call, tool invocation, and span so you can see
exactly what the agent did, why, and where things went wrong.

This script assumes the .env file is located
in the parent directory, and it's properly configured.
See README.md for setup and run instructions.
"""

import json
import os

from dotenv import load_dotenv

from splunk_ao import log, splunk_ao_context
from splunk_ao.openai import OpenAI

load_dotenv()
project = os.environ.get("SPLUNK_AO_PROJECT")
agent_stream = os.environ.get("SPLUNK_AO_AGENT_STREAM")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- Simple tools the agent can call ---


@log(span_type="tool")
def get_account_balance(account_id: str) -> dict:
    """Simulated tool: fetch account balance."""
    # Simulated data — in a real app this would call your backend
    balances = {"ACC-001": {"balance": 4200.00, "currency": "USD"}, "ACC-002": {"balance": 150.75, "currency": "USD"}}
    return balances.get(account_id, {"error": f"Account {account_id} not found"})


@log(span_type="tool")
def check_loan_eligibility(account_id: str, loan_amount: float) -> dict:
    """Simulated tool: check if an account is eligible for a loan."""
    balance = get_account_balance(account_id).get("balance", 0)
    eligible = balance >= loan_amount * 0.2  # Simple rule: need 20% of loan as balance
    return {
        "eligible": eligible,
        "account_id": account_id,
        "requested_amount": loan_amount,
        "reason": "Sufficient balance" if eligible else "Insufficient balance for loan",
    }


# --- Tool definitions for the LLM ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_account_balance",
            "description": "Get the current balance for a bank account",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string", "description": "The account ID, e.g. ACC-001"}},
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_loan_eligibility",
            "description": "Check if an account is eligible for a loan of a given amount",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "The account ID"},
                    "loan_amount": {"type": "number", "description": "The requested loan amount in USD"},
                },
                "required": ["account_id", "loan_amount"],
            },
        },
    },
]
TOOL_MAP = {"get_account_balance": get_account_balance, "check_loan_eligibility": check_loan_eligibility}
# --- Agent loop instrumented with Splunk AO ---


@log(span_type="agent", name="Agent Workflow")
def run_agent(user_query: str) -> None:
    """
    Run a simple tool-using agent and log every step to Splunk AO.
    This demonstrates agent observability: every LLM call, tool call,
    and final response is captured as a trace with spans.
    """
    print(f"\n{'=' * 60}")
    print(f"User query: {user_query}")
    print(f"{'=' * 60}")
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful banking assistant. "
                "Use the available tools to answer questions about accounts and loans. "
                "Always use the exact account ID provided by the user."
            ),
        },
        {"role": "user", "content": user_query},
    ]
    # Agentic loop — runs until the model stops calling tools
    max_steps = 5
    for step in range(max_steps):
        print(f"\n[Step {step + 1}] Calling LLM...")

        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, tools=TOOLS, tool_choice="auto"
        )

        message = response.choices[0].message

        # If no tool calls, we're done
        if not message.tool_calls:
            print(f"\nFinal answer: {message.content}")
            break

        # Otherwise, process each tool call
        messages.append(message)
        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            print(f"  -> Tool call: {fn_name}({fn_args})")
            # Execute the tool
            result = TOOL_MAP[fn_name](**fn_args)
            print(f"  <- Tool result: {result}")

            # Append tool result to message history
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})


# --- Run sample queries ---
if __name__ == "__main__":
    with splunk_ao_context(project=project, agent_stream=agent_stream):
        splunk_ao_context.start_session(name="Lab 02 - Agent Streams")

        # Query 1: Normal flow — should work fine
        run_agent("What is the balance for account ACC-001?")

        # Query 2: Loan eligibility check
        run_agent("Can account ACC-002 get a loan of $5000?")
        # Query 3: Ambiguous query — watch how the agent handles it
        run_agent("Can I get a loan?")

    print("\n\nOpen your Splunk Agent Observability dashboard to see the traces for these 3 runs.")
    print("Look for differences in tool selection quality and context adherence across the queries.")
