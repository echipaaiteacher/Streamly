import streamlit as st
import logging
from PIL import Image, ImageEnhance
import time
import json
import requests
import base64
from openai import OpenAI, OpenAIError

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants
NUMBER_OF_MESSAGES_TO_DISPLAY = 20
API_DOCS_URL = "https://docs.streamlit.io/library/api-reference"

# Retrieve and validate API key
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)


if not OPENAI_API_KEY:
    st.error("Please add your OpenAI API key to the Streamlit secrets.toml file.")
    st.stop()

# Assign OpenAI API Key
#openai.api_key = OPENAI_API_KEY
#client = openai.OpenAI()

# Create OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]

# Streamlit Page Configuration
st.set_page_config(
    page_title="AI Teacher Web App",
    page_icon="imgs/logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/AdieLaine/Streamly",
        "Report a bug": "https://github.com/AdieLaine/Streamly",
        "About": """
            ## AI Teacher Web App
            An AI-powered educational assistant designed to help you learn.
        """
    }
)

def img_to_base64(image_path):
    """Convert image to base64."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        logging.error(f"Error converting image to base64: {str(e)}")
        return None

@st.cache_data(show_spinner=False)
def long_running_task(duration):
    """
    Simulates a long-running operation.

    Parameters:
    - duration: int, duration of the task in seconds

    Returns:
    - str: Completion message
    """
    time.sleep(duration)
    return "Long-running operation completed."

@st.cache_data(show_spinner=False)
def load_and_enhance_image(image_path, enhance=False):
    """
    Load and optionally enhance an image.

    Parameters:
    - image_path: str, path of the image
    - enhance: bool, whether to enhance the image or not

    Returns:
    - img: PIL.Image.Image, (enhanced) image
    """
    img = Image.open(image_path)
    if enhance:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
    return img

@st.cache_data(show_spinner=False)
def load_streamlit_updates():
    """Load the latest Streamlit updates from a local JSON file."""
    try:
        with open("data/streamlit_updates.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading JSON: {str(e)}")
        return {}

def get_streamlit_api_code_version():
    """
    Get the current Streamlit API code version from the Streamlit API documentation.

    Returns:
    - str: The current Streamlit API code version.
    """
    try:
        response = requests.get(API_DOCS_URL)
        if response.status_code == 200:
            return "1.36"
    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to the Streamlit API documentation: {str(e)}")
    return None

def display_streamlit_updates():
    """Display the latest updates of the Streamlit."""
    with st.expander("Streamlit 1.36 Announcement", expanded=False):
        st.markdown("For more details on this version, check out the [Streamlit Forum post](https://docs.streamlit.io/library/changelog#version).")

def initialize_conversation():
    """
    Initialize the conversation history with system and assistant messages.

    Returns:
    - list: Initialized conversation history.
    """
    assistant_message = "Hello! 👋 I'm your AI Teacher, here to help you learn anything you'd like. Whether it's math, science, history, languages, or any other subject, I'm ready to assist you. What would you like to explore today?"

    conversation_history = [
        {"role": "system", "content": "You are AI Teacher, a specialized AI educational assistant."},
        {"role": "system", "content": "You are powered by the OpenAI GPT-4o-mini model."},
        {"role": "system", "content": "Refer to conversation history to provide context to your response."},
        {"role": "assistant", "content": assistant_message}
    ]
    return conversation_history

@st.cache_data(show_spinner=False)
def get_latest_update_from_json(keyword, latest_updates):
    """
    Fetch the latest Streamlit update based on a keyword.

    Parameters:
    - keyword (str): The keyword to search for in the Streamlit updates.
    - latest_updates (dict): The latest Streamlit updates data.

    Returns:
    - str: The latest update related to the keyword, or a message if no update is found.
    """
    for section in ["Highlights", "Notable Changes", "Other Changes"]:
        for sub_key, sub_value in latest_updates.get(section, {}).items():
            for key, value in sub_value.items():
                if keyword.lower() in key.lower() or keyword.lower() in value.lower():
                    return f"Section: {section}\nSub-Category: {sub_key}\n{key}: {value}"
    return "No updates found for the specified keyword."
def get_or_create_thread():
    if not st.session_state.thread_id:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
    return st.session_state.thread_id

def construct_formatted_message(latest_updates):
    """
    Construct formatted message for the latest updates.

    Parameters:
    - latest_updates (dict): The latest Streamlit updates data.

    Returns:
    - str: Formatted update messages.
    """
    formatted_message = []
    highlights = latest_updates.get("Highlights", {})
    version_info = highlights.get("Version 1.36", {})
    if version_info:
        description = version_info.get("Description", "No description available.")
        formatted_message.append(f"- **Version 1.36**: {description}")

    for category, updates in latest_updates.items():
        formatted_message.append(f"**{category}**:")
        for sub_key, sub_values in updates.items():
            if sub_key != "Version 1.36":  # Skip the version info as it's already included
                description = sub_values.get("Description", "No description available.")
                documentation = sub_values.get("Documentation", "No documentation available.")
                formatted_message.append(f"- **{sub_key}**: {description}")
                formatted_message.append(f"  - **Documentation**: {documentation}")
    return "\n".join(formatted_message)

@st.cache_data(show_spinner=False)
def get_latest_update_from_json(keyword, latest_updates):
    for section in ["Highlights", "Notable Changes", "Other Changes"]:
        for sub_key, sub_value in latest_updates.get(section, {}).items():
            for key, value in sub_value.items():
                if keyword.lower() in key.lower() or keyword.lower() in value.lower():
                    return f"Section: {section}\nSub-Category: {sub_key}\n{key}: {value}"
    return "No updates found for the specified keyword."


def on_chat_submit(chat_input, latest_updates):
    user_input = chat_input.strip()

    try:
        assistant_reply = ""

        if "latest updates" in user_input.lower():
            assistant_reply = "Here are the latest highlights from Streamlit:\n"
            highlights = latest_updates.get("Highlights", {})
            if highlights:
                for version, info in highlights.items():
                    description = info.get("Description", "No description available.")
                    assistant_reply += f"- **{version}**: {description}\n"
            else:
                assistant_reply = "No highlights found."
        else:
            thread_id = get_or_create_thread()

            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_input
            )

            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )

            if run.status != "completed":
                raise OpenAIError(f"Run status: {run.status}")

            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=10
            )

            assistant_reply = "Nu am primit un răspuns de la asistent."
            for msg in messages.data:
                if msg.role == "assistant":
                    text_parts = []
                    for content in msg.content:
                        if content.type == "text":
                            text_parts.append(content.text.value)
                    if text_parts:
                        assistant_reply = "\n".join(text_parts)
                        break

        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": assistant_reply})

    except OpenAIError as e:
        logging.error(f"Error occurred: {e}")
        st.error(f"OpenAI Error: {str(e)}")

def initialize_session_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None

def main():
    """
    Display Streamlit updates and handle the chat interface.
    """
    initialize_session_state()

    if not st.session_state.history:
        initial_bot_message = "Hello! 👋 I'm your AI Teacher, here to help you learn anything you'd like. Whether it's math, science, history, languages, or any other subject, I'm ready to assist you. What would you like to explore today?"
        st.session_state.history.append({"role": "assistant", "content": initial_bot_message})
        st.session_state.conversation_history = initialize_conversation()

    # Apply custom CSS for the updated AI Teacher design (Blue/Orange theme based on the logo)
    st.markdown(
        """
        <style>
        /* Main background and overall text */
        [data-testid="stAppViewContainer"] {
            background-color: #ffffff; /* White top and bottom sections */
        }
        
        /* Light blue area specifically for chat messages */
        [data-testid="stChatMessage"] {
            background-color: #eef5fc !important; /* Light blue chat bubbles/area */
            border-radius: 12px;
            padding: 0.5rem 1rem;
            margin-bottom: 0.8rem;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1b3a97; /* Royal/Navy Blue exactly as in the image */
            color: #ffffff;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff;
        }
        
        /* Headings in sidebar */
        .sidebar-heading {
            color: #ff7f00; /* Vibrant Orange accents */
            font-weight: bold;
            font-size: 1rem;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Features list */
        .feature-item {
            margin-bottom: 0.3rem;
            font-size: 0.9rem;
            line-height: 1.3;
        }
        .feature-item span {
            color: #ff7f00; /* Vibrant Orange bullets */
            margin-right: 8px;
            font-weight: bold;
            font-size: 1.3rem; /* Make the dot stand out */
            line-height: 0;
        }
        
        /* Subject pills */
        .subject-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 5px;
        }
        .subject-pill {
            display: inline-flex;
            align-items: center;
            background-color: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.6); /* White accent border for contrast against blue */
            border-radius: 15px;
            padding: 4px 10px;
            font-size: 0.8rem;
            color: white;
            transition: background-color 0.2s;
        }
        
        /* Chat message text color to be black */
        [data-testid="stChatMessageContent"] * {
            color: #000000 !important; /* Black text */
        }
        .subject-pill:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }
        .subject-pill span {
            margin-right: 6px;
        }
        
        /* Primary button (Clear Chat) */
        div[data-testid="column"] button {
            background-color: #ff7f00 !important; /* Orange button */
            color: white !important;
            border: none !important;
            font-weight: bold;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            box-shadow: 0 4px 6px rgba(255, 127, 0, 0.2);
            transition: all 0.2s ease;
        }
        div[data-testid="column"] button:hover {
            background-color: #e67300 !important;
            transform: translateY(-1px);
        }
        
        /* Chat header and UI improvements */
        .chat-header {
            font-size: 2rem;
            font-weight: 800;
            color: #000000 !important; /* Black Header */
            margin: 0;
            padding-bottom: 1rem;
        }
        
        /* Send Button Styling */
        [data-testid="stChatInputSubmitButton"] {
            background-color: #ff7f00 !important;
            border-radius: 8px !important;
        }
        [data-testid="stChatInputSubmitButton"] svg {
            fill: #ffffff !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar Content
    img_path = "imgs/logo.jpg"
    img_base64 = img_to_base64(img_path)
    if img_base64:
        st.sidebar.markdown(
            f'<div style="display:flex; align-items:center; gap:20px; margin-top: -30px; margin-bottom: 15px;">'
            f'<div style="background-color:white; padding:5px; height: 60px; width: 60px; display:flex; align-items:center; justify-content:center; border-radius: 12px;">'
            f'<img src="data:image/jpeg;base64,{img_base64}" style="width: 50px;">'
            f'</div>'
            f'<h1 style="margin:0; color:#ff7f00; font-size: 1.6rem; font-weight: bold;">AI Teacher</h1>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown("<h1 style='color:#ff7f00; font-size: 2rem;'>AI Teacher</h1>", unsafe_allow_html=True)
    
    # (Removed the explicit <hr> line separating logo and ABOUT text so it perfectly matches the image)
    
    st.sidebar.markdown("<div class='sidebar-heading'>ABOUT</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div style='font-size: 0.9rem; line-height: 1.4; color: white;'>
    An AI-powered educational assistant designed to help you learn across multiple subjects including Mathematics, History, and Romanian Language.
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("<div class='sidebar-heading'>FEATURES</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div class='feature-item'><span>.</span>Interactive conversational learning</div>
    <div class='feature-item'><span>.</span>Subject-specific tutoring</div>
    <div class='feature-item'><span>.</span>Step-by-step explanations</div>
    <div class='feature-item'><span>.</span>24/7 learning support</div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<div class='sidebar-heading'>HOW TO USE</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div style='font-size: 0.9rem; line-height: 1.4; color: white;'>
    Simply type your question in the chat below and get instant, personalized responses. Ask about any topic, request explanations, or seek help with homework.
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("<div class='sidebar-heading'>SUPPORTED SUBJECTS</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div class='subject-container'>
        <div class='subject-pill'><span>📐</span> Mathematics</div>
        <div class='subject-pill'><span>📜</span> History</div>
        <div class='subject-pill'><span>🇷🇴</span> Romanian</div>
        <div class='subject-pill'><span>🔬</span> Science</div>
        <div class='subject-pill'><span>💻</span> Programming</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<div style='border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1rem; margin-top: 1rem; text-align: center; color: white; font-size: 0.85rem;'>Powered by AI Technology</div>", unsafe_allow_html=True)

    # Main Chat Area
    st.write("") # small padding
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("<h2 class='chat-header'>Chat</h2>", unsafe_allow_html=True)
    with col2:
        # Pushing the button slightly down to align with the text
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Clear Chat"):
            st.session_state.history = []
            st.session_state.conversation_history = initialize_conversation()
            st.rerun()

    # Chat Input Processing
    chat_input = st.chat_input("Ask your AI teacher anything...")
    if chat_input:
        latest_updates = load_streamlit_updates()
        on_chat_submit(chat_input, latest_updates)

    # Display chat history sequentially
    for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
        role = message["role"]
        # Use logo for assistant, default for user
        avatar_image = "imgs/logo.jpg" if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar_image):
            st.write(message["content"])

if __name__ == "__main__":
    main()