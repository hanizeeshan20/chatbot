
import streamlit as st
import datetime
import os
import re
import time
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv

# Load OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize session state
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

st.set_page_config(page_title="DBT Chatbot", layout="centered")
st.title("🧠 Your mental health companion")
st.markdown("Start chatting below. This bot reflects on emotional patterns and remembers key themes over time.")

# Display chat history BEFORE input
chat_placeholder = st.empty()
with chat_placeholder.container():
    for chat in st.session_state.chat_history:
        if chat['user']:
            with st.chat_message("user"):
                st.markdown(chat['user'])
        with st.chat_message("assistant"):
            st.markdown(chat['bot'])

# User input box
user_input = st.chat_input("You:")

def extract_themes_from_response(response):
    themes = ["shame", "anger", "impulsivity", "loneliness", "worthlessness", "avoidance", "abandonment", "perfectionism", "fear", "guilt", "rejection"]
    extracted = []
    for theme in themes:
        if re.search(rf"\b{theme}\b", response, re.IGNORECASE):
            extracted.append(theme)
    return extracted

def get_bot_response(user_message, chat_log):
    messages = [{"role": "system", "content": "You are a DBT-informed therapeutic chatbot. Your role is to gently explore the user's emotions, behaviors, and patterns over time. Do not offer treatment or diagnosis. Instead, embed reflective questions where relevant and take note of any recurring themes."}]

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

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        typing = st.empty()
        typing.markdown("💬 _Typing..._")
        time.sleep(1.5)  # simulate typing delay
        bot_response = get_bot_response(user_input, st.session_state.chat_history)
        typing.empty()
        st.markdown(bot_response)

    # Save chat history
    st.session_state.chat_history.append({
        "user": user_input,
        "bot": bot_response
    })

    # Save reflections
    st.session_state.summary_notes.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d')}] User: {user_input} | Bot: {bot_response}")

    # Update memory with emotional themes
    themes_found = extract_themes_from_response(user_input + " " + bot_response)
    for theme in themes_found:
        st.session_state.theme_memory[theme] += 1

# Summary if 2 weeks have passed
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
