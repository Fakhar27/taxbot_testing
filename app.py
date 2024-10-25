import os
import openai
import time
import logging
from io import BytesIO
from datetime import datetime
import streamlit as st
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI

# Load environment variables
api_key = "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"

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model configuration
MODEL = "gpt-4o"

# Initialize session states
if "file_id_list" not in st.session_state:
    st.session_state.file_id_list = []
if "start_chat" not in st.session_state:
    st.session_state.start_chat = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None

# Set up page configuration
st.set_page_config(page_title="Study Buddy - Chat and Learn", page_icon=":books:")

def create_vector_store_with_file(file_content, filename, store_name):
    """Create a vector store and upload a file to it"""
    try:
        # Create a vector store
        vector_store = client.beta.vector_stores.create(
            name=store_name,
            expires_after={
                "anchor": "last_active_at",
                "days": 7
            }
        )
        
        # Create a BytesIO object with the file content
        file_obj = BytesIO(file_content)
        
        # Upload the file to the vector store with the original filename
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=[(filename, file_obj)]  # Use the original filename here
        )
        
        return vector_store
        
    except Exception as e:
        logger.error(f"Error creating vector store: {e}")
        raise

# def create_vector_store_with_file(file_content, filename, store_name):
#     """Create a vector store and upload a file to it"""
#     try:
#         # Create a vector store
#         vector_store = client.beta.vector_stores.create(
#             name=store_name,
#             expires_after={
#                 "anchor": "last_active_at",
#                 "days": 7
#             }
#         )
        
#         # Upload the file to the vector store
#         file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
#             vector_store_id=vector_store.id,
#             files=[("file", BytesIO(file_content))]
#         )
        
#         return vector_store
        
#     except Exception as e:
#         logger.error(f"Error creating vector store: {e}")
#         raise

def process_message_with_citations(message):
    """Process assistant messages and format citations"""
    # Get the first content item's text value
    if not message.content or not message.content[0].text:
        return ""
        
    message_content = message.content[0].text
    citations = []
    
    # Check if there are any annotations
    if hasattr(message_content, 'annotations') and message_content.annotations:
        # Process annotations and citations
        for index, annotation in enumerate(message_content.annotations):
            # Replace the text with a citation marker
            message_content.value = message_content.value.replace(
                annotation.text, f" [{index + 1}]"
            )

            if hasattr(annotation, 'file_citation'):
                try:
                    cited_file = client.files.retrieve(annotation.file_citation.file_id)
                    citations.append(
                        f'[{index + 1}] {annotation.text} (from {cited_file.filename})'
                    )
                except Exception as e:
                    citations.append(f'[{index + 1}] Citation error: {str(e)}')

    final_message = message_content.value if hasattr(message_content, 'value') else str(message_content)
    
    if citations:
        final_message += "\n\nSources:\n" + "\n".join(citations)
        
    return final_message

file_uploaded = st.sidebar.file_uploader(
    "Upload a file to be transformed into embeddings", 
    key="file_upload"
)

if st.sidebar.button("Upload File"):
    if file_uploaded:
        try:
            vector_store = create_vector_store_with_file(
                file_uploaded.getvalue(),
                file_uploaded.name,  # Pass the original filename
                f"Study_Store_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            st.session_state.vector_store_id = vector_store.id
            st.sidebar.success(f"File uploaded successfully! Vector Store ID: {vector_store.id}")
            
        except Exception as e:
            st.sidebar.error(f"Error uploading file: {e}")

# Start chat button
if st.sidebar.button("Start Chatting..."):
    if st.session_state.vector_store_id:
        st.session_state.start_chat = True
        
        # Create a new thread with vector store
        thread = client.beta.threads.create(
            tool_resources={
                "file_search": {
                    "vector_store_ids": [st.session_state.vector_store_id]
                }
            }
        )
        st.session_state.thread_id = thread.id
        st.write("Thread ID:", thread.id)
    else:
        st.sidebar.warning("No files found. Please upload at least one file to get started.")

# Main chat interface
st.title("Study Buddy")
st.write("Learn fast by chatting with your documents")

# Ensure `start_chat` is initialized in session state
if st.session_state.get("start_chat"):
    
    # Initialize `messages` and `thread_id` in session state if not already present
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "thread_id" not in st.session_state or st.session_state.thread_id is None:
        # Create a new thread and store its ID
        thread = client.beta.threads.create()  # Adjust this line if needed for your API setup
        st.session_state.thread_id = thread.id  # Ensure this is a string

    # Display existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Capture user input
    if prompt := st.chat_input("What's new?"):
        
        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add user message to thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # Initiate assistant run
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id="asst_EwELGKkb0FM7RYe5Qx6CDHvq",  # Replace with your assistant ID
            instructions="""Please answer the questions using the knowledge provided in t8he files.
            When adding additional information, make sure to distinguish it with bold or underlined text."""
        )

        # Wait for the assistant's response
        with st.spinner("Thinking..."):
            while run.status != "completed":
                time.sleep(1)
                
                # Ensure `thread_id` is valid before calling retrieve
                if isinstance(st.session_state.thread_id, str):
                    run = client.beta.threads.runs.retrieve(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id
                    )
                else:
                    st.error("Thread ID is not valid.")
                    break

            # Retrieve assistant's messages
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id
            )
            
            # Process and display assistant messages
            assistant_messages = [
                message for message in messages
                if message.run_id == run.id and message.role == "assistant"
            ]

            for message in assistant_messages:
                full_response = process_message_with_citations(message)
                
                # Store assistant's response in session state and display
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )
                with st.chat_message("assistant"):
                    st.markdown(full_response, unsafe_allow_html=True)
else:
    st.write("Please upload at least one file to get started by clicking on the 'Start Chat' button.")


