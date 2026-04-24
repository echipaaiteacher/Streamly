import streamlit as st
import logging
from PIL import Image, ImageEnhance
import time
import json
import requests
import base64
from openai import OpenAI, OpenAIError
import os
import re

# Base directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

@st.cache_data(show_spinner=False)
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
    conversation_history = [
        {"role": "system", "content": "You are AI Teacher, a specialized AI educational assistant."},
        {"role": "system", "content": "You are powered by the OpenAI GPT-4o-mini model."},
        {"role": "system", "content": "Refer to conversation history to provide context to your response."}
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

    # Verificare dacă utilizatorul este blocat temporar
    if st.session_state.get("block_until", 0) > time.time():
        remaining = max(0, int(st.session_state.block_until - time.time()))
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": f"Conversația a fost închisă temporar din cauza limbajului neadecvat. Te rog să aștepți {remaining} secunde."})
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()
        return
    elif st.session_state.get("block_until", 0) != 0 and st.session_state.get("block_until", 0) <= time.time():
        # Expirarea blocajului, resetăm contoarele
        st.session_state.block_until = 0
        st.session_state.abatere_count = 0
        st.session_state.injurii_count = 0

    # Verificare moderare limbaj cu LLM (o pre-verificare rapidă)
    try:
        prompt_check = f'''Ești un asistent AI care monitorizează limbajul utilizatorului. Trebuie să detectezi limbajul jignitor sau injurios. Analizează textul și returnează un JSON strict cu următoarele câmpuri: "is_offensive" (boolean): true dacă mesajul conține cuvinte jignitoare, insulte sau înjurături. "injurii_count" (int): numărul de cuvinte injurioase/vulgare găsite în text. Text de analizat: "{user_input}"'''
        mod_response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": prompt_check}],
            max_tokens=60
        )
        mod_result = json.loads(mod_response.choices[0].message.content)
        is_offensive = mod_result.get("is_offensive", False)
        new_injurii = mod_result.get("injurii_count", 0)
        
        if is_offensive or new_injurii > 0:
            st.session_state.abatere_count += 1
            st.session_state.injurii_count += new_injurii
            
            assistant_reply = ""
            if st.session_state.abatere_count >= 3 or st.session_state.injurii_count >= 3:
                st.session_state.block_until = time.time() + 60
                assistant_reply = "Conversația a fost închisă pentru 60 de secunde din cauza limbajului neadecvat. Te rog să revii după acest interval."
            elif st.session_state.abatere_count == 2:
                assistant_reply = "Te rog din nou să ai grijă la limbaj. Dacă vei continua, conversația va fi oprită temporar."
            else:
                assistant_reply = "Te rog să folosești un limbaj respectuos."
                
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.history.append({"role": "assistant", "content": assistant_reply})
            
            if st.session_state.abatere_count >= 3 or st.session_state.injurii_count >= 3:
                # Trigger a fresh UI reload immediately so the input box hides:
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()
            return
            
    except Exception as e:
        # Ignore moderation errors to not break chat, unless it was our rerun instruction:
        if isinstance(e, (st.runtime.scriptrunner.StopException, getattr(st, 'StopException', type(None)))):
            raise e
        logging.error(f"Eroare la moderarea limbajului: {e}")

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
                assistant_id=ASSISTANT_ID,
                tools=[{"type": "file_search"}],
                additional_instructions="Recomandare de sistem: Folosește obligatoriu cunoștințele din fișierele și baza ta de date atașată (file_search) pentru a răspunde detaliat la întrebări."
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
        assistant_reply = re.sub(r'\u3010[^\u3011]*\u3011', '', assistant_reply).strip()
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
    if "abatere_count" not in st.session_state:
        st.session_state.abatere_count = 0
    if "injurii_count" not in st.session_state:
        st.session_state.injurii_count = 0
    if "block_until" not in st.session_state:
        st.session_state.block_until = 0
    if "pending_input" not in st.session_state:
        st.session_state.pending_input = None

def _check_moderation(user_input):
    """
    Run offensive-language check via LLM.
    Returns a moderation reply string if the message is flagged, or None if clean.
    Also updates session state counters and block_until.
    """
    try:
        prompt_check = f'''Ești un asistent AI care monitorizează limbajul utilizatorului. Trebuie să detectezi limbajul jignitor sau injurios. Analizează textul și returnează un JSON strict cu următoarele câmpuri: "is_offensive" (boolean): true dacă mesajul conține cuvinte jignitoare, insulte sau înjurături. "injurii_count" (int): numărul de cuvinte injurioase/vulgare găsite în text. Text de analizat: "{user_input}"'''
        mod_response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": prompt_check}],
            max_tokens=60
        )
        mod_result = json.loads(mod_response.choices[0].message.content)
        is_offensive = mod_result.get("is_offensive", False)
        new_injurii = mod_result.get("injurii_count", 0)

        if is_offensive or new_injurii > 0:
            st.session_state.abatere_count += 1
            st.session_state.injurii_count += new_injurii
            if st.session_state.abatere_count >= 3 or st.session_state.injurii_count >= 3:
                st.session_state.block_until = time.time() + 60
                return "Conversația a fost închisă pentru 60 de secunde din cauza limbajului neadecvat. Te rog să revii după acest interval."
            elif st.session_state.abatere_count == 2:
                return "Te rog din nou să ai grijă la limbaj. Dacă vei continua, conversația va fi oprită temporar."
            else:
                return "Te rog să folosești un limbaj respectuos."
        return None
    except Exception as e:
        if isinstance(e, (st.runtime.scriptrunner.StopException, getattr(st, 'StopException', type(None)))):
            raise e
        logging.error(f"Eroare la moderarea limbajului: {e}")
        return None


def _get_ai_reply(user_input, latest_updates):
    """
    Call the OpenAI assistant and append only the assistant reply to history.
    The user message must already be in history before calling this.
    """
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
                assistant_id=ASSISTANT_ID,
                tools=[{"type": "file_search"}],
                additional_instructions="Recomandare de sistem: Folosește obligatoriu cunoștințele din fișierele și baza ta de date atașată (file_search) pentru a răspunde detaliat la întrebări."
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
        assistant_reply = re.sub(r'\u3010[^\u3011]*\u3011', '', assistant_reply).strip()
        st.session_state.history.append({"role": "assistant", "content": assistant_reply})
    except OpenAIError as e:
        logging.error(f"Error occurred: {e}")
        st.error(f"OpenAI Error: {str(e)}")


def main():
    """
    Display Streamlit updates and handle the chat interface.
    """
    initialize_session_state()

    if not st.session_state.history and not st.session_state.conversation_history:
        st.session_state.conversation_history = initialize_conversation()

    # Apply custom CSS for the updated AI Teacher design (Blue/Orange theme based on the logo)
    st.markdown(
        """
        <style>
        /* Main background — saturated light blue matching Figma */
        [data-testid="stAppViewContainer"] {
            background-color: #d4e5f7 !important;
        }
        
        /* Top white strip — 35px spacer above the bar */
        [data-testid="stHeader"] {
            background-color: #ffffff !important;
            height: 35px !important;
            min-height: 35px !important;
            overflow: hidden !important;
        }
        /* Hide Deploy button and 3-dot menu */
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"] {
            display: none !important;
        }

        /* Running animation — keep visible, orange icon */
        [data-testid="stStatusWidget"] {
            display: flex !important;
            color: #000000 !important;
        }
        [data-testid="stStatusWidget"] svg {
            color: #ff7f00 !important;
            fill: #ff7f00 !important;
        }

        /* Make all chat message bubbles completely transparent */
        [data-testid="stChatMessage"] {
            background-color: transparent !important; 
            border: none !important;
            border-radius: 0;
            padding: 0.5rem 0;
            margin-bottom: 0.8rem;
            box-shadow: none !important;
        }
        [data-testid="stChatMessage"] > div,
        [data-testid="stChatMessageContent"] {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
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
            font-size: 1.3rem;
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
            border: 1px solid rgba(255, 255, 255, 0.6);
            border-radius: 15px;
            padding: 4px 10px;
            font-size: 0.8rem;
            color: white;
            transition: background-color 0.2s;
        }
        
        /* Chat message text color to be black */
        [data-testid="stChatMessageContent"] * {
            color: #000000 !important;
        }
        .subject-pill:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }
        .subject-pill span {
            margin-right: 6px;
        }
        
        /* Orange primary button (Cere Hint) — matching Figma */
        [data-testid="stBaseButton-secondary"] {
            background-color: #ff7f00 !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 600;
            border-radius: 8px !important;
            padding: 0.4rem 1.2rem !important;
            box-shadow: 0 2px 4px rgba(255, 127, 0, 0.3) !important;
            transition: all 0.2s ease;
            white-space: nowrap !important;
            font-size: 0.9rem !important;
            min-width: fit-content !important;
        }
        [data-testid="stBaseButton-secondary"]:hover {
            background-color: #e67300 !important;
            color: #ffffff !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(255, 127, 0, 0.4) !important;
        }

        /* Responsive: smaller Cere Hint on narrow screens */
        @media (max-width: 768px) {
            [data-testid="stBaseButton-secondary"] {
                padding: 0.3rem 0.8rem !important;
                font-size: 0.8rem !important;
            }
        }
        @media (max-width: 480px) {
            [data-testid="stBaseButton-secondary"] {
                padding: 0.25rem 0.6rem !important;
                font-size: 0.7rem !important;
            }
        }
        
        /* Chat header — compact inline label */
        .chat-header {
            font-size: 2rem;
            font-weight: 700;
            color: #ff7f00 !important;
            margin: 0 0 0 30px;
            padding: 0;
            line-height: 50px;
            white-space: nowrap;
        }
        
        /* Header row — white, FIXED below 25px top strip, 50px height */
        [data-testid="stHorizontalBlock"] {
            background-color: #ffffff !important;
            padding: 0 1.5rem !important;
            border-bottom: 1px solid #e0e4e8 !important;
            border-radius: 0 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
            position: fixed !important;
            top: 35px !important;
            left: 18rem !important;
            right: 0 !important;
            z-index: 999 !important;
            margin: 0 !important;
            width: auto !important;
            height: 50px !important;
            max-height: 50px !important;
            /* Force single-row layout at all resolutions */
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            overflow: hidden !important;
            transition: left 0.3s ease;
        }
        /* Extend header to full width when sidebar is collapsed.
           In Streamlit 1.55, stExpandSidebarButton appears when collapsed. */
        :root:has([data-testid="stExpandSidebarButton"]) [data-testid="stHorizontalBlock"] {
            left: 0 !important;
        }
        
        /* Sidebar expand arrow (far-left) — orange to match brand colour.
           Targets the specific data-testid for Streamlit 1.55+ and overrides all inner spans. */
        [data-testid="stExpandSidebarButton"],
        [data-testid="stExpandSidebarButton"] * {
            color: #ff7f00 !important;
        }
        /* Col1 (Chat label): fill available space */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            height: 50px !important;
            display: flex !important;
            align-items: center !important;
        }
        /* Col2 (Cere Hint button): shrink to fit content, never wrap */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex: 0 0 auto !important;
            width: auto !important;
            height: 50px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
        }

        /* Push main content down — 35px strip + 50px bar = 85px total */
        .block-container, 
        [data-testid="stMainBlockContainer"] {
            padding-top: 5.5rem !important;
        }
        
        /* Send Button — rounded square matching Figma */
        [data-testid="stChatInputSubmitButton"] {
            background-color: #ff7f00 !important;
            border-radius: 8px !important;
            width: 35px !important;
            height: 35px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin-right: 5px;
            border: none !important;
            box-shadow: 0 2px 4px rgba(255,127,0,0.3);
        }
        [data-testid="stChatInputSubmitButton"] svg {
            fill: #ffffff !important;
            color: #ffffff !important;
            width: 18px !important;
            height: 18px !important;
        }

        /* Chat Input — white background matching Figma */
        [data-testid="stChatInput"] {
            background-color: transparent !important;
        }
        [data-testid="stChatInput"] > div {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
            padding: 2px !important;
        }
        [data-testid="stChatInput"] textarea {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: none !important;
            caret-color: #000000 !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: #9ca3af !important; /* Gray placeholder text */
            opacity: 1 !important;
        }
        [data-testid="stChatInput"] textarea:focus {
            background-color: #ffffff !important;
            color: #000000 !important;
            outline: none !important;
            caret-color: #000000 !important;
        }

        /* Bottom container — white background */
        [data-testid="stBottomBlockContainer"] {
            background-color: #ffffff !important;
        }

        /* Chat input box shadow for visibility on white */
        [data-testid="stChatInput"] > div {
            box-shadow: 0 2px 12px rgba(0,0,0,0.15) !important;
        }
        /* Spinner text — orange to match running animation */
        [data-testid="stSpinner"] p,
        [data-testid="stSpinner"] span {
            color: #ff7f00 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar Content
    img_path = os.path.join(BASE_DIR, "imgs", "logo.jpg")
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
    
    st.sidebar.markdown("<div class='sidebar-heading'>DESPRE</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div style='font-size: 0.9rem; line-height: 1.4; color: white;'>
    Un asistent educațional inteligent, creat pentru a te ajuta să înveți la Limba Română.
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("<div class='sidebar-heading'>FUNCȚIONALITĂȚI</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div class='feature-item'><span>.</span>Învățare interactivă prin conversații</div>
    <div class='feature-item'><span>.</span>Tutorat personalizat pe materii</div>
    <div class='feature-item'><span>.</span>Explicații pas cu pas</div>
    <div class='feature-item'><span>.</span>Suport educațional 24/7</div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<div class='sidebar-heading'>CUM FUNCȚIONEAZĂ</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div style='font-size: 0.9rem; line-height: 1.4; color: white;'>
    Scrie întrebarea ta în chat-ul de mai jos și primește răspunsuri instantanee și personalizate. Poți întreba despre orice subiect, poți cere detalii sau poți solicita ajutor la teme.
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("<div class='sidebar-heading'>MATERII DISPONIBILE</div>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div class='subject-container'>
        <div class='subject-pill'><span>🇷🇴</span> Română</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<div style='border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1rem; margin-top: 1rem; text-align: center; color: white; font-size: 0.85rem;'>Susținut de Inteligența Artificială</div>", unsafe_allow_html=True)

    # Verificare dacă utilizatorul este blocat temporar
    is_blocked = False
    if st.session_state.get("block_until", 0) > time.time():
        is_blocked = True
    elif st.session_state.get("block_until", 0) != 0 and st.session_state.get("block_until", 0) <= time.time():
        st.session_state.block_until = 0
        st.session_state.abatere_count = 0
        st.session_state.injurii_count = 0

    # Main Chat Area — header row (fixed bar via CSS)
    st.write("")  # small padding
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<span class='chat-header'>Chat</span>", unsafe_allow_html=True)
    with col2:
        if st.button("💡 Cere Hint", disabled=is_blocked):
            hint_message = "Mă poți ajuta cu un mic indiciu pentru a continua? Te rog nu-mi da rezolvarea completă."
            latest_updates = load_streamlit_updates()
            with st.spinner("Pregătesc indiciul..."):
                on_chat_submit(hint_message, latest_updates)

    # ── Step 1: Display history FIRST so the user sees their message
    #            while the AI is processing in the next run.
    for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
        role = message["role"]
        avatar_image = os.path.join(BASE_DIR, "imgs", "logo.jpg") if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar_image):
            st.write(message["content"])

    # ── Step 2: If a pending user message exists (Run 2), call AI now.
    #            History is already rendered above, so user sees their question.
    if st.session_state.get("pending_input") and not is_blocked:
        pending = st.session_state.pending_input
        st.session_state.pending_input = None
        latest_updates = load_streamlit_updates()
        with st.spinner("🤔 AI-ul procesează răspunsul..."):
            _get_ai_reply(pending, latest_updates)
        st.rerun()

    # ── Step 3: Blocked state or accept new input (Run 1).
    elif is_blocked:
        remaining = max(0, int(st.session_state.block_until - time.time()))
        st.error(f"🚫 Chat-ul este restricționat din cauza limbajului neadecvat. Te rugăm să aștepți {remaining} secunde.")
        if st.button("🔄 Verifică status"):
            st.rerun()
    else:
        chat_input = st.chat_input("Întreabă-ți profesorul AI orice...")
        if chat_input:
            mod_reply = _check_moderation(chat_input)
            if mod_reply:
                # Offensive language — add user msg + warning together, no pending needed
                st.session_state.history.append({"role": "user", "content": chat_input})
                st.session_state.history.append({"role": "assistant", "content": mod_reply})
            else:
                # Clean input — add user msg now, queue AI for next run
                st.session_state.history.append({"role": "user", "content": chat_input})
                st.session_state.pending_input = chat_input
            st.rerun()

if __name__ == "__main__":
    main()