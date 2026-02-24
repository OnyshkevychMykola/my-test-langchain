import uuid
import streamlit as st
from chains import answer_query
from dotenv import load_dotenv
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

load_dotenv()

st.set_page_config(
    page_title="Medical AI Assistant",
    layout="wide",
)

st.title("🩺 Medical Information Assistant")

if "chats" not in st.session_state:
    st.session_state.chats = {}

if "active_chat" not in st.session_state:
    st.session_state.active_chat = str(uuid.uuid4())

if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None


def get_history(chat_id: str) -> StreamlitChatMessageHistory:
    if chat_id not in st.session_state.chats:
        st.session_state.chats[chat_id] = StreamlitChatMessageHistory(
            key=f"chat_{chat_id}"
        )
    return st.session_state.chats[chat_id]

with st.sidebar:
    st.header("💬 Chats")

    if st.button("🆕 New Chat"):
        st.session_state.active_chat = str(uuid.uuid4())

    for chat_id in st.session_state.chats.keys():
        label = f"Chat {chat_id[:8]}"
        if st.button(label, key=f"select_{chat_id}"):
            st.session_state.active_chat = chat_id

history = get_history(st.session_state.active_chat)

if history.messages:
    for msg in history.messages:
        if msg.type == "human":
            with st.chat_message("user"):
                st.write(msg.content)
        else:
            with st.chat_message("assistant"):
                st.write(msg.content)
else:
    st.info("Start a medical-related conversation 👇")

col1, col2 = st.columns([10, 1])

with col2:
    with st.popover("📎"):
        uploaded_file = st.file_uploader(
            "Upload image",
            type=["png", "jpg", "jpeg"],
            key="upload"
        )

        camera_file = st.camera_input(
            "Take photo",
            key="camera"
        )

        st.session_state.uploaded_image = uploaded_file or camera_file

if st.session_state.uploaded_image:
    st.image(
        st.session_state.uploaded_image,
        caption="Attached image",
        width=200
    )

query = st.chat_input("Ask a medical question...")

if query:
    history.add_user_message(query)
    with st.chat_message("user"):
        st.write(query)

    with st.spinner("Thinking..."):
        answer = answer_query(
            query=query,
            image_file=st.session_state.uploaded_image,
            history=history,
        )

    history.add_ai_message(answer)

    with st.chat_message("assistant"):
        st.write(answer)

    st.session_state.uploaded_image = None
