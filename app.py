import streamlit as st
from chains import answer_query
from dotenv import load_dotenv
load_dotenv()
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
history = StreamlitChatMessageHistory()


st.set_page_config(page_title="My Test Language Chain")

st.title("Just answering questions")

if "session_id" not in st.session_state:
    st.session_state.session_id = st.session_state.get("run_id", "default-session")

query = st.text_input("Ask question:")

if st.button("Press to get answer") or query:
    with st.spinner("Thinking..."):
        answer = answer_query(query, st.session_state.session_id)
    st.write(answer)

    history = StreamlitChatMessageHistory(key="chat_history")
    st.header("Chat history")
    for msg in history.messages:
        role = "Human" if msg.type == "human" else "AI"
        st.write(f"{role}: {msg.content}")
