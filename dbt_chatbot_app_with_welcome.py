
import streamlit as st
import openai
import datetime
import os
import re
from dotenv import load_dotenv
from collections import defaultdict

# Load OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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

st.title("🧠 DBT Chatbot – Reflective Companion with Memory")

st.markdown("Start chatting below. This bot reflects on emotional patterns and remembers key themes over time. It will not offer DBT skills until enough insight is developed.")

user_input = st.text_input("You:", key="user_input")

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

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )

    return response['choices'][0]['message']['content']

if user_input:
    bot_response = get_bot_response(user_input, st.session_state.chat_history)

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

# Display chat history
for chat in st.session_state.chat_history:
    if chat['user']:
        st.markdown(f"**You:** {chat['user']}")
    st.markdown(f"**Bot:** {chat['bot']}")

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
    st.info(f"🕒 {14 - days_elapsed} day(s) remaining until skill suggestions become available.")
