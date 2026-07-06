import os

from dotenv import load_dotenv

from splunk_ao import openai, splunk_ao_context

load_dotenv()

# If you've set your SPLUNK_AO_PROJECT and SPLUNK_AO_LOG_STREAM env vars, you can skip this step
splunk_ao_context.init(project="your-project-name", log_stream="your-log-stream-name")

# Initialize the Splunk AO wrapped OpenAI client
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def call_openai():
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "Say this is a test"}], model="gpt-4o"
    )

    return chat_completion.choices[0].message.content


# This will create a single span trace with the OpenAI call
call_openai()

# This will upload the trace to Splunk AO
splunk_ao_context.flush()
