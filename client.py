import json
import os
import asyncio
from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage

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
    },
    "chroma": {
        "url": "http://localhost:8003/mcp",
        "transport": "streamable_http"
    }
})

tools = asyncio.run(mcp_client.get_tools())

llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)

agent = create_agent(llm, tools)

async def get_supported_cities_context():
    blobs = await mcp_client.get_resources(
        server_name="weather",
        uris="weather://supported-cities"
    )

    if not blobs:
        return ""

    raw = blobs[0].as_string()
    data = json.loads(raw)

    cities = ", ".join(data["cities"])
    return f"You can provide weather only for these cities: {cities}."

st.title("AI Agent (MCP Version)")
task = st.text_input("Assign me a task")


if task:
    supported_cities_context = asyncio.run(get_supported_cities_context())

    messages = [
        SystemMessage(content=supported_cities_context),
        HumanMessage(content=task)
    ]

    response = asyncio.run(agent.ainvoke({"messages": messages}))
    st.write(response)
    final_output = response["messages"][-1].content
    st.write(final_output)
