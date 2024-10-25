from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler

client = OpenAI(api_key="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")
 

assistant = client.beta.assistants.create(
  name="Math Tutor",
  instructions="You are a personal math tutor. Write and run code to answer math questions.",
  tools=[{"type": "code_interpreter"}],
  model="gpt-4o",
)

thread = client.beta.threads.create()

message = client.beta.threads.messages.create(
  thread_id=thread.id,
  role="user",
  content="I need to solve the equation `3x + 11 = 14`. Can you help me?"
)
 
run = client.beta.threads.runs.create_and_poll(
  thread_id=thread.id,
  assistant_id=assistant.id,
  instructions="Please address the user as Jane Doe. The user has a premium account."
)

if run.status == 'completed': 
  messages = client.beta.threads.messages.list(
    thread_id=thread.id
  )
  print(messages)
else:
  print(run.status)