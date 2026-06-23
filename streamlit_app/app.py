"""Streamlit chat UI for the College Chatbot."""

import os
import sys

import requests
import streamlit as st

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="College Chatbot",
    page_icon="🎓",
    layout="wide",
)

# Title
st.title("College Data Chatbot")
st.caption("Ask questions about students, attendance, exams, placements, and more — in English, Hindi, or Hinglish.")

# Sidebar with example questions
with st.sidebar:
    st.header("Example Questions")
    st.markdown("Click any example to try it:")

    examples = [
        "How many students are in Center Delhi?",
        "Show me the top 5 students in Math Mid-Term exam",
        "Which students have attendance above 90%?",
        "Students who got placed with package > 10 LPA",
        "List members of the Coding Club from Center Mumbai",
        "How many problems did Rohan Das solve?",
        "Students whose attendance rose by 30% from week 1 to week 2",
        "What's the average placement package?",
        "Show all certifications obtained by Aarav Sharma",
    ]

    for example in examples:
        if st.button(example, key=f"ex_{example[:20]}", use_container_width=True):
            st.session_state["input_question"] = example

    st.divider()
    st.header("Settings")
    show_sql = st.checkbox("Show generated SQL", value=True)
    st.caption(f"Backend: {BACKEND_URL}")


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


def send_question(question: str) -> dict:
    """Send a question to the backend API."""
    try:
        payload = {"question": question}
        if st.session_state.conversation_id:
            payload["conversation_id"] = st.session_state.conversation_id

        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "answer": "Could not connect to the backend server. Make sure it's running at " + BACKEND_URL,
            "is_clarification": False,
            "conversation_id": st.session_state.conversation_id or "",
        }
    except requests.exceptions.Timeout:
        return {
            "answer": "The request timed out. The server might be processing a complex query. Please try again.",
            "is_clarification": False,
            "conversation_id": st.session_state.conversation_id or "",
        }
    except Exception as e:
        return {
            "answer": f"An error occurred: {str(e)}",
            "is_clarification": False,
            "conversation_id": st.session_state.conversation_id or "",
        }


# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("sql") and show_sql:
            with st.expander("View SQL Query"):
                st.code(message["sql"], language="sql")


# Chat input
input_question = st.session_state.pop("input_question", None)
user_input = st.chat_input("Ask a question about college data...")

# Use either sidebar example or chat input
question = input_question or user_input

if question:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = send_question(question)

        # Update conversation ID
        if response.get("conversation_id"):
            st.session_state.conversation_id = response["conversation_id"]

        answer = response.get("answer", "Sorry, I couldn't process that.")
        sql = response.get("sql")
        is_clarification = response.get("is_clarification", False)

        # Display response
        st.markdown(answer)

        if sql and show_sql and not is_clarification:
            with st.expander("View SQL Query"):
                st.code(sql, language="sql")

        # Store in history
        msg = {"role": "assistant", "content": answer}
        if sql:
            msg["sql"] = sql
        st.session_state.messages.append(msg)


# Footer
st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()
with col2:
    st.caption("Powered by Gemini + FastAPI")
