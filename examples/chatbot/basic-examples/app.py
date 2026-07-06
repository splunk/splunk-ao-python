import os

from dotenv import load_dotenv

from splunk_ao import openai  # The Splunk AO OpenAI client wrapper is all you need!

load_dotenv()

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), organization=os.environ.get("OPENAI_ORGANIZATION"))

prompt = "Explain the following topic succinctly: Newton's First Law"
response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}])

print(response.choices[0].message.content.strip())
