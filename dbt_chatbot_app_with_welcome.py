
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
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av

# Load OpenAI key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="DBT Voice Chatbot", layout="centered")
st.title("🧠 Your mental health companion")
st.markdown("You can type or speak to the bot. This DBT-informed companion reflects on your emotions over time.")

# Set up session state
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
if 'use_mic' not in st.session_state:
    st.session_state.use_mic = False

# Theme extractor
def extract_themes_from_response(response):
    themes = ["shame", "anger", "impulsivity", "loneliness", "worthlessness", "avoidance", "abandonment", "perfectionism", "fear", "guilt", "rejection"]
    return [theme for theme in themes if re.search(rf"\b{theme}\b", response, re.IGNORECASE)]

# GPT response
def get_bot_response(user_message, chat_log):
    messages = [{"role": "system", "content": "You are a DBT-informed chatbot exploring emotion and behavior gently. Do not diagnose or offer treatment. Embed reflective prompts."}]
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

# Text input
user_input = st.chat_input("You:")

# Voice fallback
if not user_input:
    st.markdown("Or use your voice 👇")
    class AudioProcessor(AudioProcessorBase):
        def __init__(self):
            self.recorder = whisper.load_model("base")
            self.frames = []

        def recv(self, frame):
            audio = frame.to_ndarray()
            self.frames.append(audio)
            return av.AudioFrame.from_ndarray(audio, layout="mono")

    ctx = webrtc_streamer(key="speech", audio_processor_factory=AudioProcessor, media_stream_constraints={"audio": True, "video": False})
    if ctx.audio_processor and len(ctx.audio_processor.frames) > 0:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            audio_path = f.name
        whisper.save_audio(audio_path, ctx.audio_processor.frames)
        transcription = whisper.load_model("base").transcribe(audio_path)["text"]
        if transcription:
            user_input = transcription
            st.session_state.use_mic = True

# Show chat so far
for chat in st.session_state.chat_history:
    if chat['user']:
        with st.chat_message("user"):
            st.markdown(chat['user'])
    with st.chat_message("assistant"):
        st.markdown(chat['bot'])

# Process input
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    offer_voice_switch = not st.session_state.use_mic and len(st.session_state.chat_history) >= 3
    if offer_voice_switch:
        switch_prompt = "Would you prefer switching to voice chat? If that feels more natural, I can activate the mic."
        st.session_state.chat_history.append({"user": user_input, "bot": switch_prompt})
        with st.chat_message("assistant"):
            st.markdown(switch_prompt)
        switch = st.radio("Use voice?", ["No", "Yes"], index=0)
        if switch == "Yes":
            st.session_state.use_mic = True
        st.stop()

    with st.chat_message("assistant"):
        typing = st.empty()
        typing.markdown("💬 _Typing..._")
        time.sleep(1.5)
        bot_response = get_bot_response(user_input, st.session_state.chat_history)
        typing.empty()
        st.markdown(bot_response)

    st.session_state.chat_history.append({"user": user_input, "bot": bot_response})
    st.session_state.summary_notes.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d')}] User: {user_input} | Bot: {bot_response}")
    themes_found = extract_themes_from_response(user_input + " " + bot_response)
    for theme in themes_found:
        st.session_state.theme_memory[theme] += 1

# Summary logic
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
