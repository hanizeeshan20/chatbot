
import streamlit as st
import datetime
import os
import re
import time
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv
from gtts import gTTS
import base64
import tempfile
from streamlit_audio_recorder import audio_recorder

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="DBT Voice Chatbot", layout="centered")
st.title("🧠 Your mental health companion")
st.markdown("Talk to the bot using your voice or type below. The bot reflects on your emotions and themes over time.")

# Check if user has accepted voice chat
if 'voice_chat_opt_in' not in st.session_state:
    st.session_state.voice_chat_opt_in = False

# Audio input using mic button only if user agreed
audio_bytes = None
if st.session_state.voice_chat_opt_in:
    audio_bytes = audio_recorder(pause_threshold=1.5, sample_rate=44100)

# Session state setup
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'first_interaction' not in st.session_state:
    st.session_state.first_interaction = datetime.datetime.now()
if 'summary_notes' not in st.session_state:
    st.session_state.summary_notes = []
if 'theme_memory' not in st.session_state:
    st.session_state.theme_memory = defaultdict(int)
if 'chat_started' not in st.session_state:
    st.session_state.chat_history.append({
        "user": "",
        "bot": "Hi there. What brings you here today?"
    })
    st.session_state.chat_started = True

chat_placeholder = st.container()
with chat_placeholder:
    for chat in st.session_state.chat_history:
        if chat['user']:
            with st.chat_message("user"):
                st.markdown(chat['user'])
        with st.chat_message("assistant"):
            st.markdown(chat['bot'])

typed_input = st.chat_input("You:")

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    with open(tmp_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text

def extract_themes_from_response(response):
    themes = ["shame", "anger", "impulsivity", "loneliness", "worthlessness", "avoidance", "abandonment", "perfectionism", "fear", "guilt", "rejection"]
    extracted = []
    for theme in themes:
        if re.search(rf"\b{theme}\b", response, re.IGNORECASE):
            extracted.append(theme)
    return extracted

def get_bot_response(user_message, chat_log):
    messages = [{"role": "system", "content": "You are a DBT-informed therapeutic chatbot. Gently explore the user's emotions, behaviors, and themes. Do not diagnose. Wait two weeks before offering DBT skills."}]
    for entry in chat_log:
        if entry['user']:
            messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['bot']})
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return response.choices[0].message.content

def play_tts(text):
    tts = gTTS(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
        tts.save(tmpfile.name)
        return tmpfile.name

# Get input
if audio_bytes:
    user_input = transcribe_audio(audio_bytes)
else:
    user_input = typed_input

# Detect if voice chat suggestion should happen (after 3+ messages)
offer_voice_switch = False
if not st.session_state.voice_chat_opt_in and len(st.session_state.chat_history) >= 4:
    offer_voice_switch = True

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    if offer_voice_switch:
        suggestion = "Would you prefer to continue this conversation using your voice? If that feels more comfortable for you, I can switch to voice chat now."
        st.session_state.chat_history.append({
            "user": user_input,
            "bot": suggestion
        })
        with st.chat_message("assistant"):
            st.markdown(suggestion)
        use_voice = st.radio("Would you like to use voice chat from now on?", ["No", "Yes"], index=0)
        if use_voice == "Yes":
            st.session_state.voice_chat_opt_in = True
        st.stop()

    with st.chat_message("assistant"):
        typing = st.empty()
        typing.markdown("💬 _Typing..._")
        time.sleep(1.5)
        bot_response = get_bot_response(user_input, st.session_state.chat_history)
        typing.empty()
        st.markdown(bot_response)

        audio_file_path = play_tts(bot_response)
        audio_data = open(audio_file_path, 'rb').read()
        st.audio(audio_data, format='audio/mp3')

    st.session_state.chat_history.append({
        "user": user_input,
        "bot": bot_response
    })
    st.session_state.summary_notes.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d')}] User: {user_input} | Bot: {bot_response}")
    themes_found = extract_themes_from_response(user_input + " " + bot_response)
    for theme in themes_found:
        st.session_state.theme_memory[theme] += 1

# Show summary if 2 weeks passed
days_elapsed = (datetime.datetime.now() - st.session_state.first_interaction).days
if days_elapsed >= 14:
    st.markdown("### 🧾 Summary of Reflections So Far")
    for note in st.session_state.summary_notes[-10:]:
        st.markdown(f"- {note}")
    st.markdown("### 🧠 Recurring Emotional Themes")
    sorted_themes = sorted(st.session_state.theme_memory.items(), key=lambda x: -x[1])
    for theme, count in sorted_themes:
        st.markdown(f"- **{theme.title()}**: mentioned {count} time(s)")
    st.markdown("You’ve now spent two weeks building self-awareness. Would you like to explore a DBT skill next time?")
else:
    st.info(f"Keep engaging for {14 - days_elapsed} day(s) more to receive personalised suggestions.")
