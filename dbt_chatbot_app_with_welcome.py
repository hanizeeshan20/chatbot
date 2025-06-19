
import streamlit as st
import datetime
import os
import re
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv
from gtts import gTTS
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import tempfile
from transformers import pipeline

# Load OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load emotion classifier
emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

# Audio processor class (needed even if it's basic)
class AudioProcessor(AudioProcessorBase):
    def recv(self, frame):
        return frame

# Session state initialisation
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'first_interaction' not in st.session_state:
    st.session_state.first_interaction = datetime.datetime.now()
if 'summary_notes' not in st.session_state:
    st.session_state.summary_notes = []
if 'emotion_trends' not in st.session_state:
    st.session_state.emotion_trends = defaultdict(int)

if 'theme_memory' not in st.session_state:
    st.session_state.theme_memory = defaultdict(int)
if 'chat_started' not in st.session_state:
    st.session_state.chat_history.append({
        "user": "",
        "bot": "Hi there. What brings you here today?"
    })
    st.session_state.chat_started = True
    st.session_state.voice_prompt_asked = False
if 'use_voice' not in st.session_state:
    st.session_state.use_voice = False

st.title("🧠 Your mental health companion")
st.markdown("You can type or speak to the bot. This DBT-informed companion reflects on your emotions over time.")

# Ask about voice chat after first user message
def ask_voice_chat():
    if not st.session_state.voice_prompt_asked:
        st.session_state.chat_history.append({
            "user": "",
            "bot": "Would you prefer to speak instead of type? I can listen to your voice if you're more comfortable that way."
        })
        st.session_state.voice_prompt_asked = True

# Display chat history
for chat in st.session_state.chat_history:
    if chat['user']:
        st.markdown(f"**You:** {chat['user']}")
    st.markdown(f"**Bot:** {chat['bot']}")

# Voice chat toggle response
if st.session_state.voice_prompt_asked and not st.session_state.use_voice:
    voice_response = st.radio("Would you like to switch to voice chat?", ("No", "Yes"), key="voice_choice")
    if voice_response == "Yes":
        st.session_state.use_voice = True
        st.experimental_rerun()

# Voice chat interface
if st.session_state.use_voice:
    st.markdown("Or use your voice 👇")
    ctx = webrtc_streamer(
        key="speech",
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False}
    )

# User input
user_input = st.text_input("You:", key="user_input")

# Theme extraction
def extract_themes_from_response(response):
    themes = ["shame", "anger", "impulsivity", "loneliness", "worthlessness", "avoidance", "abandonment", "perfectionism", "fear", "guilt", "rejection"]
    return [theme for theme in themes if re.search(rf"\b{theme}\b", response, re.IGNORECASE)]

# Bot response logic
def get_bot_response(user_message, chat_log):
    messages = [{"role": "system", "content": "You are a DBT-informed therapeutic chatbot. You are aware of the user's dominant emotional tone (e.g. sadness, anger, joy) and should gently adapt your language to that tone where appropriate. Your role is to gently explore the user's emotions, behaviors, and patterns over time. Do not offer treatment or diagnosis. Instead, embed reflective questions where relevant and take note of any recurring themes."}]
    for entry in chat_log:
        if entry['user']:
            messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['bot']})
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(model="gpt-4o", messages=messages)
    return response.choices[0].message.content

# TTS playback
def speak_text(text):
    tts = gTTS(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_path = fp.name
        tts.save(temp_path)
        st.audio(temp_path, format="audio/mp3")

# Handle user input
if user_input:
    bot_response = get_bot_response(user_input, st.session_state.chat_history)

    st.session_state.chat_history.append({
        "user": user_input,
        "bot": bot_response
    })

    st.session_state.summary_notes.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d')}] User: {user_input} | Bot: {bot_response}")

    for theme in extract_themes_from_response(user_input + " " + bot_response):
        st.session_state.theme_memory[theme] += 1

    speak_text(bot_response)
    emotions = analyze_emotions(user_input)
    st.markdown(f"🧠 **Detected emotions:** {', '.join(emotions)}")
    for em in emotions:
        label = em.split(" ")[0].lower()
        st.session_state.emotion_trends[label] += 1
    ask_voice_chat()

# Weekly summary logic
days_elapsed = (datetime.datetime.now() - st.session_state.first_interaction).days
if days_elapsed >= 14:
    st.markdown("### 🧾 Summary of Reflections So Far")
    for note in st.session_state.summary_notes[-10:]:
        st.markdown(f"- {note}")
    st.markdown("### 🧠 Recurring Emotional Themes")
    sorted_themes = sorted(st.session_state.theme_memory.items(), key=lambda x: -x[1])
    for theme, count in sorted_themes:
        st.markdown(f"- **{theme.title()}**: mentioned {count} time(s)")
    st.markdown("### 📊 Emotion Trends (Top 5)")
    if st.session_state.emotion_trends:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        sorted_emotions = sorted(st.session_state.emotion_trends.items(), key=lambda x: -x[1])[:5]
        labels, values = zip(*sorted_emotions)
        ax.bar(labels, values)
        ax.set_ylabel("Mentions")
        ax.set_title("Emotion Frequency Over Time")
        st.pyplot(fig)
    st.markdown("You’ve now spent two weeks building self-awareness. Would you like to explore a DBT skill next time?")
else:
    st.info(f"Keep engaging for {14 - days_elapsed} day(s) more to receive personalised suggestions.")


# Emotion analysis
def analyze_emotions(text):
    results = emotion_classifier(text)
    sorted_emotions = sorted(results[0], key=lambda x: x['score'], reverse=True)
    top_emotions = [f"{e['label']} ({round(e['score'] * 100, 2)}%)" for e in sorted_emotions[:3]]
    return top_emotions
