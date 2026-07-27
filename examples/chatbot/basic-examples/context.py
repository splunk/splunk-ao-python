import os

from splunk_ao import splunk_ao_context, openai

# If you've set your SPLUNK_AO_PROJECT and SPLUNK_AO_AGENT_STREAM env vars, you can skip this step
splunk_ao_context.init(project="your-project-id", log_stream="your-log-stream-id")

# Initialize the Splunk AO wrapped OpenAI client
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def call_openai():
    chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": "Say this is a test"}], model="gpt-4o")

    return chat_completion.choices[0].message.content


# This will create a single span trace with the OpenAI call
call_openai()
