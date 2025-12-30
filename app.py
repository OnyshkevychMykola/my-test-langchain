import streamlit as st
from chains import answer_query
from dotenv import load_dotenv
load_dotenv()
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

st.set_page_config(page_title="My Test Language Chain")

st.title("Just answering questions")

if "session_id" not in st.session_state:
    st.session_state.session_id = st.session_state.get("run_id", "default-session")

history = StreamlitChatMessageHistory(key="chat_history")

if st.button("🆕 New Chat"):
    history.clear()

if history.messages:
    st.header("📝 Chat history")
    for msg in history.messages:
        if msg.type == "human":
            with st.chat_message("user"):
                st.write(msg.content)
        else:
            with st.chat_message("assistant"):
                st.write(msg.content)
else:
    st.info("No chat history yet. Start by asking a question! 👇")

query = st.chat_input("Ask your question here...")

if query:
    history.add_user_message(query)

    with st.chat_message("user"):
        st.write(query)

    with st.spinner("Thinking..."):
        answer = answer_query(query)

    history.add_ai_message(answer)

    with st.chat_message("assistant"):
        st.write(answer)
