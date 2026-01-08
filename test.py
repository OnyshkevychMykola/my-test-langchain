import os
import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()


OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model='gpt-4o')
first_prompt = PromptTemplate( input_variables=['description'],
    template="""
    Based on provided description context guess the country and answer only with it's name.
    Context:
    {description}
    """
)
prompt = PromptTemplate( input_variables=['country'],
    template="""
    You are professional geographer, by context of country name - give 5 interesting geographical facts about it.
    If country does not exists respond that you can't answer the question.
    Context:
    {country}
    """
)


first_chain = first_prompt | llm | StrOutputParser() | (lambda title: (st.write(title),title)[1])
second_chain = prompt | llm
final_chain = first_chain | second_chain
st.title("Country Info")
description = st.text_input('Describe your country: ')

if description:
    response = final_chain.invoke({'description': description})
    st.write(response.content)