import os
import openai
import logging
from datetime import datetime
from openai import OpenAI

api_key = "g9MZcozfif6MsP51zXa54FSJI4metuT8_eS9xSkAr_fIFaW91rUeolFrOrL0wgZ1Xf8mXiWImkT3BlbkFJcEW4w7rPq57A0lyiPRjYVdAkaFOviIUTKyD7JMbpd8mqsm9ECagDFeOgbhqj5E5vyzzcneOn8A"
client = OpenAI(api_key=api_key)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# this will be a function to create an assistant with vector_store and file search capabilities
# two paramters: filepath which is the path to the file attached whcih assistant will use vector store and model which assistant will use
def setup_assistant(filepath: str, model: str = "gpt-4o"):
    """
    Set up the initial assistant with vector store and file search capabilities
    """
    try:
        # vector_store's create function to create a vector store which expires after 7 days
        vector_store = client.beta.vector_stores.create(
            name="Study Buddy Store",
            expires_after={
                "anchor": "last_active_at",
                "days": 7
            }
        )
        # uploading the file to the vector_store we just created
        with open(filepath, "rb") as file:
            file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=[(os.path.basename(filepath), file)]
            )
        # finally creating an assistant which uses the vector store we just created
        # model is mandotory parameter, others are optional
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
        
        return assistant, vector_store # will return all the ids etc of both recnently created assistant and vector store
        
    except Exception as e:
        logger.error(f"Error setting up assistant: {e}")
        raise

def main():
    """
    Main function to set up the initial assistant and store IDs
    """
    try:
        # calling the setup_assistant function
        assistant, vector_store = setup_assistant("./erasmus.pdf")
        # printing the assistant id and vector store id
        print(f"\nAssistant ID: {assistant.id}")
        print(f"Vector Store ID: {vector_store.id}")
        # creating a thread with vector store id
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

