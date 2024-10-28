import os
import openai
import time
import logging
from io import BytesIO
from datetime import datetime
import streamlit as st
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI

client = OpenAI(api_key=api_key)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL = "gpt-4o"

# initailizing SESSION STATE variables which are 4: file_id_list which is a list of file ids, start_chat which is a boolean, thread_id which is a thread id, vector_store_id which is a vector store id
if "file_id_list" not in st.session_state:
    st.session_state.file_id_list = []
if "start_chat" not in st.session_state:
    st.session_state.start_chat = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None

st.set_page_config(page_title="Study Buddy - Chat and Learn", page_icon=":books:")

# creating a vector_store to store embeddi
def create_vector_store_with_file(file_content, filename, store_name):
    """Create a vector store and upload a file to it"""
    try:
        # fucntion to create a vector_store
        # function has multiple optional parameters like
        # name, expires_after, metadata, and vector_store_config, chunking_strategy
        vector_store = client.beta.vector_stores.create(
            name=store_name,
            expires_after={
                "anchor": "last_active_at",
                "days": 7
            }
        )
        
        # Converting content of the file to bytes for vector store 
        file_obj = BytesIO(file_content)
        
        # uploading the file to the vector_store we created above, takes in ID of the vector_store and a list of files
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=[(filename, file_obj)]  
        )
        
        # returning the vector_store, we will have ID,name,bytes,file count object etc
        return vector_store
        
    except Exception as e:
        logger.error(f"Error creating vector store: {e}")
        raise

# This fucntion will basically take messages/responses from the assistant and format them, formats citations as well
# message parameter will be an object
# message = {
#     "content": [
#         {
#             "text": "The theory of relativity is a fundamental concept in physics. According to Einstein, space and time are intertwined.",
#             "annotations": [
#                 {
#                     "text": "theory of relativity",
#                     "file_citation": {"file_id": "12345"}
#                 },
#                 {
#                     "text": "Einstein",
#                     "file_citation": {"file_id": "67890"}
#                 }
#             ]
#         }
#     ]
# }
def process_message_with_citations(message):
    """Process assistant messages and format citations"""
    # edge case if message is empty
    if not message.content or not message.content[0].text:
        return ""
    # extract message content
    message_content = message.content[0].text # "The theory of relativity is a fundamental......"
    # initialize citations which will be a list
    citations = []
    
    if hasattr(message_content, 'annotations') and message_content.annotations:
        for index, annotation in enumerate(message_content.annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f" [{index + 1}]"
            )

            if hasattr(annotation, 'file_citation'):
                try:
                    cited_file = client.files.retrieve(annotation.file_citation.file_id)
                    citations.append(
                        f'[{index + 1}] {annotation.text}'
                    )
                except Exception as e:
                    citations.append(f'[{index + 1}] Citation error: {str(e)}')

    final_message = message_content.value if hasattr(message_content, 'value') else str(message_content)
    
    if citations:
        final_message += "\n\nSources:\n" + "\n".join(citations)
        
    return final_message

# initiLizing a button called file_uploaded for uplaoding files on the sidebar
file_uploaded = st.sidebar.file_uploader(
    "Upload a file to be transformed into embeddings", 
    key="file_upload"
)

# Logic for file_uploaded button 
if st.sidebar.button("Upload File"):
    if file_uploaded:
        try:
            # when clicke on function we made above is called to create,convert and upload the file to vector store
            vector_store = create_vector_store_with_file(
                file_uploaded.getvalue(), # getting the content of the file
                file_uploaded.name, # getting the name of the file
                f"Study_Store_{datetime.now().strftime('%Y%m%d_%H%M%S')}" # creating a name for the vector store
            )
            
            st.session_state.vector_store_id = vector_store.id  # storing the ID of the vector store in the session state
            st.sidebar.success(f"File uploaded successfully! Vector Store ID: {vector_store.id}")
            
        except Exception as e:
            st.sidebar.error(f"Error uploading file: {e}")

# Logic for start_chat button
if st.sidebar.button("Start Chatting..."):
    if st.session_state.vector_store_id: # if vector_store id is not None and vector_store is created
        st.session_state.start_chat = True # setting start_chat session variable to True
        # creating an assistant thread with vector store id
        # thread call has request body with optional parameters like
        # messages which is an array, tool_resources which can be object or null, metadata which is a map
        thread = client.beta.threads.create(
            tool_resources={
                "file_search": {
                    "vector_store_ids": [st.session_state.vector_store_id]
                }
            }
        )
        st.session_state.thread_id = thread.id # storing the thread id in session varaible
        st.write("Thread ID:", thread.id)
    else:
        st.sidebar.warning("No files found. Please upload at least one file to get started.")

# Frontend stuff
st.title("Study Buddy")
st.write("Learn fast by chatting with your documents")

# chat interface
if st.session_state.get("start_chat"): # if start_chat session variable is True
    
    if "messages" not in st.session_state: # if messages is not in session state
        st.session_state.messages = [] # initializes an empty list to hold messages
    
    if "thread_id" not in st.session_state or st.session_state.thread_id is None: # if thread_id is None
        thread = client.beta.threads.create() # creates a new thread
        st.session_state.thread_id = thread.id # stores the thread id in session state
    for message in st.session_state.messages: # for each message in messages
        with st.chat_message(message["role"]): # creates a chat message
            st.markdown(message["content"])

    if prompt := st.chat_input("What's new?"): # basically asking user for an initial prompt, runs if not none
        # user's entered prompt is stored in session state with role as User
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        # Here is where openai comes into plat
        # we have created a thread with vector store id
        # we use that and send it a message with role and content
        # create has Mandotory parameters which are thread_id, role and content
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )
        # now we call run fucntion to feed the thread into the assistant
        # thread_id is Mandotory parameter, assistant_id is Mandotory parameter
        # instructions is optional parameter
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id="asst_EwELGKkb0FM7RYe5Qx6CDHvq", 
            instructions="""Please answer the questions using the knowledge provided in the files.
            When adding additional information, make sure to distinguish it with bold or underlined text."""
        )
        # frontend spinner till the run is completed
        with st.spinner("Thinking..."):
            # check for status if run completed is true
            while run.status != "completed":
                time.sleep(1) # every second
                if isinstance(st.session_state.thread_id, str): # if thread id is valid and exists
                    run = client.beta.threads.runs.retrieve(  # we do run.retrieve function to get the run details
                        thread_id=st.session_state.thread_id, # mansotory parameter
                        run_id=run.id # mansotory parameter
                    )
                    # run response returns status
                else:
                    st.error("Thread ID is not valid.")
                    break
                
            # retrieving the list of all the messages in this specific thread
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id
            )
            # filters out the messages that have run_id and role as assistant
            assistant_messages = [
                message for message in messages
                if message.run_id == run.id and message.role == "assistant"
            ]
            # runs formatting function
            # gets response and appends them to messages session state
            for message in assistant_messages:
                full_response = process_message_with_citations(message)
                
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )
                with st.chat_message("assistant"):
                    st.markdown(full_response, unsafe_allow_html=True)
else:
    st.write("Please upload at least one file to get started by clicking on the 'Start Chat' button.")


