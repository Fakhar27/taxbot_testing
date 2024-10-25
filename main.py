import os
import openai
import logging
from datetime import datetime
from openai import OpenAI

api_key = "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"

client = OpenAI(api_key=api_key)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_assistant(filepath: str, model: str = "gpt-4o"):
    """
    Set up the initial assistant with vector store and file search capabilities
    """
    try:
        # Create vector store
        vector_store = client.beta.vector_stores.create(
            name="Study Buddy Store",
            expires_after={
                "anchor": "last_active_at",
                "days": 7
            }
        )
        
        # Upload file to vector store
        with open(filepath, "rb") as file:
            file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=[(os.path.basename(filepath), file)]
            )
        
        # Create assistant
        assistant = client.beta.assistants.create(
            name="Study Buddy",
            instructions="""You are a helpful study assistant who knows a lot about understanding research papers.
            Your role is to summarize papers, clarify terminology within context, and extract key figures and data.
            Cross-reference information for additional insights and answer related questions comprehensively.
            Analyze the papers, noting strengths and limitations.
            Respond to queries effectively, incorporating feedback to enhance your accuracy.
            Handle data securely and update your knowledge base with the latest research.
            Adhere to ethical standards, respect intellectual property, and provide users with guidance on any limitations.
            Maintain a feedback loop for continuous improvement and user support.
            Your ultimate goal is to facilitate a deeper understanding of complex scientific material, making it more accessible and comprehensible.""",
            model=model,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )
        
        logger.info(f"Assistant created with ID: {assistant.id}")
        logger.info(f"Vector store created with ID: {vector_store.id}")
        
        return assistant, vector_store
        
    except Exception as e:
        logger.error(f"Error setting up assistant: {e}")
        raise

def main():
    """
    Main function to set up the initial assistant and store IDs
    """
    try:
        # Setup assistant with initial file
        assistant, vector_store = setup_assistant("./erasmus.pdf")
        
        # Print IDs for future use
        print(f"\nAssistant ID: {assistant.id}")
        print(f"Vector Store ID: {vector_store.id}")
        
        # Create initial thread
        thread = client.beta.threads.create(
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )
        print(f"Thread ID: {thread.id}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
















# import os
# import openai
# import requests
# import json

# import time
# import logging
# from datetime import datetime
# import streamlit as st

# client = openai.OpenAI()

# model = "gpt-4-1106-preview" 

# # Step 1. Upload a file to OpenaI embeddings ===
# filepath = "./erasmus.pdf"
# file_object = client.files.create(file=open(filepath, "rb"), purpose="assistants")

# # Step 2 - Create an assistant
# assistant = client.beta.assistants.create(
#     name="Erasmus Guider",
#     instructions="""Analyze and summarize documents with precision. Extract key info, features, and structures. Preprocess text for clarity. Identify entities, dates, and numbers. Understand document purpose and generate concise summaries. Present structured output with metadata. Learn and adapt with user feedback. Ensure data security. Stay updated with NLP advancements. Guide users with clear documentation""",
#     tools=[{"type": "retrieval"}],
#     model=model,
#     file_ids=[file_object.id],
# )

# # === Get the Assis ID ===
# assis_id = assistant.id
# print(assis_id)

# # == Hardcoded ids to be used once the first code run is done and the assistant was created
# thread_id = "thread_inGWHWAOfo3yxnwNZCophiXL"
# assis_id = "asst_KPhtBJnaLiJaYqGDqnoHn9oP"

# # == Step 3. Create a Thread
# message = "What is mining?"

# # thread = client.beta.threads.create()
# # thread_id = thread.id
# # print(thread_id)

# message = client.beta.threads.messages.create(
#     thread_id=thread_id, role="user", content=message
# )

# # == Run the Assistant
# run = client.beta.threads.runs.create(
#     thread_id=thread_id,
#     assistant_id=assis_id,
#     instructions="Please address the user as d",
# )


# def wait_for_run_completion(client, thread_id, run_id, sleep_interval=5):
#     """
#     Waits for a run to complete and prints the elapsed time.:param client: The OpenAI client object.
#     :param thread_id: The ID of the thread.
#     :param run_id: The ID of the run.
#     :param sleep_interval: Time in seconds to wait between checks.
#     """
#     while True:
#         try:
#             run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
#             if run.completed_at:
#                 elapsed_time = run.completed_at - run.created_at
#                 formatted_elapsed_time = time.strftime(
#                     "%H:%M:%S", time.gmtime(elapsed_time)
#                 )
#                 print(f"Run completed in {formatted_elapsed_time}")
#                 logging.info(f"Run completed in {formatted_elapsed_time}")
#                 # Get messages here once Run is completed!
#                 messages = client.beta.threads.messages.list(thread_id=thread_id)
#                 last_message = messages.data[0]
#                 response = last_message.content[0].text.value
#                 print(f"Assistant Response: {response}")
#                 break
#         except Exception as e:
#             logging.error(f"An error occurred while retrieving the run: {e}")
#             break
#         logging.info("Waiting for run to complete...")
#         time.sleep(sleep_interval)


# # == Run it
# wait_for_run_completion(client=client, thread_id=thread_id, run_id=run.id)

# # === Check the Run Steps - LOGS ===
# run_steps = client.beta.threads.runs.steps.list(thread_id=thread_id, run_id=run.id)
# print(f"Run Steps --> {run_steps.data[0]}")