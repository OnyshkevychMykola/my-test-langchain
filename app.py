import streamlit as st
from chains import answer_query
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="My Test Language Chain")

st.title("Just answering questions")

query = st.text_input("Asc question:")

if st.button("Press to get answer") or query:
    with st.spinner("Thinking..."):
        answer = answer_query(query)
    st.write(answer)
