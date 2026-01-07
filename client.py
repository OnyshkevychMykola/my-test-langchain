import os
import asyncio
from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from langchain_mcp_adapters.client import MultiServerMCPClient
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
load_dotenv()

mcp_client = MultiServerMCPClient({
    "math": {
        "url": "http://localhost:8001/mcp",
        "transport": "streamable_http"
    },
    "weather": {
        "url": "http://localhost:8002/mcp",
        "transport": "streamable_http"
    }
})

tools = asyncio.run(mcp_client.get_tools())

llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)

agent = create_agent(llm, tools)

st.title("AI Agent (MCP Version)")
task = st.text_input("Assign me a task")


if task:
    response = asyncio.run(agent.ainvoke({"messages": task}))
    st.write(response)
    final_output = response["messages"][-1].content
    st.write(final_output)
